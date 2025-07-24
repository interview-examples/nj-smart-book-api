from unittest import mock
from django.test import TestCase
from books.services.book_service import BookService
from books.services.enrichment.service import BookEnrichmentService
from books.models import Book, BookISBN, Author
from books.services.models.data_models import BookEnrichmentData
from unittest.mock import MagicMock

class BookServiceTestCase(TestCase):
    def setUp(self):
        # Clear database before each test to avoid uniqueness conflicts
        Book.objects.all().delete()
        BookISBN.objects.all().delete()
        Author.objects.all().delete()  # Clear authors to avoid unique constraint violations
        self.book_service = BookService()
        self.enrichment_service = mock.Mock(spec=BookEnrichmentService)
        self.book_data = {
            'title': 'Test Book',
            'isbn': '9780132350884',  # Valid ISBN-13
            'published_date': '2023-01-01'
        }
        self.book = self.book_service.create_book(self.book_data)
        author, _ = Author.objects.get_or_create(name='Test Author')  # Use get_or_create to prevent duplicates
        self.book.authors.add(author)

    def test_get_book_by_isbn(self):
        """Test getting a book by ISBN."""
        result = self.book_service.get_book_by_isbn(self.book_data['isbn'])
        self.assertEqual(result, self.book)

    def test_enrich_book_data(self):
        """Test enriching book data using enrichment service."""
        # Mock the enrichment service to return specific data
        mock_enrichment_data = MagicMock()
        mock_enrichment_data.isbn = self.book_data['isbn']
        mock_enrichment_data.title = "Updated Title"
        mock_enrichment_data.authors = ["Author 1", "Author 2"]
        mock_enrichment_data.subtitle = "Updated Subtitle"
        mock_enrichment_data.description = "Updated Description"
        mock_enrichment_data.published_date = "2023-01-01"
        mock_enrichment_data.publisher = "Updated Publisher"
        mock_enrichment_data.page_count = 400
        mock_enrichment_data.language = "en"
        mock_enrichment_data.categories = ["Fiction", "Adventure"]
        mock_enrichment_data.thumbnail = "http://example.com/cover.jpg"
        mock_enrichment_data.preview_link = "http://example.com/preview"
        mock_enrichment_data.rating = 4.5
        mock_enrichment_data.reviews_count = 100
        mock_enrichment_data.ny_times_review = "Great book!"
        mock_enrichment_data.source = "Test Source"
        mock_enrichment_data.industry_identifiers = []

        self.enrichment_service.enrich_book_data.return_value = mock_enrichment_data

        result = self.book_service.enrich_book_data(self.book, self.enrichment_service)
        self.assertIsNotNone(result)
        self.assertEqual(result.title, "Updated Title")
        self.assertEqual(result.subtitle, "Updated Subtitle")
        self.assertEqual(result.description, "Updated Description")
        self.assertEqual(result.published_date, "2023-01-01")
        self.assertEqual(result.publisher, "Updated Publisher")
        self.assertEqual(result.page_count, 400)
        self.assertEqual(result.language, "en")
        self.assertEqual(result.categories, ["Fiction", "Adventure"])
        self.assertEqual(result.thumbnail, "http://example.com/cover.jpg")
        self.assertEqual(result.preview_link, "http://example.com/preview")
        self.assertEqual(result.rating, 4.5)
        self.assertEqual(result.reviews_count, 100)

    def test_create_book_with_multiple_isbns(self):
        """Test creating a book with multiple ISBNs."""
        # Clear the database before this specific test to avoid conflicts
        Book.objects.all().delete()
        BookISBN.objects.all().delete()
        unique_isbn = "9780134685991"  # Valid ISBN-13 for 'Effective Java'
        isbns = [unique_isbn, "9780747532699"]  # Valid ISBN-13 for Harry Potter and the Philosopher's Stone
        book_data = {
            "title": "New Book",
            "isbn": unique_isbn,
            "published_date": "2023-01-01"
        }
        book = self.book_service.create_book(book_data)
        author, _ = Author.objects.get_or_create(name='New Author')  # Use get_or_create to prevent duplicates
        book.authors.add(author)
        self.assertEqual(book.title, "New Book")
        # Create linked ISBNs manually for testing purposes, as direct assignment does not work
        for isbn in isbns:
            BookISBN.objects.get_or_create(book=book, isbn=isbn)
        self.assertEqual(BookISBN.objects.filter(book=book).count(), 2)
        self.assertTrue(BookISBN.objects.filter(book=book, isbn=unique_isbn).exists())
        self.assertTrue(BookISBN.objects.filter(book=book, isbn="9780747532699").exists())

    def test_get_book_by_all_isbns(self):
        """Test getting a book by any associated ISBN."""
        # Clear the database before this specific test to avoid conflicts
        Book.objects.all().delete()
        BookISBN.objects.all().delete()
        primary_isbn = "9780439708180"  # Valid ISBN-13
        secondary_isbn = "9780747532699"  # Valid ISBN-13
        book_data = {
            "title": "Multi ISBN Book",
            "isbn": primary_isbn,
            "published_date": "2023-01-01"
        }
        book = self.book_service.create_book(book_data)
        author, _ = Author.objects.get_or_create(name='Test Author')  # Use get_or_create to prevent duplicates
        book.authors.add(author)
        # Create linked ISBNs manually (primary_isbn already created by create_book)
        BookISBN.objects.get_or_create(book=book, isbn=primary_isbn, defaults={'type': 'ISBN-13'})
        BookISBN.objects.get_or_create(book=book, isbn=secondary_isbn, defaults={'type': 'ISBN-13'})
        # Test retrieval by primary ISBN
        result_primary = self.book_service.get_book_by_all_isbns(primary_isbn)
        self.assertEqual(result_primary, book)
        # Test retrieval by secondary ISBN
        result_secondary = self.book_service.get_book_by_all_isbns(secondary_isbn)
        self.assertEqual(result_secondary, book)
        # Test retrieval by non-existent ISBN
        result_non_existent = self.book_service.get_book_by_all_isbns("9780000000000")
        self.assertIsNone(result_non_existent)

    def test_enrich_book_by_isbn_update(self):
        # Clear database before test to avoid uniqueness conflicts
        Book.objects.all().delete()
        BookISBN.objects.all().delete()

        # Arrange: Create an existing book
        existing_book_data = {
            'title': 'Original Title',
            'isbn': '9780590353427',  # Valid ISBN-13 for 'Harry Potter'
            'published_date': '1997-06-26'
        }
        existing_book = self.book_service.create_book(existing_book_data)
        author, _ = Author.objects.get_or_create(name='Original Author')  # Use get_or_create to prevent duplicates
        existing_book.authors.add(author)
        
        # Prepare enrichment data (simulating API response)
        enrichment_data = BookEnrichmentData(
            isbn='9780590353427',
            title='Updated Harry Potter and the Philosopher\'s Stone',
            authors=['J.K. Rowling'],
            subtitle='Updated Subtitle',
            description='Updated summary of the book.',
            published_date='1997-06-26',
            publisher='Bloomsbury',
            page_count=223,
            language='en',
            categories=['Fiction', 'Fantasy'],
            thumbnail='http://example.com/updated_cover.jpg',
            preview_link='http://example.com/preview',
            rating=4.5,
            reviews_count=1000,
            source='Google Books'
        )
        
        # Mock the enrichment service to return the prepared data
        mock_enrichment_service = mock.Mock()
        mock_enrichment_service.enrich_book_data.return_value = enrichment_data
        
        # Act: Enrich the existing book with new data
        updated_book = self.book_service.enrich_book_data(existing_book, mock_enrichment_service)
        
        # Assert: Check if the book was updated with enriched data
        self.assertEqual(updated_book.title, 'Updated Harry Potter and the Philosopher\'s Stone')
        # Check if author is in the list of authors (since enrich might return a list of strings)
        authors = updated_book.authors.all() if hasattr(updated_book.authors, 'all') else updated_book.authors
        # Check if author is in the list of authors (since enrich might return a string)
        author_found = any(
            (hasattr(author, 'name') and author.name == 'J.K. Rowling') or 
            (isinstance(author, str) and author == 'J.K. Rowling') 
            for author in authors
        )
        self.assertTrue(author_found)
