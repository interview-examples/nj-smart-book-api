from django.test import TestCase
from unittest.mock import patch
from rest_framework.exceptions import ValidationError
from books.models import Book, Author
from books.serializers import (
    BookSerializer,
    EnrichedBookSerializer,
    BookCreateUpdateSerializer
)

class BookSerializerTests(TestCase):
    """Tests for BookSerializer."""
    
    def setUp(self):
        """Set up test data."""
        # Create author separately
        self.author = Author.objects.create(name='Test Author')
        
        # Create book without author
        self.book_data = {
            'title': 'Test Book',
            'isbn': '9780201896831',
            'description': 'Test description of the book',
            'published_date': '2023-01-01'
        }
        
        self.book = Book.objects.create(**self.book_data)
        # Link author to book
        self.book.authors.add(self.author)
        
        self.serializer = BookSerializer(instance=self.book)
    
    def test_contains_expected_fields(self):
        """Check for expected fields in serialized data."""
        data = self.serializer.data
        self.assertCountEqual(data.keys(), [
            'id', 'title', 'authors', 'isbn', 'description', 'published_date'
        ])
    
    def test_title_field_content(self):
        """Check title field content."""
        data = self.serializer.data
        self.assertEqual(data['title'], self.book_data['title'])
    
    def test_authors_field_content(self):
        """Check authors field content."""
        data = self.serializer.data
        self.assertTrue(isinstance(data['authors'], list))
        self.assertEqual(len(data['authors']), 1)
        # Check that authors contains 'Test Author' information
        if isinstance(data['authors'][0], dict):
            self.assertEqual(data['authors'][0]['name'], 'Test Author')
        else:
            self.assertEqual(data['authors'][0], 'Test Author')


class EnrichedBookSerializerTests(TestCase):
    """Tests for EnrichedBookSerializer."""
    
    def setUp(self):
        """Set up test data."""
        # Create author separately
        self.author = Author.objects.create(name='Test Author')
        
        # Create book without author
        self.book_data = {
            'title': 'Test Book',
            'isbn': '9780201896831',
            'description': 'Test description of the book',
            'published_date': '2023-01-01'
        }
        
        self.book = Book.objects.create(**self.book_data)
        # Link author to book
        self.book.authors.add(self.author)
        
        self.serializer = EnrichedBookSerializer(instance=self.book)
    
    def test_contains_expected_fields(self):
        """Check for expected fields in serialized data."""
        data = self.serializer.data
        expected_fields = [
            'id', 'title', 'authors', 'isbn', 'description', 
            'published_date', 'enriched_data'
        ]
        self.assertCountEqual(data.keys(), expected_fields)
    
    def test_enriched_data_structure(self):
        """Check enriched data structure."""
        data = self.serializer.data
        self.assertIn('enriched_data', data)


class BookCreateUpdateSerializerTests(TestCase):
    """Tests for BookCreateUpdateSerializer."""
    
    def setUp(self):
        """Set up test data."""
        # Create author and get ID for use in data
        self.author = Author.objects.create(name='New Test Author')
        
        self.valid_data = {
            'title': 'New Test Book',
            'authors': [self.author.id],  # Pass list of author IDs
            'isbn': '9780132350884',
            'description': 'New test description',
            'published_date': '2023-01-01'
        }
        
        self.invalid_isbn_data = {
            'title': 'Invalid ISBN Book',
            'authors': [self.author.id],
            'isbn': '978-0201-6831',  # Invalid ISBN
            'description': 'Book with invalid ISBN',
            'published_date': '2023-01-01'
        }

        self.invalid_date_data = {
            'title': 'Invalid Date Book',
            'authors': [self.author.id],
            'isbn': '9780132350884',
            'description': 'Book with invalid date',
            'published_date': 'not-a-date'
        }

        self.partial_data = {
            'title': 'Partial Book',
            'authors': [self.author.id],
            'isbn': '9780132350884',
            'published_date': '2023-01-01'  # Add required published_date
        }
    
    def test_validate_valid_data(self):
        """Test validation of valid data."""
        serializer = BookCreateUpdateSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid())
    
    def test_validate_invalid_isbn(self):
        """Test validation with invalid ISBN."""
        serializer = BookCreateUpdateSerializer(data=self.invalid_isbn_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('isbn', serializer.errors)
    
    def test_validate_invalid_date(self):
        """Test validation with invalid date."""
        serializer = BookCreateUpdateSerializer(data=self.invalid_date_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('published_date', serializer.errors)
    
    def test_create_with_partial_data(self):
        """Test creation with partial data."""
        serializer = BookCreateUpdateSerializer(data=self.partial_data)
        self.assertTrue(serializer.is_valid())
        
        book = serializer.save()
        self.assertEqual(book.title, self.partial_data['title'])
        self.assertEqual(book.authors.count(), 1)  # Check that author is added
        self.assertEqual(book.isbn, self.partial_data['isbn'])
    
    def test_update_existing_book(self):
        """Test updating an existing book."""
        book = Book.objects.create(**{
            'title': 'Original Title',
            'isbn': '9780132350884',
            'description': 'Original description',
            'published_date': '2023-01-01'
        })
        book.authors.add(self.author)
        
        update_data = {
            'title': 'Updated Title',
            'description': 'Updated description',
            'authors': [self.author.name]
        }
        
        serializer = BookCreateUpdateSerializer(
            instance=book,
            data=update_data,
            partial=True
        )
        
        self.assertTrue(serializer.is_valid())
        updated_book = serializer.save()
        
        # Check updated fields
        self.assertEqual(updated_book.title, update_data['title'])
        self.assertEqual(updated_book.description, update_data['description'])
        self.assertEqual(updated_book.authors.count(), 1)
        self.assertEqual(updated_book.isbn, '9780132350884')
    
    def test_auto_fill_functionality(self):
        """Test auto-fill functionality."""
        data_with_auto_fill = {
            'title': 'Auto Fill Book',
            'isbn': '9781617294136',
            'authors': [self.author.name],
            'published_date': '2023-01-01',
            'auto_fill': True
        }
        
        from books.services.models.data_models import BookEnrichmentData
        
        mock_data = BookEnrichmentData(
            isbn='9781617294136',
            title='Spring in Action',
            authors=['Craig Walls'],
            description='Test description from external API',
            published_date='2023-01-01'
        )
        
        with patch('books.services.enrichment.service.BookEnrichmentService.enrich_book_data') as mock_enrich:
            mock_enrich.return_value = mock_data
            serializer = BookCreateUpdateSerializer(data=data_with_auto_fill)
            self.assertTrue(serializer.is_valid())
            book = serializer.save()
            
            self.assertEqual(book.title, data_with_auto_fill['title'])
            self.assertEqual(book.isbn, data_with_auto_fill['isbn'])
            self.assertIsNotNone(book.authors.count())
            self.assertIsNotNone(book.description)
