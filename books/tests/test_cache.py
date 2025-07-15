import unittest
from unittest import mock
from django.core.cache import cache
from django.test import override_settings
from books.services.apis.google_books import GoogleBooksService
from books.services.apis.open_library import OpenLibraryService
from books.services.apis.nytimes import NYTimesService
from books.services.enrichment.service import BookEnrichmentService
from books.services.models.data_models import BookEnrichmentData

MOCK_GOOGLE_BOOKS_RESPONSE = {
    "kind": "books#volumes",
    "totalItems": 1,
    "items": [
        {
            "volumeInfo": {
                "title": "Cached Google Book",
                "authors": ["Test Author"],
                "publishedDate": "2022-06-01",
                "industryIdentifiers": [
                    {"type": "ISBN_13", "identifier": "9781234567890"}
                ]
            }
        }
    ]
}

MOCK_OPEN_LIBRARY_RESPONSE = {
    "ISBN:9781234567897": {
        "title": "Cached Open Library Book",
        "authors": [{"name": "Test Author"}],
        "publish_date": "2022-06-01"
    }
}

MOCK_NY_TIMES_RESPONSE = {
    "num_results": 1,
    "results": [
        {
            "summary": "This is a mocked review",
            "book_details": [
                {
                    "title": "Cached NY Times Book",
                    "author": "Test Author",
                    "primary_isbn13": "9781234567897"
                }
            ]
        }
    ]
}

class ExternalAPIsCacheTests(unittest.TestCase):
    """Тесты для проверки кэширования запросов к внешним API."""
    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_google_books_caching(self):
        """Тест кэширования запросов к Google Books API."""
        service = GoogleBooksService()
        with mock.patch.object(service, '_make_request') as mock_make_request:
            mock_make_request.return_value = MOCK_GOOGLE_BOOKS_RESPONSE
            TEST_ISBN = "9781234567890"
            result1 = service.get_book_data(TEST_ISBN)
            self.assertEqual(mock_make_request.call_count, 1)
            mock_make_request.reset_mock()
            result2 = service.get_book_data(TEST_ISBN)
            self.assertEqual(mock_make_request.call_count, 0)
            self.assertEqual(result1.get('title'), result2.get('title'))

    def test_open_library_caching(self):
        """Тест кэширования запросов к Open Library API."""
        service = OpenLibraryService()
        with mock.patch.object(service, '_make_request') as mock_make_request:
            mock_make_request.return_value = MOCK_OPEN_LIBRARY_RESPONSE
            TEST_ISBN = "9781234567897"
            result1 = service.get_book_data(TEST_ISBN)
            self.assertEqual(mock_make_request.call_count, 1)
            mock_make_request.reset_mock()
            result2 = service.get_book_data(TEST_ISBN)
            self.assertEqual(mock_make_request.call_count, 0)
            self.assertEqual(result1.get('title'), result2.get('title'))

    @override_settings(NY_TIMES_API_KEY='test_key')
    def test_ny_times_caching(self):
        """Тест кэширования запросов к NY Times API."""
        service = NYTimesService()
        with mock.patch.object(service, '_make_request') as mock_make_request:
            mock_make_request.return_value = MOCK_NY_TIMES_RESPONSE
            TEST_ISBN = "9781234567897"
            result1 = service.get_book_review(TEST_ISBN)
            self.assertEqual(mock_make_request.call_count, 1)
            mock_make_request.reset_mock()
            result2 = service.get_book_review(TEST_ISBN)
            self.assertEqual(mock_make_request.call_count, 0)
            self.assertEqual(result1, result2)

class EnrichmentServiceCacheTests(unittest.TestCase):
    """Тесты для проверки кэширования BookEnrichmentService."""

    def setUp(self):
        self.enrichment_service = BookEnrichmentService()
        cache.clear()

        # Патчим метод get_book_data в GoogleBooksService
        self.google_patcher = mock.patch.object(
            self.enrichment_service.google_books,
            'get_book_data',
            autospec=True
        )
        self.mock_google_get_book_data = self.google_patcher.start()
        # Возвращаем данные о книге, которые будут преобразованы в BookEnrichmentData
        self.mock_google_get_book_data.return_value = {
            "title": "Mocked Google Book",
            "authors": ["Test Google Author"],
            "publishedDate": "2022-05-15",
            "industryIdentifiers": [
                {"type": "ISBN_13", "identifier": "9781234567890"}
            ]
        }

        # Патчим метод get_book_data в OpenLibraryService
        self.ol_patcher = mock.patch.object(
            self.enrichment_service.open_library,
            'get_book_data',
            autospec=True
        )
        self.mock_ol_get_book_data = self.ol_patcher.start()
        self.mock_ol_get_book_data.return_value = {
            "title": "Mocked Open Library Book",
            "authors": [{"name": "Test OL Author"}],
            "publish_date": "2022-06-01",
            "identifiers": {"isbn_13": ["9781234567890"]}
        }

        # Патчим метод get_book_review в NYTimesService
        self.nyt_patcher = mock.patch.object(
            self.enrichment_service.ny_times,
            'get_book_review',
            autospec=True
        )
        self.mock_nyt_get_book_review = self.nyt_patcher.start()
        self.mock_nyt_get_book_review.return_value = "This is a mocked NY Times review."

    def tearDown(self):
        self.google_patcher.stop()
        self.ol_patcher.stop()
        self.nyt_patcher.stop()
        cache.clear()

    def test_enrichment_service_caching(self):
        """Тест кэширования для сервиса обогащения данных."""
        TEST_ISBN = "9781234567890"
        result1 = self.enrichment_service.enrich_book_data(TEST_ISBN)
        self.assertEqual(self.mock_google_get_book_data.call_count, 1)
        self.assertEqual(self.mock_ol_get_book_data.call_count, 1)
        self.assertEqual(self.mock_nyt_get_book_review.call_count, 1)

        # Сбрасываем все счетчики
        self.mock_google_get_book_data.reset_mock()
        self.mock_ol_get_book_data.reset_mock()
        self.mock_nyt_get_book_review.reset_mock()

        result2 = self.enrichment_service.enrich_book_data(TEST_ISBN)
        self.assertEqual(self.mock_google_get_book_data.call_count, 0)
        self.assertEqual(self.mock_ol_get_book_data.call_count, 0)
        self.assertEqual(self.mock_nyt_get_book_review.call_count, 0)
