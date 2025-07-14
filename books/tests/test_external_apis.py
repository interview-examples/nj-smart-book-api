from unittest import mock
from django.test import TestCase, override_settings
from django.core.cache import cache
from books.services.external_apis import (
    GoogleBooksService,
    OpenLibraryService,
    NYTimesService,
    BookEnrichmentService,
    BookEnrichmentData
)
from books.models import Book

# Моковые данные для внешних API
MOCK_GOOGLE_BOOKS_RESPONSE = {
    "kind": "books#volumes",
    "totalItems": 1,
    "items": [
        {
            "id": "12345",
            "volumeInfo": {
                "title": "A Test-Book for Students",
                "authors": ["Test Author"],
                "description": "Test description",
                "publishedDate": "2023-01-01",
                "industryIdentifiers": [
                    {"type": "ISBN_13", "identifier": "9781234567897"}
                ],
                "categories": ["Fiction", "Novel"],
                "imageLinks": {
                    "thumbnail": "http://example.com/thumbnail.jpg"
                }
            }
        }
    ]
}

MOCK_GOOGLE_BOOKS_SEARCH_RESPONSE = {
    "kind": "books#volumes",
    "totalItems": 1,
    "items": [
        {
            "id": "12345",
            "volumeInfo": {
                "title": "A Test-Book for Students",
                "authors": ["Test Author"],
                "description": "Test description",
                "publishedDate": "2023-01-01",
                "industryIdentifiers": [
                    {"type": "ISBN_13", "identifier": "9781234567897"}
                ],
                "categories": ["Fiction", "Novel"],
                "imageLinks": {
                    "thumbnail": "http://example.com/thumbnail.jpg"
                }
            }
        }
    ]
}

MOCK_OPEN_LIBRARY_RESPONSE = {
    "ISBN:9781234567897": {
        "title": "Test Book",
        "authors": [{"name": "Test Author"}],
        "description": "Test description",
        "publish_date": "2023-01-01",
        "subjects": ["Fiction", "Novel"],
        "cover": {"medium": "http://example.com/thumbnail.jpg"}
    }
}

MOCK_OPEN_LIBRARY_SEARCH_RESPONSE = {
    "num_found": 1,
    "docs": [
        {
            "title": "Test Book",
            "author_name": ["Test Author"],
            "first_publish_year": 2023,
            "isbn": ["9781234567897"],
            "subject": ["Fiction", "Novel"]
        }
    ]
}

MOCK_NY_TIMES_RESPONSE = {
    "num_results": 1,
    "results": [
        {
            "summary": "Test book review summary",
            "book_details": [
                {
                    "title": "Test Book",
                    "author": "Test Author",
                    "primary_isbn13": "9781234567897"
                }
            ]
        }
    ]
}


