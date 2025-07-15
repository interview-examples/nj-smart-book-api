"""
Tests for API service adapters.
"""

import unittest
from unittest import mock

from django.test import TestCase

from books.services.enrichment.adapters import (
    GoogleBooksAdapter,
    OpenLibraryAdapter,
    NYTimesReviewAdapter,
    BookDataAdapter
)
from books.services.models.data_models import BookEnrichmentData, IndustryIdentifier
from books.services.apis.google_books import GoogleBooksService
from books.services.apis.open_library import OpenLibraryService
from books.services.apis.nytimes import NYTimesService
from books.tests.services.test_base import BaseAPIServiceTestCase, MockResponses


class GoogleBooksAdapterTestCase(BaseAPIServiceTestCase):
    """Test case for GoogleBooksAdapter."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()

        # Create mock for GoogleBooksService
        self.google_books_service = mock.MagicMock(spec=GoogleBooksService)

        # Create adapter with mock service
        self.adapter = GoogleBooksAdapter(self.google_books_service)

        # Test data
        self.test_isbn = "9781234567890"
        self.test_isbn_alt = "1234567890"

        # Mock response data
        self.google_books_data = MockResponses.google_books_success()

        # Sample enrichment data
        self.google_enrichment_data = BookEnrichmentData(
            isbn=self.test_isbn,
            title="Test Book",
            subtitle="A Test Book",
            author="Test Author",
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

    def test_get_book_data(self):
        """Test get_book_data method."""
        # Setup mock service
        self.google_books_service.get_book_data.return_value = self.google_books_data
        self.google_books_service.to_enrichment_data.return_value = self.google_enrichment_data

        # Call the method under test
        result = self.adapter.get_book_data(self.test_isbn)

        # Assert result
        self.assertIsNotNone(result)
        self.assertIsInstance(result, BookEnrichmentData)
        self.assertEqual(result.title, "Test Book")
        self.assertEqual(result.source, "Google Books")

        # Verify service calls
        self.google_books_service.get_book_data.assert_called_once_with(self.test_isbn)
        self.google_books_service.to_enrichment_data.assert_called_once_with(self.google_books_data["items"][0])

    def test_get_book_data_not_found(self):
        """Test get_book_data method when book is not found."""
        # Setup mock service to return None
        self.google_books_service.get_book_data.return_value = None

        # Call the method under test
        result = self.adapter.get_book_data(self.test_isbn)

        # Assert result
        self.assertIsNone(result)

        # Verify service calls
        self.google_books_service.get_book_data.assert_called_once_with(self.test_isbn)
        self.google_books_service.to_enrichment_data.assert_not_called()

    def test_search_books(self):
        """Test search_books method."""
        # Setup mock service
        self.google_books_service.search_books.return_value = [self.google_books_data["items"][0]]
        self.google_books_service.to_enrichment_data.return_value = self.google_enrichment_data

        # Call the method under test
        results = self.adapter.search_books(query="test", limit=5)

        # Assert results
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Test Book")

        # Verify service calls
        self.google_books_service.search_books.assert_called_once_with(query="test", limit=5)
        self.google_books_service.to_enrichment_data.assert_called_once()


class OpenLibraryAdapterTestCase(BaseAPIServiceTestCase):
    """Test case for OpenLibraryAdapter."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()

        # Create mock for OpenLibraryService
        self.open_library_service = mock.MagicMock(spec=OpenLibraryService)

        # Create adapter with mock service
        self.adapter = OpenLibraryAdapter(self.open_library_service)

        # Test data
        self.test_isbn = "9781234567890"

        # Mock response data
        self.open_library_data = MockResponses.open_library_success()

        # Sample enrichment data
        self.open_library_enrichment_data = BookEnrichmentData(
            isbn=self.test_isbn,
            title="Test Book",
            subtitle="A Test Book",
            author="Test Author",
            publisher="Test Publisher",
            published_date="2021",
            description="",
            page_count=100,
            categories=["Test Category"],
            thumbnail="http://test.com/thumbnail.jpg",
            language="eng",
            industry_identifiers=[
                IndustryIdentifier(type="ISBN_13", identifier=self.test_isbn)
            ],
            source="Open Library"
        )

    def test_get_book_data(self):
        """Test get_book_data method."""
        # Setup mock service
        self.open_library_service.get_book_data.return_value = self.open_library_data
        self.open_library_service.to_enrichment_data.return_value = self.open_library_enrichment_data

        # Call the method under test
        result = self.adapter.get_book_data(self.test_isbn)

        # Assert result
        self.assertIsNotNone(result)
        self.assertIsInstance(result, BookEnrichmentData)
        self.assertEqual(result.title, "Test Book")
        self.assertEqual(result.source, "Open Library")

        # Verify service calls
        self.open_library_service.get_book_data.assert_called_once_with(self.test_isbn)
        self.open_library_service.to_enrichment_data.assert_called_once()

    def test_search_books(self):
        """Test search_books method."""
        # Setup mock service
        self.open_library_service.search_books.return_value = [
            {"key": "/books/OL12345M", "title": "Test Book"}
        ]
        self.open_library_service.get_book_by_key.return_value = self.open_library_data
        self.open_library_service.to_enrichment_data.return_value = self.open_library_enrichment_data

        # Call the method under test
        results = self.adapter.search_books(query="test", limit=5)

        # Assert results
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Test Book")

        # Verify service calls
        self.open_library_service.search_books.assert_called_once_with(query="test", limit=5)
        self.open_library_service.get_book_by_key.assert_called_once()
        self.open_library_service.to_enrichment_data.assert_called_once()


