"""
API service adapters for book data enrichment.
Provides adapter classes for converting API-specific data formats to BookEnrichmentData.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List

from books.services.apis.base import BookDataService, ReviewService
from books.services.apis.google_books import GoogleBooksService
from books.services.apis.open_library import OpenLibraryService
from books.services.apis.nytimes import NYTimesService
from books.services.models.data_models import BookEnrichmentData, IndustryIdentifier

logger = logging.getLogger(__name__)


class BookDataAdapter(ABC):
    """
    Abstract adapter for book data API services.
    Defines interface for converting API-specific data to BookEnrichmentData.
    """

    @abstractmethod
    def get_book_data(self, isbn: str) -> Optional[BookEnrichmentData]:
        """
        Get book data by ISBN and convert to BookEnrichmentData.

        Args:
            isbn: ISBN of the book

        Returns:
            Optional[BookEnrichmentData]: Enriched book data or None if not found
        """
        pass

    @abstractmethod
    def search_books(self, **kwargs) -> List[BookEnrichmentData]:
        """
        Search books and convert results to BookEnrichmentData.

        Args:
            **kwargs: Search parameters

        Returns:
            List[BookEnrichmentData]: List of enriched book data
        """
        pass


class GoogleBooksAdapter(BookDataAdapter):
    """Adapter for Google Books API service."""

    def __init__(self, service: Optional[GoogleBooksService] = None):
        """
        Initialize adapter with Google Books service.

        Args:
            service: Google Books API service instance
        """
        self.service = service or GoogleBooksService()

    def get_book_data(self, isbn: str) -> Optional[BookEnrichmentData]:
        """
        Get book data from Google Books and convert to BookEnrichmentData.

        Args:
            isbn: ISBN of the book

        Returns:
            Optional[BookEnrichmentData]: Enriched book data or None if not found
        """
        try:
            data = self.service.get_book_data(isbn)
            if not data:
                return None
            return self.service.to_enrichment_data(data, isbn)
        except Exception as e:
            logger.error(f"Error getting book data from Google Books: {str(e)}")
            return None

    def search_books(self, **kwargs) -> List[BookEnrichmentData]:
        """
        Search books in Google Books and convert results to BookEnrichmentData.

        Args:
            **kwargs: Search parameters (query, title, author, isbn, limit)

        Returns:
            List[BookEnrichmentData]: List of enriched book data
        """
        try:
            results = self.service.search_books(**kwargs)
            return [self.service.to_enrichment_data(item) for item in results if item]
        except Exception as e:
            logger.error(f"Error searching books in Google Books: {str(e)}")
            return []


class OpenLibraryAdapter(BookDataAdapter):
    """Adapter for Open Library API service."""

    def __init__(self, service: Optional[OpenLibraryService] = None):
        """
        Initialize adapter with Open Library service.

        Args:
            service: Open Library API service instance
        """
        self.service = service or OpenLibraryService()

    def get_book_data(self, isbn: str) -> Optional[BookEnrichmentData]:
        """
        Get book data from Open Library and convert to BookEnrichmentData.

        Args:
            isbn: ISBN of the book

        Returns:
            Optional[BookEnrichmentData]: Enriched book data or None if not found
        """
        try:
            data = self.service.get_book_data(isbn)
            if not data:
                return None
            return self.service.to_enrichment_data(data, isbn)
        except Exception as e:
            logger.error(f"Error getting book data from Open Library: {str(e)}")
            return None

    def search_books(self, **kwargs) -> List[BookEnrichmentData]:
        """
        Search books in Open Library and convert results to BookEnrichmentData.

        Args:
            **kwargs: Search parameters (query, title, author, isbn, limit)

        Returns:
            List[BookEnrichmentData]: List of enriched book data
        """
        try:
            results = self.service.search_books(**kwargs)
            return [self.service.to_enrichment_data(item) for item in results if item]
        except Exception as e:
            logger.error(f"Error searching books in Open Library: {str(e)}")
            return []


class NYTimesReviewAdapter:
    """Adapter for NY Times API service for book reviews."""

    def __init__(self, service: Optional[NYTimesService] = None):
        """
        Initialize adapter with NY Times service.

        Args:
            service: NY Times API service instance
        """
        self.service = service or NYTimesService()

    def get_book_review(self, isbn: str) -> Optional[str]:
        """
        Get book review from NY Times.

        Args:
            isbn: ISBN of the book

        Returns:
            Optional[str]: Book review or None if not found
        """
        try:
            return self.service.get_book_review(isbn)
        except Exception as e:
            logger.error(f"Error getting book review from NY Times: {str(e)}")
            return None

    def get_bestsellers(self, list_name: str = "hardcover-fiction") -> Dict[str, Any]:
        """
        Get bestseller list from NY Times.

        Args:
            list_name: Name of the bestseller list

        Returns:
            Dict[str, Any]: Bestseller list data
        """
        try:
            return self.service.get_bestsellers(list_name)
        except Exception as e:
            logger.error(f"Error getting bestsellers from NY Times: {str(e)}")
            return {}

    def enrich_with_bestseller_data(self, enrichment_data: BookEnrichmentData, bestseller_data: Dict[str, Any]) -> BookEnrichmentData:
        """
        Enrich BookEnrichmentData with bestseller data.

        Args:
            enrichment_data: Book enrichment data to enrich
            bestseller_data: Bestseller data from NY Times

        Returns:
            BookEnrichmentData: Enriched book data
        """
        if not enrichment_data or not bestseller_data:
            return enrichment_data

        enrichment_data.rank = bestseller_data.get('rank', 0)
        enrichment_data.weeks_on_list = bestseller_data.get('weeks_on_list', 0)

        return enrichment_data
