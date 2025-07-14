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
    industryIdentifiers: Optional[List[Dict[str, str]]] = None

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
    BASE_URL = "https://www.googleapis.com/books/v1"
    CACHE_TIMEOUT = getattr(settings, 'GOOGLE_BOOKS_CACHE_TIMEOUT', 14400)

    def __init__(self):
        self.api_key = getattr(settings, 'GOOGLE_BOOKS_API_KEY', None)

    @cached_api_call(cache_timeout=CACHE_TIMEOUT)
    def get_book_data(self, isbn: str) -> Optional[BookEnrichmentData]:
        url = f"{self.BASE_URL}/volumes"
        params = {'q': f"isbn:{isbn}", 'maxResults': 1}
        data = self._make_request(url, params, "Google Books API error")
        if not data or not data.get('items'):
            return None
        item = data['items'][0].get('volumeInfo', {})
        return BookEnrichmentData(
            isbn=isbn,
            title=item.get('title', ''),
            author=', '.join(item.get('authors', [])),
            description=item.get('description', ''),
            published_date=self._parse_date(item.get('publishedDate', '')),
            page_count=item.get('pageCount', 0),
            language=item.get('language', ''),
            categories=item.get('categories', []),
            thumbnail=item.get('imageLinks', {}).get('thumbnail', ''),
            preview_link=item.get('previewLink', ''),
            rating=item.get('averageRating', 0.0),
            reviews_count=item.get('ratingsCount', 0),
            source='Google Books',
            industryIdentifiers=item.get('industryIdentifiers', [])
        )

    @cached_api_call(cache_timeout=CACHE_TIMEOUT)
    def search_books(self, query: str) -> List[BookEnrichmentData]:
        """Поиск книг по запросу."""
        url = f"{self.BASE_URL}/volumes"
        params = {'q': query, 'maxResults': getattr(settings, 'GOOGLE_BOOKS_MAX_RESULTS', 10)}
        data = self._make_request(url, params, "Google Books API search error")
        if not data or not data.get('items'):
            return []
        results = []
        for item in data['items']:
            volume_info = item.get('volumeInfo', {})
            isbn_list = [identifier.get('identifier', '') for identifier in volume_info.get('industryIdentifiers', []) if identifier.get('type') == 'ISBN_13']
            isbn = isbn_list[0] if isbn_list else ''
            results.append(BookEnrichmentData(
                isbn=isbn,
                title=volume_info.get('title', ''),
                author=', '.join(volume_info.get('authors', [])),
                description=volume_info.get('description', ''),
                published_date=self._parse_date(volume_info.get('publishedDate', '')),
                page_count=volume_info.get('pageCount', 0),
                language=volume_info.get('language', ''),
                categories=volume_info.get('categories', []),
                thumbnail=volume_info.get('imageLinks', {}).get('thumbnail', ''),
                preview_link=volume_info.get('previewLink', ''),
                rating=volume_info.get('averageRating', 0.0),
                reviews_count=volume_info.get('ratingsCount', 0),
                source='Google Books',
                industryIdentifiers=volume_info.get('industryIdentifiers', [])
            ))
        return results

    def _parse_date(self, date_str: str) -> Optional[str]:
        if not date_str:
            return None
        try:
            return date_str.split('-')[0] if '-' in date_str else date_str
        except Exception as e:
            logger.error(f"Date parsing error: {str(e)}")
            return None

    def _make_request(self, url: str, params: Dict[str, Any], error_msg: str, default_return: Any = None) -> Any:
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"{error_msg}: {str(e)}")
            return default_return

