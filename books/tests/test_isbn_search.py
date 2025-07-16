from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from books.models import Book, BookISBN, Author
from books.services.book_service import BookService
from unittest import mock


class ISBNSearchTestCase(APITestCase):
    """Tests for ISBN search functionality in the API."""

    def setUp(self):
        """Setup test data."""
        # Clear database before each test to avoid ISBN uniqueness conflicts
        Book.objects.all().delete()
        BookISBN.objects.all().delete()
        Author.objects.all().delete()

        # Create authors
        self.author1 = Author.objects.create(name="Test Author 1")
        self.author2 = Author.objects.create(name="Test Author 2")
        self.author3 = Author.objects.create(name="Test Author 3")
        
        # Create primary test book with ISBN-13
        self.book1 = Book.objects.create(
            title="Test Book 1",
            isbn="9780134494166",  # Valid ISBN-13 with correct checksum
            description="Test description 1",
            published_date="2023-01-01"
        )
        # Add authors to book using the many-to-many relationship
        self.book1.authors.add(self.author1)
        
        # Create additional ISBN for book1
        BookISBN.objects.create(
            book=self.book1,
            isbn="0134494164",  # Valid ISBN-10 with correct checksum
            type="ISBN-10"
        )
        
        # Create second test book
        self.book2 = Book.objects.create(
            title="Test Book 2",
            isbn="9780306406157",  # Valid ISBN-13
            description="Test description 2",
            published_date="2023-02-01"
        )
        # Add authors to book using the many-to-many relationship
        self.book2.authors.add(self.author2)
        
        # Create third test book with ISBN-10
        self.book3 = Book.objects.create(
            title="Test Book 3",
            isbn="0306406152",  # Valid ISBN-10
            description="Test description 3",
            published_date="2023-03-01"
        )
        # Add authors to book using the many-to-many relationship
        self.book3.authors.add(self.author3)
        
        # Create additional ISBN for book3
        BookISBN.objects.create(
            book=self.book3,
            isbn="9780306406157",  # Valid ISBN-13
            type="ISBN-13"
        )

        # Create service
        self.book_service = BookService()

    def test_get_book_by_isbn_13(self):
        """Test getting a book by ISBN-13."""
        isbn = "9780134494166"
        url = reverse('books-get-by-isbn', kwargs={'isbn': isbn})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertEqual(response_data['title'], self.book1.title)
        self.assertIn(self.author1.name, response_data['authors'])

    def test_get_book_by_isbn_10(self):
        """Test getting a book by ISBN-10."""
        isbn = "0134494164"
        url = reverse('books-get-by-isbn', kwargs={'isbn': isbn})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertEqual(response_data['title'], self.book1.title)

    def test_get_book_by_isbn_with_hyphens(self):
        """Test getting a book by ISBN with hyphens."""
        isbn = "978-0-13-449416-6"  # Same as book1 ISBN but with hyphens
        url = reverse('books-get-by-isbn', kwargs={'isbn': isbn})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertEqual(response_data['title'], self.book1.title)

    def test_get_book_by_isbn_with_spaces(self):
        """Test getting a book by ISBN with spaces."""
        isbn = "978 0 13 449416 6"  # Same as book1 ISBN but with spaces
        url = reverse('books-get-by-isbn', kwargs={'isbn': isbn})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertEqual(response_data['title'], self.book1.title)

    def test_get_book_by_isbn_case_insensitive(self):
        """Test getting a book by ISBN with mixed case (for ISBN-10 with X)."""
        # Create author
        author_x = Author.objects.create(name="Test Author X")
        
        # Create a book with ISBN ending in X
        book_with_x = Book.objects.create(
            title="Book with X",
            isbn="9781234567897",  # Unique valid ISBN-13
            description="Test book with X in ISBN",
            published_date="2023-04-01"
        )
        book_with_x.authors.add(author_x)
        
        # Add an ISBN-10 with X to the book
        BookISBN.objects.create(
            book=book_with_x,
            isbn="123456789X",  # ISBN-10 with X
            type="ISBN-10"
        )
        
        # Test with lowercase x
        isbn = "123456789x"  # lowercase x
        url = reverse('books-get-by-isbn', kwargs={'isbn': isbn})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertEqual(response_data['title'], book_with_x.title)

    def test_get_book_by_alternate_isbn_format(self):
        """Test getting a book by alternate ISBN format (ISBN-10 when stored as ISBN-13 and vice versa)."""
        # Book3 was created with ISBN-10 but has ISBN-13 in BookISBN
        isbn_13 = "9780306406157"
        url = reverse('books-get-by-isbn', kwargs={'isbn': isbn_13})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertEqual(response_data['title'], self.book3.title)

    def test_get_book_by_nonexistent_isbn(self):
        """Test error response when ISBN is not found."""
        isbn = "9780000000000"  # Valid ISBN-13 that does not exist in database
        url = reverse('books-get-by-isbn', kwargs={'isbn': isbn})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json(), {'error': 'Book not found'})

    def test_get_book_with_invalid_isbn_format(self):
        """Test with invalid ISBN format."""
        isbn = "invalid-isbn"
        url = reverse('books-get-by-isbn', kwargs={'isbn': isbn})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json(), {'error': 'Book not found'})

    def test_service_method_calls(self):
        """Test that the service method is called correctly."""
        isbn = "9780134494166"
        url = reverse('books-get-by-isbn', kwargs={'isbn': isbn})
        
        # Patch the service method
        with mock.patch.object(BookService, 'get_book_by_isbn') as mock_get_book:
            mock_get_book.return_value = self.book1
            self.client.get(url)
            
            # Assert the service method was called with the correct ISBN
            mock_get_book.assert_called_once_with(isbn)

    def test_isbn_search_logging(self):
        """Test that ISBN search is logged correctly."""
        isbn = "9780134494166"
        url = reverse('books-get-by-isbn', kwargs={'isbn': isbn})
        
        # Patch the logger
        with mock.patch('logging.error') as mock_logger:
            self.client.get(url)
            
            # For this test we're just checking the endpoint works without errors
            self.assertEqual(mock_logger.call_count, 0)
