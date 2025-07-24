import uuid
from django.test import TestCase
from django.core.exceptions import ValidationError
from books.models import Book, BookISBN, Author


class BookModelTests(TestCase):
    """Tests for the Book model."""

    def setUp(self):
        """Set up test data."""
        self.book_data = {
            "title": "Test Book",
            "isbn": "9780201896831",
            "description": "Test description of the book",
            "published_date": "2023-01-01",
        }
        # Create an author separately since it's now a M2M relationship
        self.author = Author.objects.create(name="Test Author")

    def test_create_book(self):
        """Test creating a book with valid data."""
        book = Book.objects.create(**self.book_data)
        # Add author after creation since it's a M2M field
        book.authors.add(self.author)

        self.assertEqual(book.title, self.book_data["title"])
        self.assertEqual(book.authors.first().name, "Test Author")
        self.assertEqual(book.isbn, self.book_data["isbn"])
        self.assertEqual(book.description, self.book_data["description"])
        self.assertEqual(str(book.published_date), self.book_data["published_date"])
        self.assertIsNotNone(book.id)

    def test_string_representation(self):
        """Test the string representation of the model."""
        book = Book.objects.create(**self.book_data)
        book.authors.add(self.author)
        # String representation should match the implementation in the Book model
        expected_string = f"{self.book_data['title']} (ID: {book.id})"
        self.assertEqual(str(book), expected_string)

    def test_isbn_validation(self):
        """Test ISBN validation."""
        # Invalid ISBN (wrong length)
        invalid_data = self.book_data.copy()
        invalid_data["isbn"] = "123456"

        book = Book(**invalid_data)
        with self.assertRaises(ValidationError):
            book.full_clean()

        # Valid ISBN-10
        valid_data = self.book_data.copy()
        valid_data["isbn"] = "0201896834"

        book = Book(**valid_data)
        try:
            book.full_clean()
        except ValidationError:
            self.fail("ISBN-10 validation incorrectly raises an error")

        # Valid ISBN-13
        valid_data = self.book_data.copy()
        valid_data["isbn"] = "9780201896831"

        book = Book(**valid_data)
        try:
            book.full_clean()
        except ValidationError:
            self.fail("ISBN-13 validation incorrectly raises an error")

    def test_book_with_minimal_fields(self):
        """Test creating a book with minimal fields."""
        minimal_data = {
            "title": "Minimal Book",
            "isbn": "9780132350884",  # ISBN required by validator
            "published_date": "2023-01-01",  # Required field
        }

        book = Book.objects.create(**minimal_data)
        book.authors.add(self.author)

        self.assertEqual(book.title, minimal_data["title"])
        self.assertEqual(book.authors.first().name, "Test Author")
        self.assertEqual(book.isbn, minimal_data["isbn"])
        from datetime import datetime

        expected_date = datetime.strptime(
            minimal_data["published_date"], "%Y-%m-%d"
        ).date()
        self.assertEqual(book.published_date, expected_date)
        self.assertEqual(book.description, "")  # Description can be empty
        self.assertIsNotNone(book.id)

    def test_book_validation_fails_without_isbn(self):
        """Test that validation fails for a book without ISBN."""
        minimal_data = {"title": "Book Without ISBN", "published_date": "2023-01-01"}

        # Create object but DON'T save to DB
        book = Book(**minimal_data)

        # Explicitly run validation - should raise exception
        with self.assertRaises(ValidationError):
            book.full_clean()

    def test_book_validation_fails_with_invalid_isbn(self):
        """Test that validation fails for a book with invalid ISBN."""
        invalid_data = {
            "title": "Book With Invalid ISBN",
            "isbn": "12345",  # Too short for ISBN
            "published_date": "2023-01-01",
        }

        # Create object but DON'T save to DB
        book = Book(**invalid_data)

        # Explicitly run validation - should raise exception
        with self.assertRaises(ValidationError):
            book.full_clean()


class BookISBNModelTest(TestCase):
    def setUp(self):
        self.book = Book.objects.create(
            title="Test Book",
            isbn="9780201896831",  # Main ISBN (for backward compatibility)
            published_date="2023-01-01",
        )
        # Add author to the book
        author = Author.objects.create(name="Test Author")
        self.book.authors.add(author)

    def test_create_multiple_isbns(self):
        """Test creating multiple ISBNs for a single book."""
        isbn_13 = BookISBN.objects.create(
            book=self.book, isbn="9780201896831", type="ISBN-13"
        )
        isbn_10 = BookISBN.objects.create(
            book=self.book, isbn="0201896834", type="ISBN-10"
        )

        self.assertEqual(self.book.isbns.count(), 2)
        self.assertEqual(isbn_13.type, "ISBN-13")
        self.assertEqual(isbn_10.type, "ISBN-10")

    def test_unique_isbn(self):
        """Test ISBN uniqueness."""
        BookISBN.objects.create(book=self.book, isbn="9780201896831", type="ISBN-13")
        with self.assertRaises(Exception):  # Should raise IntegrityError
            BookISBN.objects.create(
                book=self.book, isbn="9780201896831", type="ISBN-13"
            )

    def test_str_method(self):
        """Test __str__ method for BookISBN."""
        isbn = BookISBN.objects.create(
            book=self.book, isbn="9780201896831", type="ISBN-13"
        )
        self.assertEqual(str(isbn), "9780201896831 (ISBN-13)")