class OpenLibraryService(BookDataService):
    """Сервис для работы с Open Library API."""
    BASE_URL = "https://openlibrary.org"
    CACHE_TIMEOUT = getattr(settings, 'OPEN_LIBRARY_CACHE_TIMEOUT', 14400)

    @cached_api_call(cache_timeout=CACHE_TIMEOUT)
    def get_book_data(self, isbn: str) -> Optional[BookEnrichmentData]:
        url = f"{self.BASE_URL}/isbn/{isbn}.json"
        data = self._make_request(url, {}, "Open Library API error")
        if not data:
            return None
        author_key = data.get('authors', [{}])[0].get('key') if data.get('authors') else None
        author_name = ''
        if author_key:
            author_data = self._make_request(f"{self.BASE_URL}{author_key}.json", {}, "Open Library Author API error")
            if author_data:
                author_name = author_data.get('name', '')
        industry_identifiers = [{'type': 'ISBN_13', 'identifier': isbn}] if len(isbn) == 13 else [{'type': 'ISBN_10', 'identifier': isbn}] if len(isbn) == 10 else []
        return BookEnrichmentData(
            isbn=isbn,
            title=data.get('title', ''),
            author=author_name,
            description=data.get('description', {}).get('value', '') if isinstance(data.get('description'), dict) else data.get('description', ''),
            published_date=self._parse_date(data.get('publish_date', '')),
            page_count=data.get('number_of_pages', 0),
            language=data.get('languages', [{}])[0].get('key', '').split('/')[-1] if data.get('languages') else '',
            categories=[subject.get('key', '').split('/')[-1] for subject in data.get('subjects', [])],
            thumbnail=f"https://covers.openlibrary.org/b/isbn/{isbn}-M.jpg" if data.get('covers') else '',
            preview_link=f"https://openlibrary.org/isbn/{isbn}",
            rating=0.0,
            reviews_count=0,
            source='Open Library',
            industryIdentifiers=industry_identifiers
        )

    @cached_api_call(cache_timeout=CACHE_TIMEOUT)
    def search_books(self, query: str) -> List[BookEnrichmentData]:
        """Поиск книг по запросу."""
        url = f"{self.BASE_URL}/search.json"
        params = {'q': query, 'limit': getattr(settings, 'OPEN_LIBRARY_MAX_RESULTS', 10)}
        data = self._make_request(url, params, "Open Library API search error")
        if not data or not data.get('docs'):
            return []
        results = []
        for doc in data['docs']:
            isbn_list = doc.get('isbn', [])
            isbn = isbn_list[0] if isbn_list else ''
            industry_identifiers = []
            for i, isbn_val in enumerate(isbn_list):
                if len(isbn_val) == 13:
                    industry_identifiers.append({'type': 'ISBN_13', 'identifier': isbn_val})
                elif len(isbn_val) == 10:
                    industry_identifiers.append({'type': 'ISBN_10', 'identifier': isbn_val})
                if i >= 1:  
                    break
            results.append(BookEnrichmentData(
                isbn=isbn,
                title=doc.get('title', ''),
                author=', '.join(doc.get('author_name', [])),
                description='',
                published_date=str(doc.get('first_publish_year', '')) if doc.get('first_publish_year') else '',
                page_count=doc.get('number_of_pages_median', 0),
                language=doc.get('language', [''])[0] if doc.get('language') else '',
                categories=doc.get('subject', []),
                thumbnail=f"https://covers.openlibrary.org/b/id/{doc.get('cover_i', '')}-M.jpg" if doc.get('cover_i') else '',
                preview_link=f"https://openlibrary.org{doc.get('key', '')}" if doc.get('key') else '',
                rating=0.0,
                reviews_count=0,
                source='Open Library',
                industryIdentifiers=industry_identifiers
            ))
        return results

    def _parse_date(self, date_str: str) -> Optional[str]:
        if not date_str:
            return None
        try:
            return date_str.split('-')[0] if '-' in date_str else date_str
        except Exception as e:
            logger.error(f"Date parsing error: {str(e)}")
            return None

    def _make_request(self, url: str, params: Dict[str, Any], error_msg: str, default_return: Any = None) -> Any:
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"{error_msg}: {str(e)}")
            return default_return

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
        google_results = self.google_books.search_books(query)
        results.extend(google_results)
        if len(results) < limit:
            remaining = limit - len(results)
            open_library_results = self.open_library.search_books(query)
            existing_isbns = {book.isbn for book in results}
            for book in open_library_results:
                if book.isbn not in existing_isbns:
                    results.append(book)
                    if len(results) >= limit:
                        break
        return results[:limit]