class NYTimesReviewAdapterTestCase(BaseAPIServiceTestCase):
    """Test case for NYTimesReviewAdapter."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()

        # Create mock for NYTimesService
        self.ny_times_service = mock.MagicMock(spec=NYTimesService)

        # Create adapter with mock service
        self.adapter = NYTimesReviewAdapter(self.ny_times_service)

        # Test data
        self.test_isbn = "9781234567890"

        # Mock response data
        self.nytimes_review_data = "This is a test review from NY Times."
        self.nytimes_bestsellers_data = MockResponses.nytimes_bestsellers_success()

    def test_get_book_review(self):
        """Test get_book_review method."""
        # Setup mock service
        self.ny_times_service.get_book_review.return_value = self.nytimes_review_data

        # Call the method under test
        result = self.adapter.get_book_review(self.test_isbn)

        # Assert result
        self.assertEqual(result, self.nytimes_review_data)

        # Verify service calls
        self.ny_times_service.get_book_review.assert_called_once_with(self.test_isbn)

    def test_get_bestsellers(self):
        """Test get_bestsellers method."""
        # Setup mock service
        self.ny_times_service.get_bestsellers.return_value = self.nytimes_bestsellers_data

        # Call the method under test
        result = self.adapter.get_bestsellers(list_name="hardcover-fiction")

        # Assert result structure
        self.assertEqual(result, self.nytimes_bestsellers_data["results"])

        # Verify service calls
        self.ny_times_service.get_bestsellers.assert_called_once_with(list_name="hardcover-fiction")

    def test_enrich_with_bestseller_data(self):
        """Test enrich_with_bestseller_data method."""
        # Setup test data
        book_data = BookEnrichmentData(
            isbn=self.test_isbn,
            title="Test Book",
            author="Test Author",
            source="Google Books"
        )
        bestseller_data = {
            "rank": 1,
            "weeks_on_list": 5,
            "description": "NY Times description"
        }

        # Call the method under test
        result = self.adapter.enrich_with_bestseller_data(book_data, bestseller_data)

        # Assert result contains bestseller data
        self.assertEqual(result.bestseller_rank, 1)
        self.assertEqual(result.bestseller_weeks, 5)
        self.assertEqual(result.description, "NY Times description")

        # Original data should be preserved
        self.assertEqual(result.title, "Test Book")
        self.assertEqual(result.author, "Test Author")
        self.assertEqual(result.isbn, self.test_isbn)


class BookDataAdapterMixinTest(TestCase):
    """Test case for BookDataAdapter mixin."""

    def test_adapter_interface(self):
        """Test that adapter interface raises NotImplementedError."""
        # Create a simple adapter that doesn't implement required methods
        adapter = BookDataAdapter()

        # Test that calling unimplemented methods raises NotImplementedError
        with self.assertRaises(NotImplementedError):
            adapter.get_book_data("1234567890")

        with self.assertRaises(NotImplementedError):
            adapter.search_books(query="test")

    def test_merge_enrichment_data(self):
        """Test merging two enrichment data objects."""
        # Create test data
        data1 = BookEnrichmentData(
            isbn="9781234567890",
            title="Test Book",
            author="Test Author",
            categories=["Fiction"],
            description="Description 1",
            source="Source 1"
        )

        data2 = BookEnrichmentData(
            isbn="9781234567890",
            title="Test Book",
            author="Test Author",
            categories=["Non-fiction", "Biography"],
            description="Description 2",
            page_count=200,
            source="Source 2"
        )

        # Create adapter to use its merge method
        adapter = BookDataAdapter()

        # Merge data objects
        result = adapter.merge_enrichment_data(data1, data2)

        # Assert merged result
        self.assertEqual(result.isbn, "9781234567890")
        self.assertEqual(result.title, "Test Book")
        self.assertEqual(result.description, "Description 1")  # First has priority
        self.assertEqual(result.page_count, 200)  # From second if not in first
        self.assertEqual(result.source, "Source 1, Source 2")  # Sources combined

        # Categories should be merged without duplicates
        self.assertEqual(len(result.categories), 3)
        self.assertIn("Fiction", result.categories)
        self.assertIn("Non-fiction", result.categories)
        self.assertIn("Biography", result.categories)