class GoogleBooksServiceTests(TestCase):
    """Тесты для Google Books API."""

    def setUp(self):
        """Настройка тестовых данных."""
        self.service = GoogleBooksService()
        cache.clear()

    def test_search_by_isbn(self):
        """Тест поиска книги по ISBN."""
        isbn = "1234567890123"
        with mock.patch.object(self.service, '_make_request') as mock_request:
            mock_request.return_value = {
                'items': [{
                    'volumeInfo': {
                        'title': 'Test Book',
                        'authors': ['Test Author'],
                        'industryIdentifiers': [{'type': 'ISBN_13', 'identifier': '1234567890123'}],
                        'description': 'Test description',
                        'publishedDate': '2020-01-01',
                        'pageCount': 200,
                        'language': 'en',
                        'categories': ['Fiction'],
                        'imageLinks': {'thumbnail': 'http://example.com/thumbnail.jpg'},
                        'previewLink': 'http://example.com/preview',
                        'averageRating': 4.5,
                        'ratingsCount': 100
                    }
                }]
            }
            result = self.service.search_books(isbn=isbn)
            self.assertIsInstance(result, list)
            self.assertTrue(len(result) > 0)
            self.assertEqual(result[0].isbn, '1234567890123')
            self.assertEqual(result[0].title, 'Test Book')
            mock_request.assert_called_once_with(
                "https://www.googleapis.com/books/v1/volumes",
                {"q": f"isbn:{isbn}", "maxResults": 1},
                "Google Books API error"
            )

    def test_search_by_title_author(self):
        """Тест поиска книги по названию и автору."""
        with mock.patch.object(self.service, '_make_request') as mock_request:
            mock_request.return_value = {
                'items': [{
                    'volumeInfo': {
                        'title': 'Test Book',
                        'authors': ['Test Author'],
                        'industryIdentifiers': [{'type': 'ISBN_13', 'identifier': '1234567890123'}],
                        'description': 'Test description',
                        'publishedDate': '2020-01-01',
                        'pageCount': 200,
                        'language': 'en',
                        'categories': ['Fiction'],
                        'imageLinks': {'thumbnail': 'http://example.com/thumbnail.jpg'},
                        'previewLink': 'http://example.com/preview',
                        'averageRating': 4.5,
                        'ratingsCount': 100
                    }
                }]
            }
            result = self.service.search_books(title='Test Book', author='Test Author')
            self.assertIsInstance(result, list)
            self.assertTrue(len(result) > 0)
            self.assertEqual(result[0].title, 'Test Book')
            self.assertEqual(result[0].author, 'Test Author')
            mock_request.assert_called_once_with(
                "https://www.googleapis.com/books/v1/volumes",
                {"q": "intitle:Test Book+inauthor:Test Author", "maxResults": 5},
                "Google Books API error"
            )

    def test_get_book_data(self):
        """Тест получения данных о книге по ISBN."""
        isbn = "9781234567897"
        with mock.patch.object(self.service, '_make_request') as mock_request:
            mock_request.return_value = {
                'items': [{
                    'volumeInfo': {
                        'title': 'Test Book',
                        'authors': ['Test Author'],
                        'industryIdentifiers': [{'type': 'ISBN_13', 'identifier': isbn}],
                        'description': 'Test description',
                        'publishedDate': '2020-01-01',
                        'pageCount': 200,
                        'language': 'en',
                        'categories': ['Fiction'],
                        'imageLinks': {'thumbnail': 'http://example.com/thumbnail.jpg'},
                        'previewLink': 'http://example.com/preview',
                        'averageRating': 4.5,
                        'ratingsCount': 100
                    }
                }]
            }
            result = self.service.get_book_data(isbn)
            self.assertIsNotNone(result)
            self.assertEqual(result.isbn, isbn)
            self.assertEqual(result.title, 'Test Book')
            self.assertEqual(result.author, 'Test Author')
            self.assertEqual(result.source, 'Google Books')

    def test_caching(self):
        """Тест кэширования запросов."""
        with mock.patch.object(self.service, '_make_request') as mock_make_request:
            mock_make_request.return_value = MOCK_GOOGLE_BOOKS_RESPONSE
            result1 = self.service.get_book_data("9781234567897")
            self.assertEqual(mock_make_request.call_count, 1)
            mock_make_request.reset_mock()
            result2 = self.service.get_book_data("9781234567897")
            self.assertEqual(mock_make_request.call_count, 0)
            self.assertEqual(result1.title, result2.title)


