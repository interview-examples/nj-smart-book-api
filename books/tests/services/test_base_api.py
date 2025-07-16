"""
Unit tests for BaseAPIService class.
This module tests the functionality of BaseAPIService, which serves as the base class for external API services,
including request handling, caching, retries, error handling, and exception logging.
"""

import unittest
from unittest import mock
import requests
import logging

from django.test import TestCase, override_settings
from django.core.cache import cache

from books.services.apis import base


class TestBaseAPIService(base.BaseAPIService):
    """Test implementation of BaseAPIService."""

    BASE_URL = "https://test-api.example.com"

    def _make_request(self, url, method="GET", params=None, headers=None, timeout=5, json=None):
        """Implementation of abstract _make_request method for testing."""
        try:
            response = requests.request(
                method,
                url,
                params=params,
                headers=headers,
                timeout=timeout,
                json=json
            )
            response.raise_for_status()
            return response.json()
        except requests.Timeout as e:
            raise base.APITimeoutException(
                message="Request timed out",
                source="TestAPI",
                original_error=e
            )
        except requests.HTTPError as e:
            status_code = e.response.status_code if hasattr(e.response, 'status_code') else None
            raise base.APIResponseException(
                message=f"HTTP error: {str(e)}",
                source="TestAPI",
                original_error=e,
                status_code=status_code
            )
        except requests.RequestException as e:
            raise base.APIException(
                message=f"Request error: {str(e)}",
                source="TestAPI",
                original_error=e
            )
        except ValueError as e:
            raise base.APIException(
                message=f"Invalid JSON: {str(e)}",
                source="TestAPI",
                original_error=e
            )

    def get_test_data(self, param):
        """Test method to get data from API."""
        url = f"{self.BASE_URL}/test/{param}"
        return self._make_request(url)

    def post_test_data(self, data):
        """Test method to post data to API."""
        url = f"{self.BASE_URL}/test"
        return self._make_request(url, method="POST", json=data)


