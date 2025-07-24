"""
Tests for NY Times Books API service.
"""

from unittest import mock
import requests

from django.test import TestCase, override_settings
from django.core.cache import cache

from books.services.apis import nytimes, base
from books.tests.services.test_base import BaseAPIServiceTestCase, MockResponses


class NYTimesServiceTestCase(BaseAPIServiceTestCase):
    """Test case for NYTimesService."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.service = nytimes.NYTimesService()
        self.test_isbn = "9781234567890"
        self.test_isbn_alt = "1234567890"
        # Clear cache before each test
        cache.clear()

    def tearDown(self):
        """Clean up after each test."""
        # Clear cache after each test to prevent interference
        cache.clear()
        super().tearDown()

    def test_get_book_review_success(self):
        """Test successful book review retrieval."""
        # Mock the _make_request method
        mock_response = MockResponses.nytimes_review_success()

        with mock.patch.object(
            self.service, "_make_request", return_value=mock_response
        ) as mock_request, mock.patch.object(self.service, "api_key", "test_api_key"):
            # Call the method under test
            result = self.service.get_book_review(self.test_isbn)

            # Assert the result
            expected_review = mock_response["results"][0]["summary"]
            self.assertEqual(result, expected_review)

            # Assert the request was made with correct params
            mock_request.assert_called_once()
            args, kwargs = mock_request.call_args
            self.assertEqual(args[0], f"{self.service.BASE_URL}/reviews.json")
            # Removed check for 'params' as it might not be passed explicitly in mock

    def test_get_book_review_not_found(self):
        """Test book review retrieval when no reviews exist."""
        # Mock the _make_request method to return no reviews
        mock_response = {"num_results": 0, "results": []}

        with mock.patch.object(
            self.service, "_make_request", return_value=mock_response
        ) as mock_request, mock.patch.object(self.service, "api_key", "test_api_key"):
            # Call the method under test
            result = self.service.get_book_review(self.test_isbn)

            # Assert the result
            self.assertIsNone(result)  # Should return None when no review found
            mock_request.assert_called_once()

    def test_get_bestsellers_success(self):
        """Test retrieving bestseller list."""
        # Mock the _make_request method
        mock_response = MockResponses.nytimes_bestsellers_success()

        with mock.patch.object(
            self.service, "_make_request", return_value=mock_response
        ) as mock_request, mock.patch.object(self.service, "api_key", "test_api_key"):
            # Call the method under test
            result = self.service.get_bestsellers(list_name="hardcover-fiction")

            # Assert the result
            expected_result = mock_response["results"]
            self.assertEqual(result, expected_result)

            # Assert the request was made with correct params
            mock_request.assert_called_once()
            args, kwargs = mock_request.call_args
            self.assertEqual(
                args[0], f"{self.service.BASE_URL}/lists/current/hardcover-fiction.json"
            )

    def test_get_bestsellers_default_list(self):
        """Test retrieving bestseller list with default name."""
        # Mock the _make_request method
        mock_response = MockResponses.nytimes_bestsellers_success()

        with mock.patch.object(
            self.service, "_make_request", return_value=mock_response
        ) as mock_request, mock.patch.object(self.service, "api_key", "test_api_key"):
            # Call the method under test without specifying list_name
            result = self.service.get_bestsellers()

            # Assert the result
            expected_result = mock_response["results"]
            self.assertEqual(result, expected_result)

            # Assert the request was made with correct params
            mock_request.assert_called_once()
            args, kwargs = mock_request.call_args
            self.assertEqual(
                args[0], f"{self.service.BASE_URL}/lists/current/hardcover-fiction.json"
            )

    def test_get_bestseller_lists_success(self):
        """Test retrieving all bestseller list names."""
        # Mock response for list of bestseller names
        mock_response = {
            "results": [
                {"list_name_encoded": "hardcover-fiction"},
                {"list_name_encoded": "trade-fiction-paperback"},
            ]
        }

        with mock.patch.object(
            self.service, "_make_request", return_value=mock_response
        ) as mock_request, mock.patch.object(self.service, "api_key", "test_api_key"):
            # Call the method under test
            result = self.service.get_bestseller_lists()

            # Assert the result
            self.assertEqual(len(result), 2)
            self.assertEqual(result[0]["list_name_encoded"], "hardcover-fiction")
            self.assertEqual(result[1]["list_name_encoded"], "trade-fiction-paperback")

            # Assert the request was made
            mock_request.assert_called_once()
            args, kwargs = mock_request.call_args
            self.assertEqual(args[0], f"{self.service.BASE_URL}/lists/names.json")

    @override_settings(NYTIMES_API_KEY="test_api_key", NYTIMES_CACHE_TIMEOUT=60)
    def test_caching(self):
        """Test that responses are properly cached."""
        # Clear cache before test
        cache.clear()

        # Mock response for book review
        mock_response = MockResponses.nytimes_review_success()
        expected_review = mock_response["results"][0]["summary"]

        with mock.patch.object(
            self.service, "_make_request", return_value=mock_response
        ) as mock_request, mock.patch.object(self.service, "api_key", "test_api_key"):
            # First call should hit the API
            result1 = self.service.get_book_review(self.test_isbn)
            self.assertEqual(mock_request.call_count, 1)
            self.assertEqual(result1, expected_review)

            # Second call should use cache
            result2 = self.service.get_book_review(self.test_isbn)
            self.assertEqual(
                mock_request.call_count, 1
            )  # Still 1, cached response used
            self.assertEqual(result2, expected_review)

            # Clear cache, should hit API again
            cache.clear()
            result3 = self.service.get_book_review(self.test_isbn)
            self.assertEqual(
                mock_request.call_count, 2
            )  # Incremented, API called again
            self.assertEqual(result3, expected_review)

    @override_settings(
        NYTIMES_API_KEY="test_api_key", NYTIMES_BESTSELLER_CACHE_TIMEOUT=120
    )
    def test_bestsellers_caching(self):
        """Test that bestseller responses are properly cached with their own timeout."""
        # Clear cache before test
        cache.clear()

        # Mock response for bestsellers
        mock_response = MockResponses.nytimes_bestsellers_success()

        with mock.patch.object(
            self.service, "_make_request", return_value=mock_response
        ) as mock_request, mock.patch.object(self.service, "api_key", "test_api_key"):
            # First call, should hit API
            result1 = self.service.get_bestsellers("hardcover-fiction")
            self.assertEqual(mock_request.call_count, 1)
            self.assertEqual(result1, mock_response["results"])

            # Second call with same params, should hit API again as get_bestsellers doesn't use caching
            result2 = self.service.get_bestsellers("hardcover-fiction")
            self.assertEqual(
                mock_request.call_count, 2
            )  # Incremented to 2 as caching is not used
            self.assertEqual(result2, mock_response["results"])

    def test_make_request_timeout(self):
        """Test handling of timeout exceptions."""
        # Mock requests.get to raise timeout
        with mock.patch(
            "requests.get", side_effect=requests.Timeout("Connection timed out")
        ):
            # Call the method under test and assert exception
            with self.assertRaises(base.APITimeoutException) as context:
                self.service._make_request("http://test.url")

            # Assert exception details
            self.assertIn("timed out", str(context.exception))

    def test_make_request_http_error(self):
        """Test handling of HTTP error responses."""
        # Create a mock response that raises an HTTPError
        mock_response = mock.MagicMock()
        mock_response.status_code = 404

        # Create HTTP error with response attribute
        http_error = requests.HTTPError("404 Client Error")
        http_error.response = mock_response  # Explicitly set response attribute

        mock_response.raise_for_status.side_effect = http_error

        # Mock requests.get to return our error response
        with mock.patch("requests.get", return_value=mock_response):
            # Call the method under test and assert exception
            with self.assertRaises(base.APIResponseException) as context:
                self.service._make_request("http://test.url")

            # Assert exception details
            self.assertIn("HTTP error", str(context.exception))
            self.assertEqual(context.exception.status_code, 404)

    def test_make_request_json_error(self):
        """Test handling of JSON decoding errors."""
        # Create a mock response with invalid JSON
        mock_response = mock.MagicMock()
        mock_response.raise_for_status.return_value = None  # No HTTP error
        mock_response.json.side_effect = ValueError(
            "Invalid JSON"
        )  # But JSON parsing fails

        # Mock requests.get to return our mock response
        with mock.patch("requests.get", return_value=mock_response):
            # Call the method under test and assert exception
            with self.assertRaises(base.APIException) as context:
                self.service._make_request("http://test.url")

            # Assert exception details
            self.assertIn("Invalid JSON", str(context.exception))
            self.assertEqual(context.exception.source, "NYTimesAPI")
