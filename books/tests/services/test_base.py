"""
Base test cases for API services testing.
"""

import unittest
from unittest import mock
from django.test import TestCase
from django.core.cache import cache
import requests
import json

from books.services.apis.base import (
    APIException,
    APITimeoutException,
    APIResponseException,
)


class BaseAPIServiceTestCase(TestCase):
    """Base test case for API service testing."""

    def setUp(self):
        """Set up test environment."""
        # Clear cache before each test
        cache.clear()

    def tearDown(self):
        """Clean up after each test."""
        # Clear cache after each test
        cache.clear()

    def mock_successful_response(self, return_value=None):
        """
        Create a mock for successful API response.

        Args:
            return_value: Value to be returned by the mock

        Returns:
            MagicMock: Configured mock object
        """
        mock_response = mock.MagicMock()
        mock_response.json.return_value = return_value or {}
        return mock_response

    def mock_error_response(self, status_code=404, text="Not Found"):
        """
        Create a mock for error API response.

        Args:
            status_code: HTTP status code
            text: Error message

        Returns:
            MagicMock: Configured mock object
        """
        mock_response = mock.MagicMock()
        mock_response.raise_for_status.side_effect = mock.Mock(
            side_effect=Exception(f"HTTP Error {status_code}: {text}")
        )
        mock_response.status_code = status_code
        mock_response.text = text
        return mock_response

    def mock_response(self, mock_get, response_data):
        """
        Configure mock response with data.

        Args:
            mock_get: Mock get method
            response_data: Response data to return
        """
        mock_response = mock.MagicMock()
        mock_response.json.return_value = response_data
        mock_response.status_code = 200
        mock_get.return_value = mock_response

    def create_http_error(self, status_code=404):
        """
        Create an HTTP error for mock responses.

        Args:
            status_code: HTTP status code

        Returns:
            Exception: HTTP error
        """
        response = mock.MagicMock()
        response.status_code = status_code
        http_error = requests.exceptions.HTTPError(f"{status_code} Client Error")
        http_error.response = response
        return http_error

    def create_timeout_error(self):
        """
        Create a timeout error for mock responses.

        Returns:
            Exception: Timeout error
        """
        return requests.exceptions.Timeout("Connection timed out")

    def create_json_decode_error(self):
        """
        Create a JSON decode error for mock responses.

        Returns:
            Exception: JSON decode error
        """
        return json.JSONDecodeError("Invalid JSON", "", 0)

    def assert_api_exception(
        self, exception, expected_type, expected_message_part=None
    ):
        """
        Assert that exception is of expected type and has expected message part.

        Args:
            exception: Exception to check
            expected_type: Expected exception type
            expected_message_part: Expected part of exception message
        """
        self.assertIsInstance(exception, expected_type)
        if expected_message_part:
            self.assertIn(expected_message_part, str(exception))


class MockResponses:
    """Mock responses for API services testing."""

    @staticmethod
    def google_books_success():
        """Return a successful Google Books API response."""
        return {
            "items": [
                {
                    "id": "test_id",
                    "volumeInfo": {
                        "title": "Test Book",
                        "subtitle": "A Test Book",
                        "authors": ["Test Author"],
                        "publisher": "Test Publisher",
                        "publishedDate": "2021",
                        "description": "Test Description",
                        "pageCount": 100,
                        "categories": ["Test Category"],
                        "imageLinks": {"thumbnail": "http://test.com/thumbnail.jpg"},
                        "language": "en",
                        "industryIdentifiers": [
                            {"type": "ISBN_13", "identifier": "9781234567890"},
                            {"type": "ISBN_10", "identifier": "1234567890"},
                        ],
                    },
                }
            ]
        }

    @staticmethod
    def google_books_search_success():
        """Return a successful Google Books API search response."""
        return {
            "items": [
                {
                    "id": "test_id_1",
                    "volumeInfo": {
                        "title": "Test Book 1",
                        "subtitle": "A Test Book",
                        "authors": ["Test Author 1"],
                        "publisher": "Test Publisher",
                        "publishedDate": "2021",
                        "description": "Test Description 1",
                        "pageCount": 100,
                        "categories": ["Test Category"],
                        "imageLinks": {"thumbnail": "http://test.com/thumbnail1.jpg"},
                        "language": "en",
                        "industryIdentifiers": [
                            {"type": "ISBN_13", "identifier": "9781234567890"},
                            {"type": "ISBN_10", "identifier": "1234567890"},
                        ],
                    },
                },
                {
                    "id": "test_id_2",
                    "volumeInfo": {
                        "title": "Test Book 2",
                        "subtitle": "Another Test Book",
                        "authors": ["Test Author 2"],
                        "publisher": "Test Publisher",
                        "publishedDate": "2022",
                        "description": "Test Description 2",
                        "pageCount": 200,
                        "categories": ["Test Category"],
                        "imageLinks": {"thumbnail": "http://test.com/thumbnail2.jpg"},
                        "language": "en",
                        "industryIdentifiers": [
                            {"type": "ISBN_13", "identifier": "9780987654321"},
                            {"type": "ISBN_10", "identifier": "0987654321"},
                        ],
                    },
                },
            ],
            "totalItems": 2,
        }

    @staticmethod
    def open_library_success():
        """Return a successful Open Library API response."""
        return {
            "ISBN:9781234567890": {
                "title": "Test Book",
                "subtitle": "A Test Book",
                "authors": [{"key": "/authors/OL123456A"}],
                "publishers": ["Test Publisher"],
                "publish_date": "2021",
                "number_of_pages": 100,
                "subjects": ["Test Category"],
                "cover": {"medium": "http://test.com/thumbnail.jpg"},
                "languages": [{"key": "/languages/eng"}],
            }
        }

    @staticmethod
    def open_library_author_success():
        """Return a successful Open Library author API response."""
        return {"name": "Test Author"}

    @staticmethod
    def nytimes_review_success():
        """Return a successful NY Times book review API response."""
        return {
            "status": "OK",
            "num_results": 1,
            "results": [
                {"summary": "Test Review Summary", "url": "http://test.com/review"}
            ],
        }

    @staticmethod
    def nytimes_bestsellers_success():
        """Return a successful NY Times bestsellers API response."""
        return {
            "status": "OK",
            "results": {
                "books": [
                    {
                        "rank": 1,
                        "weeks_on_list": 10,
                        "title": "Test Book",
                        "author": "Test Author",
                        "description": "Test Description",
                        "primary_isbn13": "9781234567890",
                        "primary_isbn10": "1234567890",
                    }
                ]
            },
        }
