"""
Tests for Book Enrichment Service.
"""

import unittest
from unittest import mock
import json

from django.test import TestCase, override_settings
from django.core.cache import cache

from books.services.enrichment.service import BookEnrichmentService
from books.services.enrichment.enhanced_service import EnhancedBookEnrichmentService
from books.services.models.data_models import BookEnrichmentData, IndustryIdentifier
from books.services.apis.google_books import GoogleBooksService
from books.services.apis.open_library import OpenLibraryService
from books.services.apis.nytimes import NYTimesService
from books.tests.services.test_base import BaseAPIServiceTestCase, MockResponses


class BookEnrichmentServiceTestCase(BaseAPIServiceTestCase):
    """Test case for BookEnrichmentService."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()

        # Create service with mock instances
        self.google_books_service = mock.MagicMock(spec=GoogleBooksService)
        self.open_library_service = mock.MagicMock(spec=OpenLibraryService)
        self.ny_times_service = mock.MagicMock(spec=NYTimesService)

        self.service = BookEnrichmentService(
            google_books_service=self.google_books_service,
            open_library_service=self.open_library_service,
            ny_times_service=self.ny_times_service
        )

        # Test data
        self.test_isbn = "9781234567890"
        self.test_isbn_alt = "1234567890"
        self.test_isbns = [self.test_isbn, self.test_isbn_alt]

        # Sample enrichment data
        self.google_books_data = {
            "id": "test_id",
            "volumeInfo": {
                "title": "Test Book",
                "subtitle": "A Test Book",
                "authors": ["Test Author"],
                "publisher": "Test Publisher",
                "publishedDate": "2021",
                "description": "Google Description",
                "pageCount": 100,
                "categories": ["Fiction"],
                "imageLinks": {
                    "thumbnail": "http://test.com/thumbnail.jpg"
                },
                "language": "en",
                "industryIdentifiers": [
                    {
                        "type": "ISBN_13",
                        "identifier": self.test_isbn
                    },
                    {
                        "type": "ISBN_10",
                        "identifier": self.test_isbn_alt
                    }
                ]
            }
        }

        self.open_library_data = {
            f"ISBN:{self.test_isbn}": {
                "title": "Test Book",
                "subtitle": "A Test Book",
                "authors": [{"key": "/authors/OL123456A"}],
                "publishers": ["Test Publisher"],
                "publish_date": "2021",
                "number_of_pages": 100,
                "subjects": ["Non-fiction"],
                "cover": {
                    "medium": "http://test.com/ol_thumbnail.jpg"
                },
                "languages": [{"key": "/languages/eng"}],
                "works": [{"key": "/works/OL12345W"}]
            }
        }

        self.google_enrichment_data = BookEnrichmentData(
            isbn=self.test_isbn,
            title="Test Book",
            subtitle="A Test Book",
            authors=["Test Author"],
            publisher="Test Publisher",
            published_date="2021",
            description="Google Description",
            page_count=100,
            categories=["Fiction"],
            thumbnail="http://test.com/thumbnail.jpg",
            language="en",
            industry_identifiers=[
                IndustryIdentifier(type="ISBN_13", identifier=self.test_isbn),
                IndustryIdentifier(type="ISBN_10", identifier=self.test_isbn_alt)
            ],
            source="Google Books"
        )

        self.open_library_enrichment_data = BookEnrichmentData(
            isbn=self.test_isbn,
            title="Test Book",
            subtitle="A Test Book",
            authors=["Test Author"],  
            publisher="Test Publisher",
            published_date="2021",
            description="",
            page_count=100,
            categories=["Non-fiction"],
            thumbnail="http://test.com/ol_thumbnail.jpg",
            language="eng",
            industry_identifiers=[
                IndustryIdentifier(type="ISBN_13", identifier=self.test_isbn)
            ],
            source="Open Library"
        )

        self.nytimes_review = "This is a test review from NY Times."

    def test_enrich_book_data_single_source(self):
        """Test enriching book data from a single source."""
        # Setup mock Google Books service to return data
        self.google_books_service.get_book_data.return_value = self.google_books_data
        self.google_books_service.to_enrichment_data.return_value = self.google_enrichment_data

        # Setup mock Open Library service to return None (no data)
        self.open_library_service.get_book_data.return_value = None

        # Setup mock NY Times service
        self.ny_times_service.get_book_review.return_value = self.nytimes_review

        # Call the method under test
        result = self.service.enrich_book_data(self.test_isbn)

        # Assert results
        self.assertIsNotNone(result)
        self.assertEqual(result.title, "Test Book")
        self.assertEqual(result.source, "Google Books")
        self.assertEqual(result.ny_times_review, self.nytimes_review)

        # Verify service calls
        self.google_books_service.get_book_data.assert_called_once_with(self.test_isbn)
        self.open_library_service.get_book_data.assert_called_once_with(self.test_isbn)
        self.ny_times_service.get_book_review.assert_called_once_with(self.test_isbn)

    def test_enrich_book_data_multiple_sources(self):
        """Test enriching book data from multiple sources."""
        # Setup mock Google Books service to return data
        self.google_books_service.get_book_data.return_value = self.google_books_data
        self.google_books_service.to_enrichment_data.return_value = self.google_enrichment_data

        # Setup mock Open Library service to return data
        self.open_library_service.get_book_data.return_value = self.open_library_data
        self.open_library_service.to_enrichment_data.return_value = self.open_library_enrichment_data

        # Setup mock NY Times service
        self.ny_times_service.get_book_review.return_value = self.nytimes_review

        # Call the method under test
        result = self.service.enrich_book_data(self.test_isbn)

        # Assert results - data should be merged
        self.assertIsNotNone(result)
        self.assertEqual(result.title, "Test Book")
        # Check that categories from both sources are merged
        self.assertIn("Fiction", result.categories)
        self.assertIn("Non-fiction", result.categories)
        # Check that the primary source is maintained
        self.assertEqual(result.source, "Google Books,Open Library")
        self.assertEqual(result.ny_times_review, self.nytimes_review)

        # Verify service calls
        self.google_books_service.get_book_data.assert_called_once_with(self.test_isbn)
        self.open_library_service.get_book_data.assert_called_once_with(self.test_isbn)
        self.ny_times_service.get_book_review.assert_called_once_with(self.test_isbn)

    def test_enrich_book_data_no_sources(self):
        """Test enriching book data when no sources have data."""
        # Setup all services to return None (no data)
        self.google_books_service.get_book_data.return_value = None
        self.open_library_service.get_book_data.return_value = None

        # Call the method under test
        result = self.service.enrich_book_data(self.test_isbn)

        # Assert results
        self.assertIsNone(result)

        # Verify service calls
        self.google_books_service.get_book_data.assert_called_once_with(self.test_isbn)
        self.open_library_service.get_book_data.assert_called_once_with(self.test_isbn)
        self.ny_times_service.get_book_review.assert_not_called()

    def test_enrich_book_data_multi_isbn(self):
        """Test enriching book data using multiple ISBNs."""
        # Setup mock services to return data for second ISBN
        self.google_books_service.get_book_data.side_effect = lambda isbn: (
            self.google_books_data if isbn == self.test_isbn_alt else None
        )

        # Setup to_enrichment_data mock
        self.google_books_service.to_enrichment_data.return_value = self.google_enrichment_data

        # Setup Open Library to return data for first ISBN
        self.open_library_service.get_book_data.side_effect = lambda isbn: (
            self.open_library_data if isbn == self.test_isbn else None
        )
        self.open_library_service.to_enrichment_data.return_value = self.open_library_enrichment_data

        # Setup mock NY Times service
        self.ny_times_service.get_book_review.return_value = self.nytimes_review

        # Call the method under test
        result = self.service.enrich_book_data_multi_isbn(self.test_isbns)

        # Assert results
        self.assertIsNotNone(result)
        self.assertEqual(result.title, "Test Book")
        self.assertEqual(result.ny_times_review, self.nytimes_review)

        # Verify service calls
        self.assertEqual(self.google_books_service.get_book_data.call_count, 2)
        self.google_books_service.get_book_data.assert_any_call(self.test_isbn)
        self.google_books_service.get_book_data.assert_any_call(self.test_isbn_alt)
        self.assertEqual(self.open_library_service.get_book_data.call_count, 2)
        self.open_library_service.get_book_data.assert_any_call(self.test_isbn)
        self.open_library_service.get_book_data.assert_any_call(self.test_isbn_alt)
        self.assertEqual(self.ny_times_service.get_book_review.call_count, 2)
        self.ny_times_service.get_book_review.assert_any_call(self.test_isbn)
        self.ny_times_service.get_book_review.assert_any_call(self.test_isbn_alt)

    def test_search_books(self):
        """Test searching for books."""
        # Setup mock Google Books service to return search results
        self.google_books_service.search_books.return_value = [self.google_books_data]
        self.google_books_service.to_enrichment_data.return_value = self.google_enrichment_data

        # Setup mock Open Library service to return empty results
        self.open_library_service.search_books.return_value = []

        # Call the method under test
        results = self.service.search_books(query="test")

        # Assert results
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Test Book")

        # Verify service calls
        self.google_books_service.search_books.assert_called_once()
        self.open_library_service.search_books.assert_called_once()

    @override_settings(BOOK_ENRICHMENT_CACHE_TIMEOUT=60)
    def test_caching(self):
        """Test that responses are properly cached."""
        # Setup mock Google Books service to return data
        self.google_books_service.get_book_data.return_value = self.google_books_data
        self.google_books_service.to_enrichment_data.return_value = self.google_enrichment_data

        # First call should hit the API
        result1 = self.service.enrich_book_data(self.test_isbn)
        self.assertEqual(self.google_books_service.get_book_data.call_count, 1)

        # Second call should use cache
        result2 = self.service.enrich_book_data(self.test_isbn)
        self.assertEqual(self.google_books_service.get_book_data.call_count, 1)  # Still 1

        # Clear cache and call again
        cache.clear()
        result3 = self.service.enrich_book_data(self.test_isbn)
        self.assertEqual(self.google_books_service.get_book_data.call_count, 2)  # Incremented


class EnhancedBookEnrichmentServiceTestCase(BaseAPIServiceTestCase):
    """Test case for EnhancedBookEnrichmentService."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()

        # Create mock adapters
        self.google_adapter = mock.MagicMock()
        self.open_library_adapter = mock.MagicMock()
        self.review_adapter = mock.MagicMock()

        # Create service with mock adapters
        self.service = EnhancedBookEnrichmentService(
            adapters=[self.google_adapter, self.open_library_adapter],
            review_adapter=self.review_adapter
        )

        # Test data
        self.test_isbn = "9781234567890"
        self.test_isbn_alt = "1234567890"
        self.test_isbns = [self.test_isbn, self.test_isbn_alt]

        # Sample enrichment data
        self.google_enrichment_data = BookEnrichmentData(
            isbn=self.test_isbn,
            title="Test Book",
            subtitle="A Test Book",
            authors=["Test Author"],
            publisher="Test Publisher",
            published_date="2021",
            description="Google Description",
            page_count=100,
            categories=["Fiction"],
            thumbnail="http://test.com/thumbnail.jpg",
            language="en",
            industry_identifiers=[
                IndustryIdentifier(type="ISBN_13", identifier=self.test_isbn),
                IndustryIdentifier(type="ISBN_10", identifier=self.test_isbn_alt)
            ],
            source="Google Books"
        )

        self.open_library_enrichment_data = BookEnrichmentData(
            isbn=self.test_isbn,
            title="Test Book",
            subtitle="A Test Book",
            authors=["Test Author"],  
            publisher="Test Publisher",
            published_date="2021",
            description="",
            page_count=100,
            categories=["Non-fiction"],
            thumbnail="http://test.com/ol_thumbnail.jpg",
            language="eng",
            industry_identifiers=[
                IndustryIdentifier(type="ISBN_13", identifier=self.test_isbn)
            ],
            source="Open Library"
        )

        self.nytimes_review = "This is a test review from NY Times."

    def test_enrich_book_data(self):
        """Test enriching book data with adapters."""
        # Setup mock adapters
        self.google_adapter.get_book_data.return_value = self.google_enrichment_data
        self.open_library_adapter.get_book_data.return_value = self.open_library_enrichment_data
        self.review_adapter.get_book_review.return_value = self.nytimes_review

        # Call the method under test
        result = self.service.enrich_book_data(self.test_isbn)

        # Assert results
        self.assertIsNotNone(result)
        self.assertEqual(result.title, "Test Book")
        self.assertEqual(result.ny_times_review, self.nytimes_review)
        # Check that categories from both sources are merged
        self.assertIn("Fiction", result.categories)
        self.assertIn("Non-fiction", result.categories)

        # Verify adapter calls
        self.google_adapter.get_book_data.assert_called_once_with(self.test_isbn)
        self.open_library_adapter.get_book_data.assert_called_once_with(self.test_isbn)
        self.review_adapter.get_book_review.assert_called_once_with(self.test_isbn)

    def test_enrich_book_data_multi_isbn(self):
        """Test enriching book data using multiple ISBNs with adapters."""
        # Setup mock adapters for different ISBNs
        self.google_adapter.get_book_data.side_effect = lambda isbn: (
            self.google_enrichment_data if isbn == self.test_isbn else None
        )
        self.open_library_adapter.get_book_data.side_effect = lambda isbn: (
            self.open_library_enrichment_data if isbn == self.test_isbn_alt else None
        )
        self.review_adapter.get_book_review.return_value = self.nytimes_review

        # Call the method under test
        result = self.service.enrich_book_data_multi_isbn(self.test_isbns)

        # Assert results
        self.assertIsNotNone(result)
        self.assertEqual(result.title, "Test Book")
        self.assertEqual(result.ny_times_review, self.nytimes_review)
        # Check that industry_identifiers contains both ISBNs
        isbn_identifiers = [i.identifier for i in result.industry_identifiers]
        self.assertIn(self.test_isbn, isbn_identifiers)
        self.assertIn(self.test_isbn_alt, isbn_identifiers)

        # Verify adapter calls
        self.assertEqual(self.google_adapter.get_book_data.call_count, 2)
        self.assertEqual(self.open_library_adapter.get_book_data.call_count, 2)
        self.assertEqual(self.review_adapter.get_book_review.call_count, 2)
        self.review_adapter.get_book_review.assert_any_call(self.test_isbn)
        self.review_adapter.get_book_review.assert_any_call(self.test_isbn_alt)

    def test_search_books(self):
        """Test searching for books with adapters."""
        # Setup mock adapters
        self.google_adapter.search_books.return_value = [self.google_enrichment_data]
        self.open_library_adapter.search_books.return_value = [self.open_library_enrichment_data]

        # Call the method under test
        results = self.service.search_books(query="test")

        # Assert results - should deduplicate by ISBN
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Test Book")

        # Verify adapter calls
        self.google_adapter.search_books.assert_called_once()
        self.open_library_adapter.search_books.assert_called_once()

    def test_get_bestsellers(self):
        """Test getting bestsellers."""
        # Setup mock review adapter
        bestseller_data = {"books": [{
            "rank": 1,
            "weeks_on_list": 10,
            "title": "Test Book",
            "author": "Test Author",
            "description": "Test Description",
            "primary_isbn13": self.test_isbn
        }]}
        self.review_adapter.get_bestsellers.return_value = bestseller_data
        self.review_adapter.enrich_with_bestseller_data.return_value = self.google_enrichment_data

        # Setup first adapter to return data for enrichment
        self.google_adapter.get_book_data.return_value = self.google_enrichment_data

        # Call the method under test
        results = self.service.get_bestsellers()

        # Assert results
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Test Book")

        # Verify adapter calls
        self.review_adapter.get_bestsellers.assert_called_once()
        self.google_adapter.get_book_data.assert_called_once()
        self.review_adapter.enrich_with_bestseller_data.assert_called_once()
