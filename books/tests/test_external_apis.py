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
        with mock.patch.object(self.service, '_make_request') as mock_make_request:
            mock_make_request.return_value = MOCK_GOOGLE_BOOKS_RESPONSE
            result = self.service.get_book_data("9781234567897")

            # Проверяем структуру и содержимое результата
            self.assertIsNotNone(result)
            self.assertEqual(result.title, "A Test-Book for Students")
            self.assertEqual(result.author, "Test Author")
            self.assertEqual(result.isbn, "9781234567897")
            mock_make_request.assert_called_once_with(
                "https://www.googleapis.com/books/v1/volumes",
                {'q': 'isbn:9781234567897', 'key': None},
                "Google Books API error"
            )

    def test_search_by_title_author(self):
        """Тест поиска книги по названию и автору."""
        with mock.patch('requests.get') as mock_get:
            mock_response = mock.Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = MOCK_GOOGLE_BOOKS_SEARCH_RESPONSE
            mock_get.return_value = mock_response
            result = self.service.search_books("Test Book Test Author")

            # Проверяем результат
            self.assertTrue(len(result) > 0)
            self.assertEqual(result[0].title, "A Test-Book for Students")
            mock_get.assert_called_once()

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
        with mock.patch.object(self.service, '_make_request') as mock_make_request:
            mock_make_request.return_value = MOCK_OPEN_LIBRARY_RESPONSE
            result = self.service.get_book_data("9781234567897")

            # Проверяем результат
            self.assertIsNotNone(result)
            self.assertEqual(result.title, "Test Book")
            self.assertEqual(result.author, "Test Author")
            mock_make_request.assert_called_once_with(
                "https://openlibrary.org/api/books",
                {'bibkeys': 'ISBN:9781234567897', 'format': 'json', 'jscmd': 'data'},
                "Open Library API error"
            )

    def test_search_by_title_author(self):
        """Тест поиска книги по названию и автору."""
        with mock.patch('requests.get') as mock_get:
            mock_response = mock.Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = MOCK_OPEN_LIBRARY_SEARCH_RESPONSE
            mock_get.return_value = mock_response
            result = self.service.search_books("Test Book Test Author")

            # Проверяем результат
            self.assertIsNotNone(result)
            self.assertTrue(len(result) > 0)
            self.assertEqual(result[0].title, "Test Book")
            mock_get.assert_called_once()

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
        self.google_patcher = mock.patch.object(self.service.google_books, 'get_book_data')
        self.ol_patcher = mock.patch.object(self.service.open_library, 'get_book_data')
        self.nyt_patcher = mock.patch.object(self.service.ny_times, 'get_book_review')
        self.mock_google_get_book_data = self.google_patcher.start()
        self.mock_ol_get_book_data = self.ol_patcher.start()
        self.mock_nyt_get_book_review = self.nyt_patcher.start()

        self.google_data = BookEnrichmentData(
            isbn="9781234567897",
            title="Google Test Book",
            author="Google Test Author",
            published_date="2023-01-01",
            source="Google Books"
        )
        self.mock_google_get_book_data.return_value = self.google_data

        self.ol_data = BookEnrichmentData(
            isbn="9781234567897",
            title="Open Library Test Book",
            author="Open Library Test Author",
            published_date="2023-01-01",
            source="Open Library"
        )
        self.mock_ol_get_book_data.return_value = self.ol_data

        self.mock_nyt_get_book_review.return_value = "Test NY Times Review"

    def tearDown(self):
        """Очистка после тестов."""
        self.google_patcher.stop()
        self.ol_patcher.stop()
        self.nyt_patcher.stop()
        cache.clear()

    def test_enrich_book_data_google_success(self):
        """Тест обогащения данных с успешным результатом от Google Books."""
        result = self.service.enrich_book_data("9781234567897")
        self.assertEqual(result.title, "Google Test Book")
        self.assertEqual(result.author, "Google Test Author")
        self.assertEqual(result.ny_times_review, "Test NY Times Review")
        self.assertEqual(self.mock_google_get_book_data.call_count, 1)
        self.assertEqual(self.mock_ol_get_book_data.call_count, 0)  # Open Library не вызывается, так как Google вернул данные
        self.assertEqual(self.mock_nyt_get_book_review.call_count, 1)

    def test_enrich_book_data_open_library_fallback(self):
        """Тест обогащения данных с откатом на Open Library, если Google не вернул данных."""
        self.mock_google_get_book_data.return_value = None
        result = self.service.enrich_book_data("9781234567897")
        self.assertEqual(result.title, "Open Library Test Book")
        self.assertEqual(result.author, "Open Library Test Author")
        self.assertEqual(result.ny_times_review, "Test NY Times Review")
        self.assertEqual(self.mock_google_get_book_data.call_count, 1)
        self.assertEqual(self.mock_ol_get_book_data.call_count, 1)
        self.assertEqual(self.mock_nyt_get_book_review.call_count, 1)

    def test_caching(self):
        """Тест кэширования запросов в BookEnrichmentService."""
        result1 = self.service.enrich_book_data("9781234567897")
        self.assertEqual(self.mock_google_get_book_data.call_count, 1)
        self.assertEqual(self.mock_ol_get_book_data.call_count, 0)
        self.assertEqual(self.mock_nyt_get_book_review.call_count, 1)

        self.mock_google_get_book_data.reset_mock()
        self.mock_ol_get_book_data.reset_mock()
        self.mock_nyt_get_book_review.reset_mock()

        result2 = self.service.enrich_book_data("9781234567897")
        self.assertEqual(self.mock_google_get_book_data.call_count, 0)
        self.assertEqual(self.mock_ol_get_book_data.call_count, 0)
        self.assertEqual(self.mock_nyt_get_book_review.call_count, 0)
        self.assertEqual(result1.title, result2.title)
        self.assertEqual(result1.ny_times_review, result2.ny_times_review)
