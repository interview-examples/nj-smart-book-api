"""
Tests for base API service.
"""

import unittest
from unittest import mock
import requests
import logging

from django.test import TestCase, override_settings
from django.core.cache import cache

from books.services.apis import base
from books.tests.services.test_base import BaseAPIServiceTestCase


class TestBaseAPIService(base.BaseAPIService):
    """Test implementation of BaseAPIService for testing purposes."""

    BASE_URL = "https://test-api.example.com"

    def get_test_data(self, param_id):
        """Test method to get data from API."""
        url = f"{self.BASE_URL}/test/{param_id}"
        cache_key = f"test_data_{param_id}"
        return self._cached_request(url, cache_key, timeout=60)

    def post_test_data(self, data):
        """Test method to post data to API."""
        url = f"{self.BASE_URL}/test"
        return self._make_request(url, method="POST", json=data)


class BaseAPIServiceTestCase(BaseAPIServiceTestCase):
    """Test case for BaseAPIService."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.service = TestBaseAPIService()
        self.test_param = "test123"
        self.test_url = f"{self.service.BASE_URL}/test/{self.test_param}"
        self.test_cache_key = f"test_data_{self.test_param}"

    def test_make_request_get(self):
        """Test making GET request."""
        # Mock response
        mock_json = {"status": "success", "data": {"id": 123, "name": "Test"}}
        mock_response = mock.MagicMock()
        mock_response.json.return_value = mock_json
        mock_response.status_code = 200

        # Patch requests.request
        with mock.patch('requests.request', return_value=mock_response) as mock_request:
            # Call the method
            result = self.service._make_request(self.test_url)

            # Assert results
            self.assertEqual(result, mock_json)
            mock_request.assert_called_once_with(
                "GET",
                self.test_url,
                timeout=5,
                headers=None,
                params=None,
                json=None
            )

    def test_make_request_post(self):
        """Test making POST request."""
        # Test data
        test_data = {"name": "Test Item", "value": 42}

        # Mock response
        mock_json = {"status": "success", "id": 123}
        mock_response = mock.MagicMock()
        mock_response.json.return_value = mock_json
        mock_response.status_code = 201

        # Patch requests.request
        with mock.patch('requests.request', return_value=mock_response) as mock_request:
            # Call the method
            result = self.service._make_request(
                self.test_url,
                method="POST",
                json=test_data
            )

            # Assert results
            self.assertEqual(result, mock_json)
            mock_request.assert_called_once_with(
                "POST",
                self.test_url,
                timeout=5,
                headers=None,
                params=None,
                json=test_data
            )

    def test_make_request_with_params(self):
        """Test making request with query parameters."""
        # Test parameters
        test_params = {"q": "test query", "limit": 5}

        # Mock response
        mock_json = {"results": [{"id": 1, "title": "Test"}]}
        mock_response = mock.MagicMock()
        mock_response.json.return_value = mock_json
        mock_response.status_code = 200

        # Patch requests.request
        with mock.patch('requests.request', return_value=mock_response) as mock_request:
            # Call the method
            result = self.service._make_request(
                self.test_url,
                params=test_params
            )

            # Assert results
            self.assertEqual(result, mock_json)
            mock_request.assert_called_once_with(
                "GET",
                self.test_url,
                timeout=5,
                headers=None,
                params=test_params,
                json=None
            )

    def test_make_request_with_headers(self):
        """Test making request with custom headers."""
        # Test headers
        test_headers = {"Authorization": "Bearer token123", "Content-Type": "application/json"}

        # Mock response
        mock_json = {"status": "authorized", "data": {"id": 123}}
        mock_response = mock.MagicMock()
        mock_response.json.return_value = mock_json
        mock_response.status_code = 200

        # Patch requests.request
        with mock.patch('requests.request', return_value=mock_response) as mock_request:
            # Call the method
            result = self.service._make_request(
                self.test_url,
                headers=test_headers
            )

            # Assert results
            self.assertEqual(result, mock_json)
            mock_request.assert_called_once_with(
                "GET",
                self.test_url,
                timeout=5,
                headers=test_headers,
                params=None,
                json=None
            )

    def test_make_request_with_custom_timeout(self):
        """Test making request with custom timeout."""
        # Mock response
        mock_json = {"status": "success"}
        mock_response = mock.MagicMock()
        mock_response.json.return_value = mock_json
        mock_response.status_code = 200

        # Patch requests.request
        with mock.patch('requests.request', return_value=mock_response) as mock_request:
            # Call the method with custom timeout
            result = self.service._make_request(
                self.test_url,
                timeout=10
            )

            # Assert timeout parameter is passed correctly
            mock_request.assert_called_once_with(
                "GET",
                self.test_url,
                timeout=10,
                headers=None,
                params=None,
                json=None
            )

    def test_make_request_connection_error(self):
        """Test handling of connection errors."""
        # Patch requests.request to raise ConnectionError
        with mock.patch('requests.request', side_effect=requests.ConnectionError("Failed to connect")):
            # Call the method and check exception
            with self.assertRaises(base.APIException) as context:
                self.service._make_request(self.test_url)

            # Assert exception details
            self.assert_api_exception(context.exception, base.APIException, "Failed to connect")

    def test_make_request_timeout_error(self):
        """Test handling of timeout errors."""
        # Patch requests.request to raise Timeout
        with mock.patch('requests.request', side_effect=requests.Timeout("Request timed out")):
            # Call the method and check exception
            with self.assertRaises(base.APITimeoutException) as context:
                self.service._make_request(self.test_url)

            # Assert exception details
            self.assert_api_exception(context.exception, base.APITimeoutException, "Request timed out")

    def test_make_request_http_error(self):
        """Test handling of HTTP error responses."""
        # Create a mock response with 404 error
        mock_response = mock.MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Client Error: Not Found")

        # Patch requests.request to return the error response
        with mock.patch('requests.request', return_value=mock_response):
            # Call the method and check exception
            with self.assertRaises(base.APIResponseException) as context:
                self.service._make_request(self.test_url)

            # Assert exception details
            self.assert_api_exception(context.exception, base.APIResponseException, "404 Client Error")
            self.assertEqual(context.exception.status_code, 404)

    def test_make_request_json_decode_error(self):
        """Test handling of JSON decode errors."""
        # Create a mock response that raises ValueError on json()
        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")

        # Patch requests.request to return our mock
        with mock.patch('requests.request', return_value=mock_response):
            # Call the method and check exception
            with self.assertRaises(base.APIResponseException) as context:
                self.service._make_request(self.test_url)

            # Assert exception details
            self.assert_api_exception(context.exception, base.APIResponseException, "Invalid JSON")

    @override_settings(API_CACHE_TIMEOUT=60)
    def test_cached_request(self):
        """Test cached request functionality."""
        # Mock response
        mock_json = {"status": "success", "data": {"id": 123, "name": "Test"}}

        # Patch _make_request
        with mock.patch.object(self.service, '_make_request', return_value=mock_json) as mock_make_request:
            # First call should make the request
            result1 = self.service.get_test_data(self.test_param)
            self.assertEqual(result1, mock_json)
            self.assertEqual(mock_make_request.call_count, 1)

            # Second call should use cache
            result2 = self.service.get_test_data(self.test_param)
            self.assertEqual(result2, mock_json)
            self.assertEqual(mock_make_request.call_count, 1)  # Still 1

            # Clear cache
            cache.clear()

            # After clearing cache, should make a new request
            result3 = self.service.get_test_data(self.test_param)
            self.assertEqual(result3, mock_json)
            self.assertEqual(mock_make_request.call_count, 2)  # Now 2

    def test_cached_request_error(self):
        """Test cached request when the underlying request fails."""
        # Patch _make_request to raise an exception
        with mock.patch.object(
            self.service, '_make_request', side_effect=base.APITimeoutException("Request timed out")
        ) as mock_make_request:
            # Call should raise the exception
            with self.assertRaises(base.APITimeoutException):
                self.service.get_test_data(self.test_param)

            # Cache should not have been set
            self.assertIsNone(cache.get(self.test_cache_key))

    def test_retries_on_timeout(self):
        """Test that service retries on timeout."""
        # Mock response for successful retry
        mock_json = {"status": "success after retry"}

        # Setup side effect to fail first with timeout, then succeed
        side_effects = [
            requests.Timeout("Request timed out"),
            mock.MagicMock(status_code=200, json=lambda: mock_json)
        ]

        # Patch requests.request with the side effects
        with mock.patch('requests.request', side_effect=side_effects) as mock_request:
            # Should succeed after retry
            result = self.service._make_request(self.test_url, max_retries=1)
            self.assertEqual(result, mock_json)
            self.assertEqual(mock_request.call_count, 2)

    def test_no_retry_on_http_error(self):
        """Test that service does not retry on HTTP errors."""
        # Create a mock response for HTTP error
        mock_response = mock.MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")

        # Patch requests.request to return the error
        with mock.patch('requests.request', return_value=mock_response) as mock_request:
            # Should raise exception without retry
            with self.assertRaises(base.APIResponseException):
                self.service._make_request(self.test_url, max_retries=1)

            # Should only have been called once
            self.assertEqual(mock_request.call_count, 1)

    def test_retry_exhaustion(self):
        """Test behavior when all retries are exhausted."""
        # Patch requests.request to always raise Timeout
        with mock.patch('requests.request', side_effect=requests.Timeout("Request timed out")) as mock_request:
            # Should raise exception after all retries
            with self.assertRaises(base.APITimeoutException):
                self.service._make_request(self.test_url, max_retries=2)

            # Should have been called 3 times (original + 2 retries)
            self.assertEqual(mock_request.call_count, 3)

    @mock.patch('logging.Logger.error')
    def test_exception_logging(self, mock_log_error):
        """Test that exceptions are properly logged."""
        # Patch requests.request to raise ConnectionError
        with mock.patch('requests.request', side_effect=requests.ConnectionError("Failed to connect")):
            # Call the method and catch the exception
            try:
                self.service._make_request(self.test_url)
            except base.APIException:
                pass

            # Assert log was called
            mock_log_error.assert_called_once()
            # Check log message contains the error
            self.assertIn("Failed to connect", mock_log_error.call_args[0][0])


class APIExceptionTestCase(TestCase):
    """Test case for API Exception classes."""

    def test_api_exception_defaults(self):
        """Test APIException default properties."""
        # Create base exception
        ex = base.APIException("Test error")
        self.assertEqual(str(ex), "API Error: Test error")
        self.assertIsNone(ex.status_code)

    def test_api_exception_with_status(self):
        """Test APIException with status code."""
        # Create exception with status
        ex = base.APIException("Test error", status_code=500)
        self.assertEqual(str(ex), "API Error: Test error")
        self.assertEqual(ex.status_code, 500)

    def test_api_timeout_exception(self):
        """Test APITimeoutException properties."""
        # Create timeout exception
        ex = base.APITimeoutException("Request timed out")
        self.assertEqual(str(ex), "API Timeout: Request timed out")
        self.assertIsNone(ex.status_code)

    def test_api_response_exception(self):
        """Test APIResponseException properties."""
        # Create response exception
        ex = base.APIResponseException("Invalid response", status_code=400)
        self.assertEqual(str(ex), "API Response Error: Invalid response")
        self.assertEqual(ex.status_code, 400)