class OpenLibraryServiceTests(TestCase):
    """Тесты для Open Library API."""

    def setUp(self):
        """Настройка тестовых данных."""
        self.service = OpenLibraryService()
        cache.clear()

    def test_search_by_isbn(self):
        """Тест поиска книги по ISBN."""
        isbn = "9876543210987"

        def mock_request_side_effect(url, params, error_msg):
            if 'api/books' in url and 'bibkeys' in params:
                return {
                    f'ISBN:{isbn}': {
                        'title': 'Test Book',
                        'authors': [{'key': '/authors/OL1A'}],
                        'publish_date': '2020',
                        'description': 'Test description',
                        'number_of_pages': 200,
                        'languages': [{'key': '/languages/eng'}],
                        'subjects': [{'key': '/subjects/fiction'}],
                        'covers': [12345],
                        'identifiers': {
                            'isbn_13': [isbn],
                            'isbn_10': ['1234567890']
                        }
                    }
                }
            elif '/authors/OL1A' in url:
                return {'name': 'Test Author'}
            return {}

        with mock.patch.object(self.service, '_make_request', side_effect=mock_request_side_effect):
            result = self.service.search_books(isbn=isbn)
            self.assertIsInstance(result, list)
            self.assertTrue(len(result) > 0)
            self.assertEqual(result[0].isbn, isbn)
            self.assertEqual(result[0].title, 'Test Book')

    def test_search_by_title_author(self):
        """Тест поиска книги по названию и автору."""
        isbn = "9876543210987"

        def mock_request_side_effect(url, params, error_msg):
            if 'search.json' in url:
                return {
                    'docs': [{
                        'title': 'Test Book',
                        'author_name': ['Test Author'],
                        'isbn': [isbn],
                        'first_publish_year': 2020
                    }]
                }
            elif f'isbn/{isbn}' in url:
                return {
                    'title': 'Test Book',
                    'authors': [{'key': '/authors/OL1A'}],
                    'publish_date': '2020',
                    'description': 'Test description',
                    'number_of_pages': 200,
                    'languages': [{'key': '/languages/eng'}],
                    'subjects': [{'key': '/subjects/fiction'}],
                    'covers': [12345]
                }
            elif '/authors/OL1A' in url:
                return {'name': 'Test Author'}
            return {}

        with mock.patch.object(self.service, '_make_request', side_effect=mock_request_side_effect):
            result = self.service.search_books(title='Test Book', author='Test Author')
            self.assertIsInstance(result, list)
            self.assertTrue(len(result) > 0)
            self.assertEqual(result[0].title, 'Test Book')
            self.assertEqual(result[0].author, 'Test Author')

    def test_get_book_data(self):
        """Тест получения данных о книге по ISBN."""
        isbn = "9781234567897"

        def mock_request_side_effect(url, params, error_msg):
            if f'isbn/{isbn}' in url:
                return {
                    'title': 'Test Book',
                    'authors': [{'key': '/authors/OL1A'}],
                    'publish_date': '2020',
                    'description': 'Test description',
                    'number_of_pages': 200,
                    'languages': [{'key': '/languages/eng'}],
                    'subjects': [{'key': '/subjects/fiction'}],
                    'covers': [12345]
                }
            elif '/authors/OL1A' in url:
                return {'name': 'Test Author'}
            return {}

        with mock.patch.object(self.service, '_make_request', side_effect=mock_request_side_effect):
            result = self.service.get_book_data(isbn)
            self.assertIsNotNone(result)
            self.assertEqual(result.isbn, isbn)
            self.assertEqual(result.title, 'Test Book')
            self.assertEqual(result.author, 'Test Author')
            self.assertEqual(result.source, 'Open Library')

    def test_caching(self):
        """Тест кэширования запросов."""
        with mock.patch.object(self.service, '_make_request') as mock_make_request:
            mock_make_request.return_value = MOCK_OPEN_LIBRARY_RESPONSE
            result1 = self.service.get_book_data("9781234567897")
            self.assertEqual(mock_make_request.call_count, 1)
            mock_make_request.reset_mock()
            result2 = self.service.get_book_data("9781234567897")
            self.assertEqual(mock_make_request.call_count, 0)
            self.assertEqual(result1.title, result2.title)


class NYTimesServiceTests(TestCase):
    """Тесты для NY Times API."""

    def setUp(self):
        """Настройка тестовых данных."""
        self.service = NYTimesService()
        self.service.api_key = 'test_key'  # Устанавливаем API ключ напрямую для тестов
        cache.clear()

    def test_get_book_review(self):
        """Тест получения обзора книги."""
        with mock.patch.object(self.service, '_make_request') as mock_make_request:
            mock_make_request.return_value = MOCK_NY_TIMES_RESPONSE
            result = self.service.get_book_review("9781234567897")

            # Проверяем результат
            self.assertIsNotNone(result)
            self.assertEqual(result, "Test book review summary")
            mock_make_request.assert_called_once_with(
                "https://api.nytimes.com/svc/books/v3/reviews.json",
                {'isbn': "9781234567897", 'api-key': 'test_key'},
                "NY Times API error",
                default_return={"num_results": 0}
            )

    def test_get_book_review_no_results(self):
        """Тест получения обзора книги когда нет результатов."""
        with mock.patch.object(self.service, '_make_request') as mock_make_request:
            mock_make_request.return_value = {"num_results": 0}
            result = self.service.get_book_review("9781234567897")
            self.assertIsNone(result)

    def test_get_book_review_no_api_key(self):
        """Тест получения обзора книги без API ключа."""
        service = NYTimesService()
        service.api_key = None
        result = service.get_book_review("9781234567897")
        self.assertIsNone(result)

    def test_caching(self):
        """Тест кэширования запросов."""
        with mock.patch.object(self.service, '_make_request') as mock_make_request:
            mock_make_request.return_value = MOCK_NY_TIMES_RESPONSE
            result1 = self.service.get_book_review("9781234567897")
            self.assertEqual(mock_make_request.call_count, 1)
            mock_make_request.reset_mock()
            result2 = self.service.get_book_review("9781234567897")
            self.assertEqual(mock_make_request.call_count, 0)
            self.assertEqual(result1, result2)


