from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
import requests
from django.conf import settings
from django.core.cache import cache
import logging
from functools import wraps
import hashlib
import json

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
    """
    Декоратор для кэширования API-вызовов.
    Генерирует безопасные ключи кэша, совместимые с Memcached.
    """
    sentinel = object()
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Создаем список аргументов для включения в ключ кэша
            arg_dict = {}
            
            # Если первый аргумент - это self или cls, пропускаем его
            if args and hasattr(args[0], '__class__'):
                method_args = args[1:]
            else:
                method_args = args
            
            # Добавляем позиционные аргументы
            for i, arg in enumerate(method_args):
                arg_dict[f'arg_{i}'] = str(arg)
            
            # Добавляем именованные аргументы
            for key, value in sorted(kwargs.items()):
                arg_dict[key] = str(value)
                
            # Создаем основу ключа с именем функции
            base_key = f"{func.__module__}.{func.__qualname__}"
            
            # Если есть аргументы, создаем хеш из их JSON-представления
            if arg_dict:
                # Преобразуем словарь аргументов в JSON и хешируем
                args_json = json.dumps(arg_dict, sort_keys=True)
                args_hash = hashlib.md5(args_json.encode()).hexdigest()
                cache_key = f"{base_key}:{args_hash}"
            else:
                cache_key = base_key

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
    def search_books(self, query: str = "", title: str = "", author: str = "", isbn: str = "", limit: int = 10) -> List[BookEnrichmentData]:
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
    def search_books(self, query: str = "", title: str = "", author: str = "", isbn: str = "") -> List[BookEnrichmentData]:
        """
        Поиск книг по названию, автору или ISBN через Google Books API.
        Args:
            query: Общий поисковый запрос (для обратной совместимости).
            title: Название книги.
            author: Автор книги.
            isbn: ISBN книги.
        Returns:
            List[BookEnrichmentData]: Список обогащенных данных о книгах.
        """
        query_parts = []
        if isbn:
            query_parts.append(f"isbn:{isbn}")
        if title:
            query_parts.append(f"intitle:{title}")
        if author:
            query_parts.append(f"inauthor:{author}")
        
        if not query_parts and not query:
            return []
        
        final_query = query if query else "+".join(query_parts)
        params = {"q": final_query, "maxResults": 1 if isbn else 5}
        response = self._make_request(self.BASE_URL + "/volumes", params, "Google Books API error")
        if not response or 'items' not in response:
            return []
        
        results = []
        for item in response.get('items', []):
            book_data = self._parse_book_data(item)
            if book_data:
                results.append(book_data)
        return results

    def _parse_date(self, date_str: str) -> Optional[str]:
        if not date_str:
            return None
        try:
            return date_str.split('-')[0] if '-' in date_str else date_str
        except Exception as e:
            logger.error(f"Date parsing error: {str(e)}")
            return None

    def _parse_book_data(self, item):
        volume_info = item.get('volumeInfo', {})
        isbn_list = [identifier.get('identifier', '') for identifier in volume_info.get('industryIdentifiers', []) if identifier.get('type') == 'ISBN_13']
        isbn = isbn_list[0] if isbn_list else ''
        return BookEnrichmentData(
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
        )

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

    def __init__(self):
        self.api_key = getattr(settings, 'OPEN_LIBRARY_API_KEY', None)

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
    def search_books(self, query: str = "", title: str = "", author: str = "", isbn: str = "") -> List[BookEnrichmentData]:
        """
        Поиск книг по названию, автору или ISBN через Open Library API.
        Args:
            query: Общий поисковый запрос (для обратной совместимости).
            title: Название книги.
            author: Автор книги.
            isbn: ISBN книги.
        Returns:
            List[BookEnrichmentData]: Список обогащенных данных о книгах.
        """
        if isbn:
            params = {"bibkeys": f"ISBN:{isbn}", "format": "json", "jscmd": "data"}
            response = self._make_request(f"{self.BASE_URL}/api/books", params, "Open Library API error")
            if not response or f"ISBN:{isbn}" not in response:
                return []
            book_data = response.get(f"ISBN:{isbn}", {})
            parsed_data = self._parse_book_data(book_data, isbn)
            return [parsed_data] if parsed_data else []
        else:
            final_query = query if query else (f"title:{title}" if title else "")
            if author and not query:
                final_query += f"+author:{author}"
            params = {"q": final_query, "limit": 5}
            response = self._make_request(f"{self.BASE_URL}/search.json", params, "Open Library Search API error")
            if not response or 'docs' not in response:
                return []
            results = []
            for doc in response.get('docs', []):
                isbn_val = doc.get('isbn', [''])[0]
                if isbn_val:
                    book_data = self._get_book_by_isbn(isbn_val)
                    if book_data:
                        results.append(book_data)
            return results

    def _parse_date(self, date_str: str) -> Optional[str]:
        if not date_str:
            return None
        try:
            return date_str.split('-')[0] if '-' in date_str else date_str
        except Exception as e:
            logger.error(f"Date parsing error: {str(e)}")
            return None

    def _parse_book_data(self, book_data: Dict[str, Any], isbn: str = "") -> Optional[BookEnrichmentData]:
        """
        Парсинг данных о книге из ответа Open Library API.
        Args:
            book_data: Данные о книге из API.
            isbn: ISBN книги (если известен).
        Returns:
            Optional[BookEnrichmentData]: Обогащенные данные о книге или None, если данные некорректны.
        """
        if not book_data or 'title' not in book_data:
            return None

        title = book_data.get('title', '')
        author = ""
        if 'authors' in book_data and book_data['authors']:
            author_data = book_data['authors'][0]
            if 'key' in author_data:
                author_info = self._make_request(f"{self.BASE_URL}{author_data['key']}", {}, "Open Library Author API error")
                if author_info and 'name' in author_info:
                    author = author_info['name']
            elif 'name' in author_data:
                author = author_data['name']

        published_date = book_data.get('publish_date', '')
        description = book_data.get('description', '')
        if isinstance(description, dict) and 'value' in description:
            description = description['value']

        isbn = isbn or book_data.get('identifiers', {}).get('isbn_13', [''])[0] or book_data.get('isbn', [''])[0]
        industry_identifiers = []
        if 'identifiers' in book_data:
            if 'isbn_13' in book_data['identifiers']:
                industry_identifiers.extend([{'type': 'ISBN_13', 'identifier': id_} for id_ in book_data['identifiers']['isbn_13']])
            if 'isbn_10' in book_data['identifiers']:
                industry_identifiers.extend([{'type': 'ISBN_10', 'identifier': id_} for id_ in book_data['identifiers']['isbn_10']])
        elif isbn:
            industry_identifiers.append({'type': 'ISBN_13', 'identifier': isbn})

        return BookEnrichmentData(
            isbn=isbn,
            title=title,
            author=author,
            description=description,
            published_date=published_date,
            source="Open Library",
            industryIdentifiers=industry_identifiers
        )

    def _get_book_by_isbn(self, isbn):
        url = f"{self.BASE_URL}/isbn/{isbn}.json"
        data = self._make_request(url, {}, "Open Library API error")
        if not data:
            return None
        return self._parse_book_data(data, isbn)

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
    def __init__(self, google_books_service=None, open_library_service=None, ny_times_service=None):
        """
        Инициализация сервиса с внедрением зависимостей.
        
        Args:
            google_books_service: Сервис Google Books API. Если None, создается экземпляр по умолчанию.
            open_library_service: Сервис Open Library API. Если None, создается экземпляр по умолчанию.
            ny_times_service: Сервис NY Times API. Если None, создается экземпляр по умолчанию.
        """
        self.google_books = google_books_service or GoogleBooksService()
        self.open_library = open_library_service or OpenLibraryService()
        self.ny_times = ny_times_service or NYTimesService()

    @cached_api_call(cache_timeout=14400)
    def enrich_book_data(self, isbn: str) -> Optional[BookEnrichmentData]:
        """
        Получение обогащенных данных о книге по ISBN из всех доступных источников.
        Args:
            isbn: ISBN книги.
        Returns:
            Optional[BookEnrichmentData]: Обогащенные данные о книге или None, если данные не найдены.
        """
        enriched_data = None
        for source in [self.google_books, self.open_library]:
            try:
                result = source.search_books(query="", isbn=isbn)
                if result and len(result) > 0:
                    enriched_data = result[0]
                    break
            except Exception as e:
                logger.error(f"Error fetching book data from {source.__class__.__name__}: {str(e)}")
        
        if enriched_data:
            try:
                # Добавляем рецензию от NY Times
                ny_times_review = self.ny_times.get_book_review(isbn)
                if ny_times_review:
                    enriched_data.ny_times_review = ny_times_review
            except Exception as e:
                logger.error(f"Error fetching NY Times review: {str(e)}")
                
        return enriched_data

    def search_books(self, query: str = "", limit: int = 10) -> List[BookEnrichmentData]:
        """
        Поиск книг по названию, автору или ISBN из всех доступных источников.
        Args:
            query: Общий поисковый запрос.
            limit: Максимальное количество результатов.
        Returns:
            List[BookEnrichmentData]: Список обогащенных данных о книгах.
        """
        results = []
        for source in [self.google_books, self.open_library]:
            try:
                source_results = source.search_books(query=query)
                if source_results:
                    results.extend(source_results)
            except Exception as e:
                logger.error(f"Error fetching book data from {source.__class__.__name__}: {str(e)}")
        return results[:limit]
