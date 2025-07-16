"""
Unit tests for adapter classes.
This module tests the functionality of adapter classes responsible for converting raw data from external APIs
into a standardized format for the Ninja Books API.
"""

import unittest
from unittest import mock

from django.test import TestCase

from books.services.enrichment.adapters import GoogleBooksAdapter, OpenLibraryAdapter
from books.services.models.data_models import BookEnrichmentData, IndustryIdentifier


class GoogleBooksAdapterTestCase(TestCase):
    """Test case for GoogleBooksAdapter class."""

    def setUp(self):
        """Set up test environment."""
        self.mock_service = mock.Mock()
        self.adapter = GoogleBooksAdapter(service=self.mock_service)
        self.isbn = '9781234567890'
        self.sample_data = {
            'id': 'test_id',
            'volumeInfo': {
                'title': 'Test Book',
                'subtitle': 'A Subtitle',
                'authors': ['Author One', 'Author Two'],
                'publisher': 'Test Publisher',
                'publishedDate': '2020-01-01',
                'description': 'A test description',
                'pageCount': 200,
                'categories': ['Fiction'],
                'imageLinks': {
                    'thumbnail': 'http://example.com/thumbnail.jpg',
                    'small': 'http://example.com/small.jpg',
                    'medium': 'http://example.com/medium.jpg',
                    'large': 'http://example.com/large.jpg'
                },
                'language': 'en',
                'industryIdentifiers': [
                    {'type': 'ISBN_10', 'identifier': '1234567890'},
                    {'type': 'ISBN_13', 'identifier': '1234567890123'}
                ]
            }
        }
        self.converted_data = BookEnrichmentData(
            isbn="9780132350884",
            title='Test Book: A Subtitle',
            authors=['Author One', 'Author Two'],
            publisher='Test Publisher',
            published_date='2020-01-01',
            description='A test description',
            page_count=200,
            categories=['Fiction'],
            language='en',
            thumbnail="http://example.com/thumbnail.jpg",
            industry_identifiers=[
                IndustryIdentifier(type='ISBN_10', identifier='1234567890'),
                IndustryIdentifier(type='ISBN_13', identifier='1234567890123')
            ]
        )

    def test_get_book_data_success(self):
        """Test successful retrieval of book data by ISBN."""
        self.mock_service.get_book_data.return_value = self.sample_data
        self.mock_service.to_enrichment_data.return_value = self.converted_data

        result = self.adapter.get_book_data(self.isbn)

        self.mock_service.get_book_data.assert_called_once_with(self.isbn)
        self.mock_service.to_enrichment_data.assert_called_once_with(self.sample_data, self.isbn)
        self.assertEqual(result, self.converted_data)

    def test_get_book_data_not_found(self):
        """Test retrieval of book data when book is not found."""
        self.mock_service.get_book_data.return_value = None

        result = self.adapter.get_book_data(self.isbn)

        self.mock_service.get_book_data.assert_called_once_with(self.isbn)
        self.assertIsNone(result)

    def test_get_book_data_exception(self):
        """Test retrieval of book data when an exception occurs."""
        self.mock_service.get_book_data.side_effect = Exception('API Error')

        result = self.adapter.get_book_data(self.isbn)

        self.mock_service.get_book_data.assert_called_once_with(self.isbn)
        self.assertIsNone(result)

    def test_search_books_success(self):
        """Test successful search of books."""
        search_params = {'query': 'test', 'limit': 5}
        raw_results = [self.sample_data]
        converted_results = [self.converted_data]
        self.mock_service.search_books.return_value = raw_results
        self.mock_service.to_enrichment_data.side_effect = lambda item, isbn=None: converted_results[0] if item else None

        results = self.adapter.search_books(**search_params)

        self.mock_service.search_books.assert_called_once_with(**search_params)
        self.assertEqual(results, converted_results)

    def test_search_books_empty(self):
        """Test search of books returning empty results."""
        search_params = {'query': 'test', 'limit': 5}
        self.mock_service.search_books.return_value = []

        results = self.adapter.search_books(**search_params)

        self.mock_service.search_books.assert_called_once_with(**search_params)
        self.assertEqual(results, [])

    def test_search_books_exception(self):
        """Test search of books when an exception occurs."""
        search_params = {'query': 'test', 'limit': 5}
        self.mock_service.search_books.side_effect = Exception('API Error')

        results = self.adapter.search_books(**search_params)

        self.mock_service.search_books.assert_called_once_with(**search_params)
        self.assertEqual(results, [])


