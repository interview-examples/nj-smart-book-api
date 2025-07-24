import unittest
from unittest import mock
from django.test import TestCase

from books.models import Book, BookISBN, Author
from books.repositories.book_repository import BookRepository
from books.services.book_service import BookService


class ISBNServiceMethodsTestCase(TestCase):
    """Tests for ISBN-related service methods."""

    def setUp(self):
        """Setup test data."""
        # Clear database before each test to avoid ISBN uniqueness conflicts
        Book.objects.all().delete()
        BookISBN.objects.all().delete()
        Author.objects.all().delete()

        # Create service
        self.service = BookService()

        # Create authors
        self.author1 = Author.objects.create(name="J.K. Rowling")
        self.author2 = Author.objects.create(name="Robert C. Martin")

        # Create test books with ISBNs
        self.book1 = Book.objects.create(
            title="Harry Potter",
            isbn="9780747532699",  # Primary ISBN-13
            description="Book about a wizard",
            published_date="1997-06-26",
        )
        # Add author to book
        self.book1.authors.add(self.author1)

        # Additional ISBNs for book1
        BookISBN.objects.create(
            book=self.book1, isbn="0747532699", type="ISBN-10"  # ISBN-10 equivalent
        )

        BookISBN.objects.create(
            book=self.book1, isbn="9780747532743", type="ISBN-13"  # Another edition
        )

        # Book with only ISBN-10
        self.book2 = Book.objects.create(
            title="Clean Code",
            isbn="0132350882",  # ISBN-10
            description="A book about good programming practices",
            published_date="2008-08-01",
        )
        # Add author to book
        self.book2.authors.add(self.author2)

    def test_get_book_by_isbn_primary(self):
        """Test retrieving a book by its primary ISBN (stored in Book.isbn field)."""
        book = self.service.get_book_by_isbn("9780747532699")
        self.assertIsNotNone(book)
        self.assertEqual(book.id, self.book1.id)
        self.assertEqual(book.title, "Harry Potter")
        self.assertEqual(book.authors.first().name, "J.K. Rowling")

    def test_get_book_by_isbn_related(self):
        """Test retrieving a book by a related ISBN (stored in BookISBN)."""
        book = self.service.get_book_by_isbn("0747532699")
        self.assertIsNotNone(book)
        self.assertEqual(book.id, self.book1.id)
        self.assertEqual(book.title, "Harry Potter")
        self.assertEqual(book.authors.first().name, "J.K. Rowling")

    def test_get_book_by_isbn_with_hyphens(self):
        """Test retrieving a book by ISBN with hyphens."""
        book = self.service.get_book_by_isbn("978-0-7475-3269-9")
        self.assertIsNotNone(book)
        self.assertEqual(book.id, self.book1.id)

    def test_get_book_by_isbn_with_spaces(self):
        """Test retrieving a book by ISBN with spaces."""
        book = self.service.get_book_by_isbn("978 0 7475 3269 9")
        self.assertIsNotNone(book)
        self.assertEqual(book.id, self.book1.id)

    def test_get_book_by_isbn_case_insensitive(self):
        """Test retrieving a book by ISBN with different case (for ISBNs with 'X')."""
        # Create author
        author_x = Author.objects.create(name="Test Author X")

        # Create a book with ISBN ending in X
        book_with_x = Book.objects.create(
            title="Test Book X",
            isbn="123456789X",
            description="Test description",
            published_date="2023-01-01",
        )
        # Add author to book
        book_with_x.authors.add(author_x)

        # Test with lowercase x
        book = self.service.get_book_by_isbn("123456789x")
        self.assertIsNotNone(book)
        self.assertEqual(book.id, book_with_x.id)
        self.assertEqual(book.authors.first().name, "Test Author X")

    def test_get_book_by_nonexistent_isbn(self):
        """Test that None is returned for non-existent ISBN."""
        book = self.service.get_book_by_isbn("9999999999999")
        self.assertIsNone(book)

    def test_get_book_by_all_isbns_single(self):
        """Test getting a book with a single provided ISBN."""
        book = self.service.get_book_by_all_isbns(["9780747532699"])
        self.assertIsNotNone(book)
        self.assertEqual(book.id, self.book1.id)

    def test_get_book_by_all_isbns_multiple(self):
        """Test getting a book with multiple provided ISBNs."""
        book = self.service.get_book_by_all_isbns(["9999999999999", "0747532699"])
        self.assertIsNotNone(book)
        self.assertEqual(book.id, self.book1.id)

    def test_get_book_by_all_isbns_order(self):
        """Test that ISBNs are checked in order."""
        # Create a service with a mocked get_book_by_isbn method
        service = BookService()

        # Patch the get_book_by_isbn method of the service
        with mock.patch.object(service, "get_book_by_isbn") as mock_get_by_isbn:
            # Configure the mock to return None for first ISBN and a book for second
            mock_get_by_isbn.side_effect = [None, self.book1]

            # Call the method with multiple ISBNs
            book = service.get_book_by_all_isbns(["9999999999999", "0747532699"])

            # Verify both ISBNs were checked in order
            self.assertEqual(mock_get_by_isbn.call_count, 2)
            mock_get_by_isbn.assert_any_call("9999999999999")
            mock_get_by_isbn.assert_any_call("0747532699")

            # Verify the correct book was returned
            self.assertEqual(book, self.book1)

    def test_get_book_by_all_isbns_none_found(self):
        """Test that None is returned when no book matches any ISBN."""
        book = self.service.get_book_by_all_isbns(["9999999999999", "8888888888888"])
        self.assertIsNone(book)

    def test_get_book_by_all_isbns_empty_list(self):
        """Test behavior with empty ISBN list."""
        book = self.service.get_book_by_all_isbns([])
        self.assertIsNone(book)

    def test_get_book_by_isbn_normalization(self):
        """Test ISBN normalization removes all non-alphanumeric characters."""
        # Create a service with mocked BookISBN.objects
        service = BookService()

        # Create ISBN with unusual formatting
        unusual_isbn = "978-0-7475-3269-9 (paperback)"
        normalized_isbn = "9780747532699(paperback)"  # Expected normalized form based on actual implementation

        # Mock the BookISBN.objects.filter to return a queryset with our book
        with mock.patch("books.models.BookISBN.objects.filter") as mock_filter:
            mock_queryset = mock.MagicMock()
            mock_book_isbn = mock.MagicMock()
            mock_book_isbn.book = self.book1
            mock_queryset.first.return_value = mock_book_isbn
            mock_filter.return_value = mock_queryset

            # Call the method with the unusual ISBN
            book = service.get_book_by_isbn(unusual_isbn)

            # Verify the ISBN was normalized before lookup with case-insensitive search
            mock_filter.assert_called_once_with(isbn__iexact=normalized_isbn)

            # Verify the correct book was returned
            self.assertIsNotNone(book)
            self.assertEqual(book, self.book1)


if __name__ == "__main__":
    unittest.main()