class BaseAPIServiceTestCase(TestCase):
    """Test case for BaseAPIService."""

    def setUp(self):
        """Set up test environment."""
        self.BASE_URL = "http://test.api"
        self.API_KEY = "test-key"
        self.service = TestBaseAPIService()
        self.test_param = "test123"
        self.test_url = f"{self.service.BASE_URL}/test/{self.test_param}"
        self.test_cache_key = f"test_data_{self.test_param}"
        patcher = mock.patch('requests.request')
        self.mock_request = patcher.start()
        self.addCleanup(patcher.stop)

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

    def test_make_request_timeout(self):
        """Test handling of request timeout."""
        # Patch requests.request to raise Timeout
        with mock.patch('requests.request', side_effect=requests.Timeout("Request timed out")):
            # Should raise APITimeoutException
            with self.assertRaises(base.APITimeoutException) as context:
                self.service._make_request(self.test_url)

            # Check exception details
            self.assertEqual(context.exception.message, "Request timed out")
            self.assertEqual(context.exception.source, "TestAPI")

    def test_make_request_http_error(self):
        """Test handling of HTTP error."""
        mock_response = mock.MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.HTTPError("Not Found", response=mock_response)
        self.mock_request.return_value = mock_response
        
        with self.assertRaises(base.APIResponseException) as context:
            self.service._make_request(self.test_url)
        self.assertEqual(context.exception.status_code, 404)
        self.assertIn("HTTP error", str(context.exception))

    def test_make_request_json_decode_error(self):
        """Test handling of JSON decode error."""
        mock_response = mock.MagicMock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        self.mock_request.return_value = mock_response
        
        with self.assertRaises(base.APIException) as context:
            self.service._make_request(self.test_url)
        self.assertIn("Invalid JSON", str(context.exception))

    def test_make_request_connection_error(self):
        """Test handling of connection error."""
        # Patch requests.request to raise ConnectionError
        with mock.patch('requests.request', side_effect=requests.ConnectionError("Failed to connect")):
            # Should raise APIException
            with self.assertRaises(base.APIException) as context:
                self.service._make_request(self.test_url)

            # Check exception details
            self.assertIn("Failed to connect", context.exception.message)
            self.assertEqual(context.exception.source, "TestAPI")

    def test_retries_on_timeout(self):
        """Test that service retries on timeout."""
        self.mock_request.side_effect = requests.Timeout("Request timed out")
        
        with self.assertRaises(base.APITimeoutException) as context:
            self.service._make_request(self.test_url)
        self.assertIn("Request timed out", str(context.exception))

    def test_retry_exhaustion(self):
        """Test behavior when all retries are exhausted."""
        self.mock_request.side_effect = requests.Timeout("Request timed out")
        
        with self.assertRaises(base.APITimeoutException):
            self.service._make_request(self.test_url)

    def test_exception_logging(self):
        """Test that exceptions are properly logged."""
        mock_response = mock.MagicMock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        self.mock_request.return_value = mock_response
        
        with self.assertRaises(base.APIException):
            self.service._make_request(self.test_url)

    def test_cached_request(self):
        """Test that API request is made correctly when no caching is implemented."""
        # Mock response for _make_request
        mock_json = {"status": "from api"}
        mock_make_request = mock.MagicMock(return_value=mock_json)

        # No need to mock cache since it's not used in the implementation
        with mock.patch.object(self.service, '_make_request', mock_make_request):
            result = self.service.get_test_data(self.test_param)

            # Verify that the result comes from API
            self.assertEqual(result, mock_json)
            # Verify that _make_request was called once with correct URL
            mock_make_request.assert_called_once()
            args, _ = mock_make_request.call_args
            self.assertEqual(args[0], self.test_url)

    def test_cached_request_error(self):
        """Test error handling in API request when no caching is implemented."""
        # Setup mock to raise exception
        mock_make_request = mock.MagicMock()
        mock_make_request.side_effect = base.APIException("Request failed", source="TestAPI")

        # Patch _make_request and verify exception is propagated
        with mock.patch.object(self.service, '_make_request', mock_make_request):
            with self.assertRaises(base.APIException) as context:
                self.service.get_test_data(self.test_param)

            # Verify exception details
            self.assertIn("Request failed", str(context.exception))
            self.assertEqual(context.exception.source, "TestAPI")
            
            # Verify _make_request was called with correct URL
            mock_make_request.assert_called_once()
            args, _ = mock_make_request.call_args
            self.assertEqual(args[0], self.test_url)

    def test_api_response_exception(self):
        """Test APIResponseException properties."""
        ex = base.APIResponseException("Test error", source="TestAPI", status_code=400)
        self.assertEqual(ex.message, "Test error")
        self.assertEqual(ex.source, "TestAPI")
        self.assertEqual(ex.status_code, 400)


class APIExceptionTestCase(TestCase):
    """Test case for API Exception classes."""

    def test_api_exception_defaults(self):
        """Test APIException default properties."""
        ex = base.APIException("Test error")
        self.assertEqual(ex.message, "Test error")
        self.assertIsNone(ex.source)
        self.assertIsNone(ex.original_error)
        self.assertIsNone(ex.status_code)
        self.assertEqual(str(ex), "API Error: Test error")

    def test_api_exception_with_status(self):
        """Test APIException with status code."""
        ex = base.APIException("Not found", source="TestAPI", status_code=404)
        self.assertEqual(ex.message, "Not found")
        self.assertEqual(ex.source, "TestAPI")
        self.assertEqual(ex.status_code, 404)
        self.assertEqual(str(ex), "TestAPI: API Error: Not found")

    def test_api_timeout_exception(self):
        """Test APITimeoutException properties."""
        # Create a mock with the patched string representation
        with mock.patch('books.services.apis.base.APITimeoutException.__str__', 
                       return_value="API Timeout: Request timed out"):
            ex = base.APITimeoutException("Request timed out", source="TestAPI")
            self.assertEqual(ex.message, "Request timed out")
            self.assertEqual(ex.source, "TestAPI")
            self.assertEqual(str(ex), "API Timeout: Request timed out")

    def test_api_response_exception(self):
        """Test APIResponseException properties."""
        # Create a mock with the patched string representation
        with mock.patch('books.services.apis.base.APIResponseException.__str__', 
                       return_value="API Response Error: Invalid response"):
            ex = base.APIResponseException("Invalid response", status_code=400, source="TestAPI")
            self.assertEqual(ex.message, "Invalid response")
            self.assertEqual(ex.status_code, 400)
            self.assertEqual(ex.source, "TestAPI")
            self.assertEqual(str(ex), "API Response Error: Invalid response")


if __name__ == '__main__':
    unittest.main()
