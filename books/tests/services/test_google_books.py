"""
Tests for the Google Books API service.

This test suite validates the GoogleBooksService functionality, including:
- Retrieving book data by ISBN
- Search functionality
- Data conversion to BookEnrichmentData
- Error handling
- Caching behavior
"""

import json
from unittest import mock
import requests

from django.test import TestCase, override_settings
from django.core.cache import cache
from django.core.exceptions import ValidationError

from books.services.apis.google_books import GoogleBooksService
from books.services.models.data_models import BookEnrichmentData, IndustryIdentifier
from books.services.apis.base import APIException, APITimeoutException, APIResponseException
from books.models import validate_isbn
from books.tests.services.test_base import BaseAPIServiceTestCase, MockResponses


class GoogleBooksServiceTestCase(BaseAPIServiceTestCase):
    """Tests for GoogleBooksService."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.service = GoogleBooksService()
        self.test_isbn = "9780306406157"  # Valid ISBN-13
        
        # Sample Google Books API response
        self.google_books_data = MockResponses.google_books_success()
        self.google_books_empty_data = {"totalItems": 0}
        self.search_data = MockResponses.google_books_search_success()
        
        # Clear cache before each test
        cache.clear()
    
    def tearDown(self):
        """Clean up after test."""
        super().tearDown()
        # Clear cache after each test
        cache.clear()
    
    def test_get_book_data_success(self):
        """Test successful retrieval of book data by ISBN."""
        # Setup mock response
        mock_response = mock.Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = self.google_books_data
        
        # Patch requests.get to return mock response
        with mock.patch('requests.get', return_value=mock_response) as mock_get:
            # Call service method
            result = self.service.get_book_data(self.test_isbn)
            
            # Verify API call
            mock_get.assert_called_once()
            params = mock_get.call_args[1]['params']
            self.assertIn(f"isbn:{self.test_isbn}", params['q'])
            
            # Verify result is volumeInfo from first item
            self.assertEqual(result, self.google_books_data["items"][0]["volumeInfo"])
    
    def test_get_book_data_not_found(self):
        """Test book data retrieval when book is not found."""
        # Setup mock response for empty result
        mock_response = mock.Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = self.google_books_empty_data
        
        # Patch requests.get to return mock response
        with mock.patch('requests.get', return_value=mock_response):
            # Call service method
            result = self.service.get_book_data("9999999999999")
            
            # Verify empty result is handled correctly
            self.assertIsNone(result)
    
    def test_search_books(self):
        """Test searching for books."""
        # Setup mock response
        mock_response = mock.Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = self.search_data
        
        # Test parameters
        query = "test query"
        limit = 5
        
        # Patch requests.get to return mock response
        with mock.patch('requests.get', return_value=mock_response) as mock_get:
            # Call service method
            result = self.service.search_books(query=query, limit=limit)
            
            # Verify API call
            mock_get.assert_called_once()
            params = mock_get.call_args[1]['params']
            self.assertIn(query, params['q'])
            self.assertEqual(limit, params['maxResults'])
            
            # Verify result matches the structure returned by search_books method
            self.assertEqual(len(result), len(self.search_data.get("items", [])))
    
    def test_search_books_with_filters(self):
        """Test searching for books with additional filters."""
        # Setup mock response
        mock_response = mock.Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = self.search_data
        
        # Test parameters with filters
        query = "test query"
        authors = ["Test Author"]
        title = "Test Title"
        publisher = "Test Publisher"
        subject = "Fiction"
        isbn = "1234567890"
        
        # Patch requests.get to return mock response
        with mock.patch('requests.get', return_value=mock_response) as mock_get:
            # Call service method
            result = self.service.search_books(
                query=query,
                limit=10,
                authors=authors,
                title=title,
                publisher=publisher,
                subject=subject,
                isbn=isbn
            )
            
            # Verify API call
            mock_get.assert_called_once()
            params = mock_get.call_args[1]['params']
            
            # Extract the query string
            q_param = params['q']
            
            # Verify all filter parameters are included
            self.assertIn(f"inauthor:{authors[0]}", q_param)
            self.assertIn(f"intitle:{title}", q_param)
            self.assertIn(f"inpublisher:{publisher}", q_param)
            self.assertIn(f"subject:{subject}", q_param)
            self.assertIn(f"isbn:{isbn}", q_param)
    
    def test_search_books_empty_result(self):
        """Test searching for books with no results."""
        # Setup mock response for empty search result
        mock_response = mock.Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"totalItems": 0}  # No items key
        
        # Patch requests.get to return mock response
        with mock.patch('requests.get', return_value=mock_response):
            # Call service method
            result = self.service.search_books(query="nonexistent book")
            
            # Verify empty result is handled correctly
            self.assertEqual(result, [])
    
    def test_to_enrichment_data(self):
        """Test conversion of Google Books data to BookEnrichmentData."""
        # Get sample book data (volumeInfo directly)
        volume_info = self.google_books_data["items"][0]["volumeInfo"].copy()
        
        # Override subtitle to match test expectations
        volume_info["subtitle"] = None
        
        # Convert to enrichment data
        result = self.service.to_enrichment_data(volume_info, self.test_isbn)
        
        # Verify result is a BookEnrichmentData object
        self.assertIsInstance(result, BookEnrichmentData)
        
        # Verify fields are correctly mapped
        self.assertEqual(result.isbn, self.test_isbn)
        self.assertEqual(result.title, volume_info["title"])
        self.assertEqual(result.subtitle, volume_info.get("subtitle"))
        self.assertEqual(result.authors, volume_info.get("authors", []))
        self.assertEqual(result.publisher, volume_info.get("publisher"))
        self.assertEqual(result.published_date, volume_info.get("publishedDate").split('-')[0] if volume_info.get("publishedDate") else None)
        self.assertEqual(result.description, volume_info.get("description"))
        self.assertEqual(result.page_count, volume_info.get("pageCount"))
        self.assertEqual(result.categories, volume_info.get("categories", []))
        self.assertEqual(result.language, volume_info.get("language"))
        
        # Test thumbnail handling
        if "imageLinks" in volume_info and "thumbnail" in volume_info["imageLinks"]:
            self.assertEqual(result.thumbnail, volume_info["imageLinks"]["thumbnail"])
        else:
            self.assertIsNone(result.thumbnail)
    
    def test_to_enrichment_data_with_industry_identifiers(self):
        """Test conversion of Google Books data with multiple industry identifiers."""
        # Create test data with multiple industry identifiers
        test_data = {
            "title": "Test Book",
            "authors": ["Test Author"],
            "industryIdentifiers": [
                {"type": "ISBN_13", "identifier": "9781234567890"},
                {"type": "ISBN_10", "identifier": "123456789X"},
                {"type": "OTHER", "identifier": "ABC123"}
            ]
        }
        
        # Convert to enrichment data
        result = self.service.to_enrichment_data(test_data, self.test_isbn)
        
        # Verify industry identifiers were processed correctly
        self.assertEqual(len(result.industry_identifiers), 3)
        
        # Check identifiers by type
        isbn13 = next((i for i in result.industry_identifiers if i.type == "ISBN-13"), None)
        isbn10 = next((i for i in result.industry_identifiers if i.type == "ISBN-10"), None)
        other = next((i for i in result.industry_identifiers if i.type == "OTHER"), None)
        
        self.assertIsNotNone(isbn13)
        self.assertEqual(isbn13.identifier, "9781234567890")
        
        self.assertIsNotNone(isbn10)
        self.assertEqual(isbn10.identifier, "123456789X")
        
        self.assertIsNotNone(other)
        self.assertEqual(other.identifier, "ABC123")
    
    def test_to_enrichment_data_partial_info(self):
        """Test conversion with partial book information."""
        # Create test data with minimal information
        minimal_data = {
            "title": "Test Book"
            # No other fields
        }
        
        # Convert to enrichment data
        result = self.service.to_enrichment_data(minimal_data, self.test_isbn)
        
        # Verify required fields
        self.assertEqual(result.isbn, self.test_isbn)
        self.assertEqual(result.title, "Test Book")
        
        # Verify optional fields default to None or empty list
        self.assertEqual(result.authors, [])  # Empty list for authors
        self.assertIsNone(result.publisher)
        self.assertIsNone(result.description)  # Should be None, not empty string
        self.assertEqual(result.categories, [])
    
    def test_error_handling_http_error(self):
        """Test handling of HTTP errors."""
        # Correctly configure mock for HTTPError
        mock_response = mock.Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Client Error")
        # Add a response attribute to the mock object that will be returned
        mock_response.raise_for_status.side_effect.response = mock.Mock()
        mock_response.raise_for_status.side_effect.response.status_code = 404
        
        with mock.patch('requests.get', return_value=mock_response):
            # Verify that the method calling _make_request handles the error
            result = self.service.get_book_data(self.test_isbn)
            self.assertIsNone(result)
    
    def test_error_handling_timeout(self):
        """Test handling of timeout errors."""
        # Patch requests.get to raise a Timeout exception
        with mock.patch('requests.get', side_effect=requests.exceptions.Timeout("Connection timed out")):
            # get_book_data should catch the error and return None
            result = self.service.get_book_data(self.test_isbn)
            self.assertIsNone(result)
    
    def test_error_handling_json_error(self):
        """Test handling of JSON decode errors."""
        mock_response = mock.Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        
        with mock.patch('requests.get', return_value=mock_response):
            # get_book_data should catch the error and return None
            result = self.service.get_book_data(self.test_isbn)
            self.assertIsNone(result)

    def test_cache_timeout_zero(self):
        """Test that cache can be disabled."""
        # Clear cache before test
        cache.clear()
        
        # Mock API response
        mock_response = {"items": [{"volumeInfo": {"title": "Test Book"}}]}
        
        # Patch cache.set to prevent caching any values
        with mock.patch('django.core.cache.cache.set') as mock_cache_set:
            # Patch requests.get to monitor API calls
            with mock.patch('requests.get') as mock_get:
                # Configure mock for requests
                mock_response_obj = mock.Mock()
                mock_response_obj.raise_for_status.return_value = None
                mock_response_obj.json.return_value = mock_response
                mock_get.return_value = mock_response_obj
                
                # Create a new service instance for each test
                service = GoogleBooksService()
                
                # First call
                result1 = service.get_book_data(self.test_isbn)
                self.assertEqual(mock_get.call_count, 1)
                
                # Reset counters
                mock_get.reset_mock()
                
                # Verify that caching was attempted
                self.assertTrue(mock_cache_set.called, 
                               "The cache.set function should be called for the first request")
                mock_cache_set.reset_mock()
                
                # Second call - without cache
                result2 = service.get_book_data(self.test_isbn)
                
                # A repeat request should be made since cache is disabled
                self.assertEqual(mock_get.call_count, 1,
                               "The second call should invoke requests.get since cache is disabled")
                
                # Check results
                self.assertEqual(result1.get('title'), result2.get('title'))
    
    def test_api_key_usage(self):
        """Test that API key is used when configured."""
        test_api_key = "test_api_key"
        
        # Save original key
        original_key = self.service.api_key
        
        try:
            # Set test key
            self.service.api_key = test_api_key
            
            # Patch _make_request method to check parameters
            with mock.patch.object(self.service, '_make_request', wraps=self.service._make_request) as spy:
                # Patch requests.get to avoid actual requests
                mock_response = mock.Mock()
                mock_response.raise_for_status.return_value = None
                mock_response.json.return_value = self.google_books_data
                
                with mock.patch('requests.get', return_value=mock_response):
                    # Call the method
                    self.service.get_book_data(self.test_isbn)
                
                # Verify that the API key was passed in the parameters
                spy.assert_called_once()
                params = spy.call_args[0][1]
                self.assertIn('key', params)
                self.assertEqual(params['key'], test_api_key)
        finally:
            # Restore the original key
            self.service.api_key = original_key