class BookEnrichmentServiceTests(TestCase):
    """Тесты для сервиса обогащения данных книги."""

    def setUp(self):
        """Настройка тестовых данных."""
        cache.clear()
        self.service = BookEnrichmentService()

    def tearDown(self):
        """Очистка после тестов."""
        cache.clear()

    def test_enrich_book_data_google_success(self):
        """Тест обогащения данных с успешным результатом от Google Books."""
        isbn = "1234567890123"
        google_data = BookEnrichmentData(
            isbn=isbn,
            title="Google Test Book",
            author="Google Test Author",
            published_date="2023-01-01",
            source="Google Books"
        )

        with mock.patch.object(self.service.google_books, 'search_books') as mock_google_search:
            mock_google_search.return_value = [google_data]
            result = self.service.enrich_book_data(isbn)
            self.assertIsNotNone(result)
            self.assertEqual(result.title, 'Google Test Book')
            self.assertEqual(result.source, 'Google Books')
            mock_google_search.assert_called_once_with(query="", isbn=isbn)

    def test_enrich_book_data_open_library_fallback(self):
        """Тест обогащения данных с откатом на Open Library, если Google не вернул данных."""
        isbn = "9876543210987"
        ol_data = BookEnrichmentData(
            isbn=isbn,
            title="Open Library Test Book",
            author="Open Library Test Author",
            published_date="2023-01-01",
            source="Open Library"
        )

        with mock.patch.object(self.service.google_books, 'search_books') as mock_google_search, \
                mock.patch.object(self.service.open_library, 'search_books') as mock_ol_search:
            mock_google_search.return_value = []
            mock_ol_search.return_value = [ol_data]
            result = self.service.enrich_book_data(isbn)
            self.assertIsNotNone(result)
            self.assertEqual(result.title, 'Open Library Test Book')
            self.assertEqual(result.source, 'Open Library')
            mock_google_search.assert_called_once_with(query="", isbn=isbn)
            mock_ol_search.assert_called_once_with(query="", isbn=isbn)

    def test_enrich_book_data_no_results(self):
        """Тест обогащения данных когда нет результатов ни от одного источника."""
        isbn = "0000000000000"

        with mock.patch.object(self.service.google_books, 'search_books') as mock_google_search, \
                mock.patch.object(self.service.open_library, 'search_books') as mock_ol_search:
            mock_google_search.return_value = []
            mock_ol_search.return_value = []
            result = self.service.enrich_book_data(isbn)
            self.assertIsNone(result)

    def test_search_books(self):
        """Тест поиска книг."""
        query = "test book"
        google_data = BookEnrichmentData(
            isbn="1234567890123",
            title="Google Test Book",
            author="Google Test Author",
            published_date="2023-01-01",
            source="Google Books"
        )
        ol_data = BookEnrichmentData(
            isbn="9876543210987",
            title="Open Library Test Book",
            author="Open Library Test Author",
            published_date="2023-01-01",
            source="Open Library"
        )

        with mock.patch.object(self.service.google_books, 'search_books') as mock_google_search, \
                mock.patch.object(self.service.open_library, 'search_books') as mock_ol_search:
            mock_google_search.return_value = [google_data]
            mock_ol_search.return_value = [ol_data]
            result = self.service.search_books(query)
            self.assertIsNotNone(result)
            self.assertEqual(len(result), 2)
            self.assertEqual(result[0].title, 'Google Test Book')
            self.assertEqual(result[1].title, 'Open Library Test Book')

    def test_caching(self):
        """Тест кэширования запросов в BookEnrichmentService."""
        isbn = "1234567890123"
        google_data = BookEnrichmentData(
            isbn=isbn,
            title="Google Test Book",
            author="Google Test Author",
            published_date="2023-01-01",
            source="Google Books"
        )

        with mock.patch.object(self.service.google_books, 'search_books') as mock_google_search:
            mock_google_search.return_value = [google_data]

            # Первый запрос - должен пойти к API
            result1 = self.service.enrich_book_data(isbn)
            self.assertIsNotNone(result1)
            self.assertEqual(result1.title, "Google Test Book")
            self.assertEqual(mock_google_search.call_count, 1)

            # Сбрасываем мок для проверки кэширования
            mock_google_search.reset_mock()

            # Второй запрос - должен взять из кэша
            result2 = self.service.enrich_book_data(isbn)
            self.assertIsNotNone(result2)
            self.assertEqual(result2.title, "Google Test Book")
            self.assertEqual(mock_google_search.call_count, 0)  # Вызов не увеличился, значит из кэша
