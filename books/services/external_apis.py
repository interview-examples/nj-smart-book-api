# books/services/external_apis.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
import requests
from django.conf import settings
from django.core.cache import cache
import logging
from functools import wraps
import time

logger = logging.getLogger(__name__)


@dataclass
class BookEnrichmentData:
    """Структура для обогащенных данных о книге"""
    isbn: str
    title: Optional[str] = None
    author: Optional[str] = None
    description: Optional[str] = None
    published_date: Optional[str] = None
    page_count: Optional[int] = None
    language: Optional[str] = None
    categories: Optional[List[str]] = None
    thumbnail: Optional[str] = None
    preview_link: Optional[str] = None
    rating: Optional[float] = None
    reviews_count: Optional[int] = None
    ny_times_review: Optional[str] = None
    source: Optional[str] = None


def cached_api_call(cache_timeout: int = 3600):
    """Декоратор для кэширования API вызовов"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Создаем уникальный ключ кэша
            cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"

            # Проверяем кэш
            result = cache.get(cache_key)
            if result is not None:
                logger.info(f"Cache hit for {func.__name__}")
                return result

            try:
                # Вызываем функцию
                result = func(*args, **kwargs)
                # Сохраняем в кэш
                cache.set(cache_key, result, cache_timeout)
                logger.info(f"Cache set for {func.__name__}")
                return result
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {str(e)}")
                return None

        return wrapper

    return decorator


class ExternalAPIService(ABC):
    """Абстрактный класс для внешних API сервисов"""

    @abstractmethod
    def get_book_data(self, isbn: str) -> Optional[BookEnrichmentData]:
        pass

    @abstractmethod
    def search_books(self, query: str, limit: int = 10) -> List[BookEnrichmentData]:
        pass


class GoogleBooksService(ExternalAPIService):
    """Сервис для работы с Google Books API"""

    BASE_URL = "https://www.googleapis.com/books/v1/volumes"

    def __init__(self):
        self.api_key = getattr(settings, 'GOOGLE_BOOKS_API_KEY', None)

    @cached_api_call(cache_timeout=7200)  # 2 часа
    def get_book_data(self, isbn: str) -> Optional[BookEnrichmentData]:
        """Получение данных о книге по ISBN"""
        try:
            params = {
                'q': f'isbn:{isbn}',
                'key': self.api_key
            }

            response = requests.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            if data.get('totalItems', 0) == 0:
                return None

            book_info = data['items'][0]['volumeInfo']

            return BookEnrichmentData(
                isbn=isbn,
                title=book_info.get('title'),
                author=', '.join(book_info.get('authors', [])),
                description=book_info.get('description'),
                published_date=book_info.get('publishedDate'),
                page_count=book_info.get('pageCount'),
                language=book_info.get('language'),
                categories=book_info.get('categories'),
                thumbnail=book_info.get('imageLinks', {}).get('thumbnail'),
                preview_link=book_info.get('previewLink'),
                rating=book_info.get('averageRating'),
                reviews_count=book_info.get('ratingsCount'),
                source='Google Books'
            )

        except requests.RequestException as e:
            logger.error(f"Google Books API error: {str(e)}")
            return None

    @cached_api_call(cache_timeout=3600)  # 1 час
    def search_books(self, query: str, limit: int = 10) -> List[BookEnrichmentData]:
        """Поиск книг по запросу"""
        try:
            params = {
                'q': query,
                'maxResults': min(limit, 40),
                'key': self.api_key
            }

            response = requests.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            results = []

            for item in data.get('items', []):
                book_info = item['volumeInfo']
                isbn = None

                # Ищем ISBN
                for identifier in book_info.get('industryIdentifiers', []):
                    if identifier['type'] in ['ISBN_13', 'ISBN_10']:
                        isbn = identifier['identifier']
                        break

                if isbn:
                    results.append(BookEnrichmentData(
                        isbn=isbn,
                        title=book_info.get('title'),
                        author=', '.join(book_info.get('authors', [])),
                        description=book_info.get('description'),
                        published_date=book_info.get('publishedDate'),
                        page_count=book_info.get('pageCount'),
                        language=book_info.get('language'),
                        categories=book_info.get('categories'),
                        thumbnail=book_info.get('imageLinks', {}).get('thumbnail'),
                        preview_link=book_info.get('previewLink'),
                        rating=book_info.get('averageRating'),
                        reviews_count=book_info.get('ratingsCount'),
                        source='Google Books'
                    ))

            return results

        except requests.RequestException as e:
            logger.error(f"Google Books search error: {str(e)}")
            return []


class OpenLibraryService(ExternalAPIService):
    """Сервис для работы с Open Library API"""

    BASE_URL = "https://openlibrary.org"

    @cached_api_call(cache_timeout=7200)  # 2 часа
    def get_book_data(self, isbn: str) -> Optional[BookEnrichmentData]:
        """Получение данных о книге по ISBN"""
        try:
            # Сначала получаем основную информацию
            response = requests.get(
                f"{self.BASE_URL}/api/books",
                params={'bibkeys': f'ISBN:{isbn}', 'format': 'json', 'jscmd': 'data'},
                timeout=10
            )
            response.raise_for_status()

            data = response.json()
            book_key = f'ISBN:{isbn}'

            if book_key not in data:
                return None

            book_info = data[book_key]

            return BookEnrichmentData(
                isbn=isbn,
                title=book_info.get('title'),
                author=', '.join([author['name'] for author in book_info.get('authors', [])]),
                description=book_info.get('description'),
                published_date=book_info.get('publish_date'),
                page_count=book_info.get('number_of_pages'),
                categories=book_info.get('subjects', [])[:5],  # Ограничиваем до 5
                thumbnail=book_info.get('cover', {}).get('medium'),
                preview_link=book_info.get('url'),
                source='Open Library'
            )

        except requests.RequestException as e:
            logger.error(f"Open Library API error: {str(e)}")
            return None

    @cached_api_call(cache_timeout=3600)  # 1 час
    def search_books(self, query: str, limit: int = 10) -> List[BookEnrichmentData]:
        """Поиск книг по запросу"""
        try:
            params = {
                'q': query,
                'limit': min(limit, 50),
                'format': 'json'
            }

            response = requests.get(f"{self.BASE_URL}/search.json", params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            results = []

            for doc in data.get('docs', []):
                isbn = None

                # Ищем ISBN
                for isbn_candidate in doc.get('isbn', []):
                    if len(isbn_candidate) in [10, 13]:
                        isbn = isbn_candidate
                        break

                if isbn:
                    results.append(BookEnrichmentData(
                        isbn=isbn,
                        title=doc.get('title'),
                        author=', '.join(doc.get('author_name', [])),
                        published_date=str(doc.get('first_publish_year', '')),
                        categories=doc.get('subject', [])[:5],
                        source='Open Library'
                    ))

            return results

        except requests.RequestException as e:
            logger.error(f"Open Library search error: {str(e)}")
            return []


class NYTimesService(ExternalAPIService):
    """Сервис для работы с NY Times Books API"""

    BASE_URL = "https://api.nytimes.com/svc/books/v3"

    def __init__(self):
        self.api_key = getattr(settings, 'NY_TIMES_API_KEY', None)

    @cached_api_call(cache_timeout=14400)  # 4 часа
    def get_book_review(self, isbn: str) -> Optional[str]:
        """Получение обзора книги"""
        if not self.api_key:
            return None

        params = {
            'isbn': isbn,
            'api-key': self.api_key
        }
        
        data = self._make_request(
            f"{self.BASE_URL}/reviews.json", 
            params, 
            "NY Times API error", 
            {}
        )
        
        if data and data.get('num_results', 0) > 0:
            return data['results'][0].get('summary')

        return None
    
    # Реализуем абстрактные методы как заглушки, так как они не используются в этом сервисе
    def get_book_data(self, isbn: str) -> Optional[BookEnrichmentData]:
        """Не используется в этом сервисе"""
        return None
        
    def search_books(self, query: str, limit: int = 10) -> List[BookEnrichmentData]:
        """Не используется в этом сервисе"""
        return []


class BookEnrichmentService:
    """Главный сервис для обогащения данных о книгах"""

    def __init__(self):
        self.google_books = GoogleBooksService()
        self.open_library = OpenLibraryService()
        self.ny_times = NYTimesService()

    def enrich_book_data(self, isbn: str) -> BookEnrichmentData:
        """Обогащение данных о книге из всех источников"""
        # Основной источник - Google Books
        enriched_data = self.google_books.get_book_data(isbn)

        # Если не нашли в Google Books, пробуем Open Library
        if not enriched_data:
            enriched_data = self.open_library.get_book_data(isbn)

        # Если все еще нет данных, создаем базовую структуру
        if not enriched_data:
            enriched_data = BookEnrichmentData(isbn=isbn)

        # Дополняем данными из Open Library, если основной источник - Google Books
        if enriched_data.source == 'Google Books':
            open_library_data = self.open_library.get_book_data(isbn)
            if open_library_data:
                # Заполняем пропущенные поля
                if not enriched_data.description and open_library_data.description:
                    enriched_data.description = open_library_data.description
                if not enriched_data.categories and open_library_data.categories:
                    enriched_data.categories = open_library_data.categories

        # Добавляем обзор от NY Times
        ny_times_review = self.ny_times.get_book_review(isbn)
        if ny_times_review:
            enriched_data.ny_times_review = ny_times_review

        return enriched_data

    def search_books(self, query: str, limit: int = 10) -> List[BookEnrichmentData]:
        """Поиск книг по запросу во всех источниках"""
        results = []

        # Поиск в Google Books
        google_results = self.google_books.search_books(query, limit)
        results.extend(google_results)

        # Дополняем поиском в Open Library, если нужно больше результатов
        if len(results) < limit:
            remaining = limit - len(results)
            open_library_results = self.open_library.search_books(query, remaining)

            # Избегаем дублирования по ISBN
            existing_isbns = {book.isbn for book in results}
            for book in open_library_results:
                if book.isbn not in existing_isbns:
                    results.append(book)
                    if len(results) >= limit:
                        break

        return results[:limit]
