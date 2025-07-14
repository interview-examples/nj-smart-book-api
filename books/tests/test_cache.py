import unittest
from unittest import mock
from django.core.cache import cache
from django.test import override_settings
from books.services.external_apis import GoogleBooksService, OpenLibraryService, NYTimesService, BookEnrichmentService, BookEnrichmentData

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
            self.assertEqual(result1.title, result2.title)

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
            self.assertEqual(result1.title, result2.title)

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
        cache.clear()
        # Создаем сервис до патчинга
        self.enrichment_service = BookEnrichmentService()
        # Патчим методы экземпляров
        self.google_patcher = mock.patch.object(self.enrichment_service.google_books, 'get_book_data')
        self.ol_patcher = mock.patch.object(self.enrichment_service.open_library, 'get_book_data')
        self.nyt_patcher = mock.patch.object(self.enrichment_service.ny_times, 'get_book_review')
        self.mock_google_get_book_data = self.google_patcher.start()
        self.mock_ol_get_book_data = self.ol_patcher.start()
        self.mock_nyt_get_book_review = self.nyt_patcher.start()

        google_data = BookEnrichmentData(
            isbn="9781234567890",
            title="Mocked Google Book",
            author="Test Google Author",
            published_date="2022-06-01",
            source="Google Books"
        )
        self.mock_google_get_book_data.return_value = google_data

        ol_data = BookEnrichmentData(
            isbn="9781234567890",
            title="Mocked Open Library Book",
            author="Test OL Author",
            published_date="2022-06-01",
            source="Open Library"
        )
        self.mock_ol_get_book_data.return_value = ol_data

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
        self.assertEqual(self.mock_ol_get_book_data.call_count, 0)
        self.assertEqual(self.mock_nyt_get_book_review.call_count, 1)

        # Сбрасываем все счетчики
        self.mock_google_get_book_data.reset_mock()
        self.mock_ol_get_book_data.reset_mock()
        self.mock_nyt_get_book_review.reset_mock()

        result2 = self.enrichment_service.enrich_book_data(TEST_ISBN)
        self.assertEqual(self.mock_google_get_book_data.call_count, 0)
        self.assertEqual(self.mock_ol_get_book_data.call_count, 0)
        self.assertEqual(self.mock_nyt_get_book_review.call_count, 0)

        # Проверяем, что результаты идентичны
        self.assertEqual(result1.isbn, result2.isbn)
        self.assertEqual(result1.title, result2.title)
        self.assertEqual(result1.author, result2.author)
        self.assertEqual(result1.published_date, result2.published_date)
        self.assertEqual(result1.ny_times_review, result2.ny_times_review)