class OpenLibraryAdapterTestCase(TestCase):
    """Test case for OpenLibraryAdapter class."""

    def setUp(self):
        """Set up test environment."""
        self.mock_service = mock.Mock()
        self.adapter = OpenLibraryAdapter(service=self.mock_service)
        self.isbn = '9781234567890'
        self.sample_data = {
            'title': 'Test Book',
            'subtitle': 'A Subtitle',
            'authors': [
                {'name': 'Author One'},
                {'name': 'Author Two'}
            ],
            'publishers': [{'name': 'Test Publisher'}],
            'publish_date': '2020',
            'notes': 'A test description',
            'number_of_pages': 200,
            'subjects': ['Fiction'],
            'cover': {
                'small': 'http://example.com/small.jpg',
                'medium': 'http://example.com/medium.jpg',
                'large': 'http://example.com/large.jpg'
            },
            'languages': [{'key': '/languages/eng'}],
            'identifiers': {
                'isbn_10': ['1234567890'],
                'isbn_13': ['1234567890123'],
                'openlibrary': ['OL123M']
            }
        }
        self.converted_data = BookEnrichmentData(
            isbn="9780596007126",
            title='Test Book: A Subtitle',
            authors=['Author One', 'Author Two'],
            publisher='Test Publisher',
            published_date='2020',
            description='A test description',
            page_count=200,
            categories=['Fiction'],
            language='en',
            thumbnail="http://example.com/small.jpg",
            industry_identifiers=[
                IndustryIdentifier(type='ISBN_10', identifier='1234567890'),
                IndustryIdentifier(type='ISBN_13', identifier='1234567890123'),
                IndustryIdentifier(type='OPENLIBRARY', identifier='OL123M')
            ]
        )

    def test_get_book_data_success(self):
        """Test successful retrieval of book data by ISBN."""
        self.mock_service.get_book_data.return_value = self.sample_data
        self.mock_service.to_enrichment_data.return_value = self.converted_data

        result = self.adapter.get_book_data(self.isbn)

        self.mock_service.get_book_data.assert_called_once_with(self.isbn)
        self.mock_service.to_enrichment_data.assert_called_once_with(self.sample_data, self.isbn)
        self.assertEqual(result, self.converted_data)

    def test_get_book_data_not_found(self):
        """Test retrieval of book data when book is not found."""
        self.mock_service.get_book_data.return_value = None

        result = self.adapter.get_book_data(self.isbn)

        self.mock_service.get_book_data.assert_called_once_with(self.isbn)
        self.assertIsNone(result)

    def test_get_book_data_exception(self):
        """Test retrieval of book data when an exception occurs."""
        self.mock_service.get_book_data.side_effect = Exception('API Error')

        result = self.adapter.get_book_data(self.isbn)

        self.mock_service.get_book_data.assert_called_once_with(self.isbn)
        self.assertIsNone(result)

    def test_search_books_success(self):
        """Test successful search of books."""
        search_params = {'query': 'test', 'limit': 5}
        raw_results = [self.sample_data]
        converted_results = [self.converted_data]
        self.mock_service.search_books.return_value = raw_results
        self.mock_service.to_enrichment_data.side_effect = lambda item, isbn=None: converted_results[0] if item else None

        results = self.adapter.search_books(**search_params)

        self.mock_service.search_books.assert_called_once_with(**search_params)
        self.assertEqual(results, converted_results)

    def test_search_books_empty(self):
        """Test search of books returning empty results."""
        search_params = {'query': 'test', 'limit': 5}
        self.mock_service.search_books.return_value = []

        results = self.adapter.search_books(**search_params)

        self.mock_service.search_books.assert_called_once_with(**search_params)
        self.assertEqual(results, [])

    def test_search_books_exception(self):
        """Test search of books when an exception occurs."""
        search_params = {'query': 'test', 'limit': 5}
        self.mock_service.search_books.side_effect = Exception('API Error')

        results = self.adapter.search_books(**search_params)

        self.mock_service.search_books.assert_called_once_with(**search_params)
        self.assertEqual(results, [])


if __name__ == '__main__':
    unittest.main()
