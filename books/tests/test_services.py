from django.test import TestCase
from unittest.mock import patch
from books.models import Book, BookISBN
from books.services.book_service import BookService
from books.services.enrichment_service import EnrichmentService
from books.services.external_apis import BookEnrichmentData

class BookServiceTest(TestCase):
    def setUp(self):
        self.book_service = BookService()
        self.book = Book.objects.create(
            title="Test Book",
            author="Test Author",
            isbn="9780201896831",
            published_date="2023-01-01"
        )
        BookISBN.objects.create(book=self.book, isbn="9780201896831", type="ISBN-13")
        BookISBN.objects.create(book=self.book, isbn="0201896834", type="ISBN-10")

    def test_get_book_by_isbn(self):
        """Тестирование получения книги по ISBN."""
        retrieved_book = self.book_service.get_book_by_isbn("9780201896831")
        self.assertEqual(retrieved_book, self.book)

        retrieved_book_by_isbn10 = self.book_service.get_book_by_isbn("0201896834")
        self.assertEqual(retrieved_book_by_isbn10, self.book)

        non_existent_book = self.book_service.get_book_by_isbn("9780132350884")
        self.assertIsNone(non_existent_book)

class EnrichmentServiceTest(TestCase):
    def setUp(self):
        self.book_service = BookService()
        self.enrichment_service = EnrichmentService(self.book_service)
        self.book = Book.objects.create(
            title="Test Book",
            author="Test Author",
            isbn="9780201896831",
            published_date="2023-01-01"
        )
        BookISBN.objects.create(book=self.book, isbn="9780201896831", type="ISBN-13")

    @patch('books.services.external_apis.BookEnrichmentService.enrich_book_data')
    def test_enrich_book_by_isbn_update(self, mock_enrich):
        """Тестирование обновления книги с несколькими ISBN."""
        mock_enrich.return_value = BookEnrichmentData(
            isbn="9780201896831",
            title="Updated Test Book",
            author="Updated Test Author",
            published_date="2023-01-15",
            description="Updated book description",
            industryIdentifiers=[
                {"type": "ISBN-13", "identifier": "9780201896831"},
                {"type": "ISBN-10", "identifier": "0201896834"}
            ]
        )
        result = self.enrichment_service.enrich_book_by_isbn("9780201896831")
        self.assertIsNotNone(result)
        self.assertEqual(result.title, "Updated Test Book")
        self.assertEqual(result.isbns.count(), 2)

    @patch('books.services.external_apis.BookEnrichmentService.enrich_book_data')
    def test_enrich_book_by_isbn_create(self, mock_enrich):
        """Тестирование создания новой книги с обогащенными данными."""
        mock_enrich.return_value = BookEnrichmentData(
            isbn="9780132350884",
            title="New Test Book",
            author="New Test Author",
            published_date="2023-02-20",
            description="New book description",
            industryIdentifiers=[
                {"type": "ISBN-13", "identifier": "9780132350884"},
                {"type": "ISBN-10", "identifier": "0132350882"}
            ]
        )
        result = self.enrichment_service.enrich_book_by_isbn("9780132350884")
        self.assertIsNotNone(result)
        self.assertEqual(result.title, "New Test Book")
        new_book = Book.objects.get(isbn="9780132350884")
        self.assertEqual(new_book.isbns.count(), 2)

    @patch('books.services.external_apis.BookEnrichmentService.enrich_book_data')
    def test_enrich_book_by_isbn_create_without_description(self, mock_enrich):
        """Тестирование создания новой книги с пустым описанием."""
        mock_enrich.return_value = BookEnrichmentData(
            isbn="9780134494166",
            title="New Test Book",
            author="New Test Author",
            published_date="2023-02-20",
            description="",
            industryIdentifiers=[
                {"type": "ISBN-13", "identifier": "9780134494166"}
            ]
        )
        result = self.enrichment_service.enrich_book_by_isbn("9780134494166")
        self.assertIsNotNone(result)
        self.assertEqual(result.title, "New Test Book")
        self.assertEqual(result.description, "")
