from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
import requests
from django.conf import settings
from django.core.cache import cache
import logging
from functools import wraps

logger = logging.getLogger(__name__)

@dataclass
class BookEnrichmentData:
    """Структура для обогащенных данных о книге."""
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
    """Декоратор для кэширования API-вызовов."""
    sentinel = object()
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            arg_strings = []
            if args and hasattr(args[0], '__class__'):
                arg_strings.extend([str(arg) for arg in args[1:]])
            else:
                arg_strings.extend([str(arg) for arg in args])
            for key, value in sorted(kwargs.items()):
                arg_strings.append(f"{key}:{value}")
            cache_key = f"{func.__module__}.{func.__qualname__}:{':'.join(arg_strings)}"

            result = cache.get(cache_key, sentinel)
            if result is not sentinel:
                logger.info(f"Cache hit for {func.__name__}")
                return result

            try:
                result = func(*args, **kwargs)
                cache.set(cache_key, result, cache_timeout)
                logger.info(f"Cache set for {func.__name__}")
                return result
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {str(e)}")
                return None

        return wrapper
    return decorator

class BaseAPIService(ABC):
    """Базовый абстрактный класс для всех внешних API-сервисов."""
    @abstractmethod
    def _make_request(self, url: str, params: Dict[str, Any], error_msg: str, default_return: Any = None) -> Any:
        """Выполняет HTTP-запрос с обработкой ошибок и логированием."""
        pass

class BookDataService(BaseAPIService):
    """Абстрактный класс для API-сервисов, предоставляющих данные о книгах."""
    @abstractmethod
    def get_book_data(self, isbn: str) -> Optional[BookEnrichmentData]:
        """Получение данных о книге по ISBN."""
        pass

    @abstractmethod
    def search_books(self, query: str, limit: int = 10) -> List[BookEnrichmentData]:
        """Поиск книг по запросу."""
        pass

class ReviewService(BaseAPIService):
    """Абстрактный класс для API-сервисов, предоставляющих обзоры книг."""
    @abstractmethod
    def get_book_review(self, isbn: str) -> Optional[str]:
        """Получение обзора книги по ISBN."""
        pass

class GoogleBooksService(BookDataService):
    """Сервис для работы с Google Books API."""
    BASE_URL = "https://www.googleapis.com/books/v1/volumes"

    def __init__(self):
        self.api_key = getattr(settings, 'GOOGLE_BOOKS_API_KEY', None)

    def _make_request(self, url: str, params: Dict[str, Any], error_msg: str, default_return: Any = None) -> Any:
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"{error_msg}: {str(e)}")
            return default_return

    @cached_api_call(cache_timeout=7200)
    def get_book_data(self, isbn: str) -> Optional[BookEnrichmentData]:
        try:
            params = {'q': f'isbn:{isbn}', 'key': self.api_key}
            data = self._make_request(self.BASE_URL, params, "Google Books API error")
            if not data or data.get('totalItems', 0) == 0:
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
        except Exception as e:
            logger.error(f"Error processing Google Books data: {str(e)}")
            return None

    @cached_api_call(cache_timeout=3600)
    def search_books(self, query: str, limit: int = 10) -> List[BookEnrichmentData]:
        try:
            params = {'q': query, 'maxResults': min(limit, 40), 'key': self.api_key}
            response = requests.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            results = []
            for item in data.get('items', []):
                book_info = item['volumeInfo']
                isbn = next((id['identifier'] for id in book_info.get('industryIdentifiers', []) if id['type'] in ['ISBN_13', 'ISBN_10']), None)
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

class OpenLibraryService(BookDataService):
    """Сервис для работы с Open Library API."""
    BASE_URL = "https://openlibrary.org"

    def _make_request(self, url: str, params: Dict[str, Any], error_msg: str, default_return: Any = None) -> Any:
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"{error_msg}: {str(e)}")
            return default_return

    @cached_api_call(cache_timeout=7200)
    def get_book_data(self, isbn: str) -> Optional[BookEnrichmentData]:
        try:
            url = f"{self.BASE_URL}/api/books"
            params = {'bibkeys': f'ISBN:{isbn}', 'format': 'json', 'jscmd': 'data'}
            data = self._make_request(url, params, "Open Library API error")
            if data is None or f'ISBN:{isbn}' not in data:
                return None
            book_info = data[f'ISBN:{isbn}']
            return BookEnrichmentData(
                isbn=isbn,
                title=book_info.get('title'),
                author=', '.join([author['name'] for author in book_info.get('authors', [])]),
                description=book_info.get('description'),
                published_date=book_info.get('publish_date'),
                page_count=book_info.get('number_of_pages'),
                categories=book_info.get('subjects', [])[:5],
                thumbnail=book_info.get('cover', {}).get('medium'),
                preview_link=book_info.get('url'),
                source='Open Library'
            )
        except requests.RequestException as e:
            logger.error(f"Open Library API error: {str(e)}")
            return None

    @cached_api_call(cache_timeout=3600)
    def search_books(self, query: str, limit: int = 10) -> List[BookEnrichmentData]:
        try:
            params = {'q': query, 'limit': min(limit, 50), 'format': 'json'}
            response = requests.get(f"{self.BASE_URL}/search.json", params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            results = []
            for doc in data.get('docs', []):
                isbn = next((isbn for isbn in doc.get('isbn', []) if len(isbn) in [10, 13]), None)
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

class NYTimesService(ReviewService):
    """Сервис для работы с NY Times Books API."""
    BASE_URL = "https://api.nytimes.com/svc/books/v3"

    def __init__(self):
        self.api_key = getattr(settings, 'NY_TIMES_API_KEY', None)

    def _make_request(self, url: str, params: Dict[str, Any], error_msg: str, default_return: Any = None) -> Any:
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"{error_msg}: {str(e)}")
            return default_return

    @cached_api_call(cache_timeout=14400)
    def get_book_review(self, isbn: str) -> Optional[str]:
        if not self.api_key:
            return None
        url = f"{self.BASE_URL}/reviews.json"
        params = {'isbn': isbn, 'api-key': self.api_key}
        data = self._make_request(url, params, "NY Times API error", default_return={"num_results": 0})
        if not data or data.get('num_results', 0) == 0:
            return None
        return data['results'][0].get('summary')

class BookEnrichmentService:
    """Главный сервис для обогащения данных о книгах."""
    def __init__(self):
        self.google_books = GoogleBooksService()
        self.open_library = OpenLibraryService()
        self.ny_times = NYTimesService()

    @cached_api_call(cache_timeout=14400)
    def enrich_book_data(self, isbn: str) -> BookEnrichmentData:
        enriched_data = BookEnrichmentData(isbn=isbn)
        google_data = self.google_books.get_book_data(isbn)
        if google_data:
            enriched_data = google_data
        else:
            ol_data = self.open_library.get_book_data(isbn)
            if ol_data:
                enriched_data = ol_data
        ny_times_review = self.ny_times.get_book_review(isbn)
        if ny_times_review:
            enriched_data.ny_times_review = ny_times_review
        return enriched_data

    def search_books(self, query: str, limit: int = 10) -> List[BookEnrichmentData]:
        results = []
        google_results = self.google_books.search_books(query, limit)
        results.extend(google_results)
        if len(results) < limit:
            remaining = limit - len(results)
            open_library_results = self.open_library.search_books(query, remaining)
            existing_isbns = {book.isbn for book in results}
            for book in open_library_results:
                if book.isbn not in existing_isbns:
                    results.append(book)
                    if len(results) >= limit:
                        break
        return results[:limit]
