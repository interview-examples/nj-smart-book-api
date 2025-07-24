"""
Tests for Open Library API service.
"""

import unittest
from unittest import mock
import requests

from django.test import TestCase, override_settings
from django.core.cache import cache

from books.services.apis.open_library import OpenLibraryService
from books.services.apis.base import (
    APIException,
    APITimeoutException,
    APIResponseException,
)
from books.services.models.data_models import BookEnrichmentData
from books.tests.services.test_base import BaseAPIServiceTestCase, MockResponses


class OpenLibraryServiceTestCase(BaseAPIServiceTestCase):
    """Test case for OpenLibraryService."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.service = OpenLibraryService()
        self.test_isbn = "9781234567890"
        self.test_author_key = "/authors/OL123456A"
        self.test_book_key = "/books/OL12345M"

        # Add test data for use in tests
        self.open_library_data = {
            "key": "/books/OL12345M",
            "title": "Test Book",
            "authors": [{"key": self.test_author_key}],
            "publish_date": "2023-01-01",
            "isbn_13": [self.test_isbn],
        }

        # Clear cache before each test
        cache.clear()

    def tearDown(self):
        """Clean up after each test."""
        # Clear cache after each test to prevent interference
        cache.clear()
        super().tearDown()

    def test_get_book_data_success(self):
        """Test successful book data retrieval by ISBN."""
        # Mock the _make_request method
        mock_response = MockResponses.open_library_success()

        with mock.patch.object(
            self.service, "_make_request", return_value=mock_response
        ) as mock_request:
            # Call the method under test
            result = self.service.get_book_data(self.test_isbn)

            # Assert results
            self.assertIsNotNone(result)
            self.assertEqual(result, mock_response)
            mock_request.assert_called_once()

            # Verify URL
            args, kwargs = mock_request.call_args
            self.assertEqual(
                args[0], f"{self.service.BASE_URL}/isbn/{self.test_isbn}.json"
            )

    def test_get_book_data_not_found(self):
        """Test book data retrieval when book is not found."""
        # Mock the _make_request method to return empty response
        with mock.patch.object(
            self.service, "_make_request", return_value={}
        ) as mock_request:
            # Call the method under test
            result = self.service.get_book_data(self.test_isbn)

            # Assert results
            self.assertIsNone(result)
            mock_request.assert_called_once()

    def test_search_books(self):
        """Test searching for books."""
        # Define mock search response with ISBNs
        mock_docs = [
            {
                "key": "/works/OL12345W",
                "title": "Test Book 1",
                "author_name": ["Test Author"],
                "isbn": ["9781234567890"],
            }
        ]
        mock_search_response = {"numFound": 1, "docs": mock_docs}

        # Mock book data returned by get_book_data
        mock_book_data = {"key": "/books/OL12345M", "title": "Test Book 1"}

        # Create a side_effect function to validate parameters
        def mock_make_request(url, params=None, *args, **kwargs):
            # Verify URL is correct
            self.assertEqual(url, f"{self.service.BASE_URL}/search.json")
            # Verify params contains expected values
            self.assertIsNotNone(params)
            self.assertIn("q", params)
            self.assertEqual(params["q"], "Test Book")
            return mock_search_response

        # Mock both _make_request and get_book_data methods
        with mock.patch.object(
            self.service, "_make_request", side_effect=mock_make_request
        ):
            with mock.patch.object(
                self.service, "get_book_data", return_value=mock_book_data
            ):
                # Call the method under test with explicit query
                results = self.service.search_books(query="Test Book")

                # Verify results
                self.assertEqual(len(results), 1)
                self.assertEqual(results[0]["title"], "Test Book 1")

    def test_search_books_with_filters(self):
        """Test searching for books with filters."""
        # Create mock responses
        mock_search_response = {
            "numFound": 1,
            "docs": [{"key": "/works/OL12345W", "isbn": ["9781234567890"]}],
        }
        mock_book_data = {"key": "/books/OL12345M", "title": "Test Book 1"}

        # Create a side_effect function that validates the parameters
        def mock_make_request(url, params=None, *args, **kwargs):
            # Verify URL is correct
            self.assertEqual(url, f"{self.service.BASE_URL}/search.json")
            # Verify params contains expected values
            self.assertIsNotNone(params)
            self.assertIn("q", params)
            query = params["q"]
            self.assertIn("title:Harry Potter", query)
            self.assertIn("author:Rowling", query)
            self.assertEqual(params["limit"], 10)
            return mock_search_response

        # Apply mocks using context manager
        with mock.patch.object(
            self.service, "_make_request", side_effect=mock_make_request
        ):
            with mock.patch.object(
                self.service, "get_book_data", return_value=mock_book_data
            ):
                # Call the method under test
                results = self.service.search_books(
                    title="Harry Potter", author="Rowling", limit=10
                )

                # Verify results
                self.assertEqual(len(results), 1)
                self.assertEqual(results[0]["title"], "Test Book 1")

    def test_search_by_isbn(self):
        """Test searching for a book by ISBN."""
        # Mock the _make_request method
        mock_response = {"key": self.test_book_key, "title": "Test Book"}

        with mock.patch.object(
            self.service, "_make_request", return_value=mock_response
        ) as mock_request:
            # Call the method under test
            result = self.service._search_by_isbn(self.test_isbn)

            # Assert results
            self.assertIsInstance(result, list)
            mock_request.assert_called_once()

    def test_get_author_name(self):
        """Test retrieving author name by author key."""
        # Mock the _make_request method
        mock_response = MockResponses.open_library_author_success()

        with mock.patch.object(
            self.service, "_make_request", return_value=mock_response
        ) as mock_request:
            # Call the method under test
            result = self.service._get_author_name(self.test_author_key)

            # Assert results
            self.assertIsInstance(result, str)
            mock_request.assert_called_once()

            # Verify URL
            args, kwargs = mock_request.call_args
            expected_url = (
                f"{self.service.BASE_URL}/authors/{self.test_author_key[9:]}.json"
            )
            self.assertEqual(args[0], expected_url)

    def test_to_enrichment_data(self):
        """Test converting Open Library data to BookEnrichmentData."""
        # Get mock data
        open_library_data = self.open_library_data
        author_data = {"name": "Test Author", "bio": "Author bio"}

        # Mock get_author_data
        with mock.patch.object(
            self.service, "_get_author_name", return_value="Test Author"
        ):
            # Convert to enrichment data
            enrichment_data = self.service.to_enrichment_data(
                open_library_data, self.test_isbn
            )

            # Assert results
            self.assertIsInstance(enrichment_data, BookEnrichmentData)
            self.assertEqual(enrichment_data.isbn, self.test_isbn)
            self.assertEqual(enrichment_data.title, open_library_data["title"])
            self.assertIn("Test Author", enrichment_data.authors)
            self.assertEqual(enrichment_data.source, "Open Library")

    def test_to_enrichment_data_missing_fields(self):
        """Test converting Open Library data with missing fields."""
        # Create minimal data with title (required field)
        minimal_data = {
            "key": self.test_book_key,
            "title": "Minimal Book",  # title is required
        }

        # Mock get_author_data
        with mock.patch.object(
            self.service, "_get_author_name", return_value="Test Author"
        ):
            # Convert to enrichment data
            enrichment_data = self.service.to_enrichment_data(
                minimal_data, self.test_isbn
            )

            # Assert minimal fields are set
            self.assertIsInstance(enrichment_data, BookEnrichmentData)
            self.assertEqual(enrichment_data.isbn, self.test_isbn)
            self.assertEqual(enrichment_data.title, "Minimal Book")
            self.assertEqual(
                enrichment_data.authors, []
            )  # Empty list for missing authors

    def test_make_request_timeout(self):
        """Test handling of timeout exceptions."""
        # Mock requests.get to raise Timeout
        with mock.patch(
            "requests.get", side_effect=requests.Timeout("Connection timed out")
        ):
            with self.assertRaises(APITimeoutException) as context:
                self.service._make_request("http://test.url")

            # Verify exception message
            self.assertIn("timed out", str(context.exception))

    def test_make_request_http_error(self):
        """Test handling of HTTP error responses."""
        # Create a mock response with HTTP error
        mock_response = mock.Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError(
            "404 Client Error"
        )

        # Add status_code to the HTTPError.response
        mock_error_response = mock.Mock()
        mock_error_response.status_code = 404

        # Get the HTTPError instance from side_effect and add response attribute
        http_error = mock_response.raise_for_status.side_effect
        http_error.response = mock_error_response

        # Test the exception handling
        with mock.patch("requests.get", return_value=mock_response):
            with self.assertRaises(APIResponseException) as context:
                self.service._make_request("http://test.url")

            # Verify the exception contains the correct status code
            self.assertEqual(context.exception.status_code, 404)

    @override_settings(OPEN_LIBRARY_CACHE_TIMEOUT=60)
    def test_caching(self):
        """Test caching behavior."""
        # Clear cache before testing
        cache.clear()

        with mock.patch.object(
            self.service, "_make_request", return_value=self.open_library_data
        ) as mock_request:
            # First call - should hit API
            result1 = self.service.get_book_data(self.test_isbn)
            self.assertEqual(mock_request.call_count, 1)

            # Reset call counter
            mock_request.reset_mock()

            # Second call should use cache
            result2 = self.service.get_book_data(self.test_isbn)
            self.assertEqual(mock_request.call_count, 0)  # API call should be skipped

            # Results should be identical
            self.assertEqual(result1, result2)

            # Clear cache and verify API is called again
            cache.clear()
            result3 = self.service.get_book_data(self.test_isbn)
            self.assertEqual(mock_request.call_count, 1)
            self.assertEqual(result1, result3)

    def test_cache_timeout_zero(self):
        """Test that cache can be disabled."""
        # Clear cache before test
        cache.clear()

        # Patch cache.set to prevent any caching
        with mock.patch("django.core.cache.cache.set") as mock_cache_set:
            # Patch _make_request to monitor API calls
            with mock.patch.object(
                self.service, "_make_request", return_value=self.open_library_data
            ) as mock_request:
                # First call
                result1 = self.service.get_book_data(self.test_isbn)
                self.assertEqual(mock_request.call_count, 1)

                # Reset counters
                mock_request.reset_mock()

                # Check that caching was attempted
                self.assertTrue(
                    mock_cache_set.called,
                    "cache.set should be called for the first request",
                )
                mock_cache_set.reset_mock()

                # Second call - without cache
                result2 = self.service.get_book_data(self.test_isbn)

                # Should make another request since caching is disabled
                self.assertEqual(
                    mock_request.call_count,
                    1,
                    "Second call should invoke _make_request as cache is disabled",
                )

                # Check results
                self.assertEqual(result1, result2)
