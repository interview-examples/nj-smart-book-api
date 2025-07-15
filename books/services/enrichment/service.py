"""
Book enrichment service.
Provides methods for retrieving and aggregating book data from multiple external sources.
"""

import logging
from typing import Dict, Any, List, Optional, Type, Union

from django.conf import settings

from books.services.apis.google_books import GoogleBooksService
from books.services.apis.open_library import OpenLibraryService
from books.services.apis.nytimes import NYTimesService
from books.services.apis.base import BookDataService, APIException
from books.services.models.data_models import BookEnrichmentData
from books.services.caching.decorators import cached_api_call

logger = logging.getLogger(__name__)


class EnrichmentServiceError(Exception):
    """Base exception for all enrichment service errors."""
    pass


class BookEnrichmentService:
    """
    Service for enriching book data from multiple external sources.
    Aggregates data from Google Books, Open Library, and NY Times.
    """

    def __init__(
        self,
        google_books_service: Optional[GoogleBooksService] = None,
        open_library_service: Optional[OpenLibraryService] = None,
        ny_times_service: Optional[NYTimesService] = None
    ):
        """
        Initialize the enrichment service with provided API services or create default instances.

        Args:
            google_books_service: Google Books API service
            open_library_service: Open Library API service
            ny_times_service: NY Times API service
        """
        self.google_books = google_books_service or GoogleBooksService()
        self.open_library = open_library_service or OpenLibraryService()
        self.ny_times = ny_times_service or NYTimesService()

        # Order of data sources by priority
        self.data_sources = [self.google_books, self.open_library]

        # Cache timeout in seconds
        self.cache_timeout = getattr(settings, 'BOOK_ENRICHMENT_CACHE_TIMEOUT', 14400)  # 4 hours default

    @cached_api_call(cache_timeout=getattr(settings, 'BOOK_ENRICHMENT_CACHE_TIMEOUT', 14400))
    def enrich_book_data(self, isbn: str) -> Optional[BookEnrichmentData]:
        """
        Get enriched book data from all available sources for a single ISBN.

        Args:
            isbn: ISBN of the book to enrich

        Returns:
            Optional[BookEnrichmentData]: Enriched book data or None if not found
        """
        if not isbn:
            logger.warning("Cannot enrich book data: No ISBN provided")
            return None

        # Try to get book data from each source
        enriched_data = None

        for source in self.data_sources:
            try:
                # Get raw book data from the source
                book_data = source.get_book_data(isbn)

                if book_data:
                    # Convert raw data to BookEnrichmentData
                    if isinstance(source, GoogleBooksService):
                        source_data = source.to_enrichment_data(book_data, isbn)
                    elif isinstance(source, OpenLibraryService):
                        source_data = source.to_enrichment_data(book_data, isbn)
                    else:
                        logger.warning(f"Unknown book data source: {source.__class__.__name__}")
                        continue

                    # Merge with existing data if any, or use this as the base
                    if enriched_data:
                        enriched_data = enriched_data.merge(source_data)
                    else:
                        enriched_data = source_data

                    logger.info(f"Retrieved book data for ISBN {isbn} from {source.__class__.__name__}")

            except APIException as e:
                logger.error(f"Error retrieving book data from {source.__class__.__name__}: {str(e)}")
            except Exception as e:
                logger.error(f"Unexpected error in {source.__class__.__name__}: {str(e)}", exc_info=True)

        # If we found book data, try to add a review from NY Times
        if enriched_data:
            try:
                review = self.ny_times.get_book_review(isbn)
                if review:
                    enriched_data.ny_times_review = review
                    logger.info(f"Added NY Times review for ISBN {isbn}")
            except Exception as e:
                logger.error(f"Error retrieving NY Times review for ISBN {isbn}: {str(e)}")
        else:
            logger.info(f"No book data found for ISBN {isbn} from any source")

        return enriched_data

    def enrich_book_data_multi_isbn(self, isbns: List[str]) -> Optional[BookEnrichmentData]:
        """
        Try to enrich book data using multiple ISBNs, merging results if found.
        Useful for books with both ISBN-10 and ISBN-13 or other alternate identifiers.

        Args:
            isbns: List of ISBNs to try

        Returns:
            Optional[BookEnrichmentData]: Enriched book data from the first successful ISBN lookup,
                                         or None if no data found for any ISBN
        """
        if not isbns:
            logger.warning("Cannot enrich book data: No ISBNs provided")
            return None

        # Try each ISBN until we find data
        enriched_data = None
        successful_isbn = None

        for isbn in isbns:
            book_data = self.enrich_book_data(isbn)
            if book_data:
                if enriched_data:
                    # Merge with existing data
                    enriched_data = enriched_data.merge(book_data)
                else:
                    enriched_data = book_data
                    successful_isbn = isbn

                logger.info(f"Found book data for ISBN {isbn}")

        if enriched_data:
            logger.info(f"Successfully enriched book data using ISBNs: {isbns}")
            # Make sure the primary ISBN is set correctly
            if successful_isbn and successful_isbn != enriched_data.isbn:
                enriched_data.isbn = successful_isbn

        else:
            logger.warning(f"No book data found for any of the provided ISBNs: {isbns}")

        return enriched_data

    def search_books(
        self,
        query: str = "",
        title: str = "",
        author: str = "",
        authors: List[str] = None,
        isbn: str = "",
        limit: int = 10
    ) -> List[BookEnrichmentData]:
        """
        Search for books across all available sources.

        Args:
            query: General search query
            title: Book title
            author: Book author (legacy parameter, use for backward compatibility)
            authors: List of book authors
            isbn: Book ISBN
            limit: Maximum number of results (default: 10)

        Returns:
            List[BookEnrichmentData]: List of enriched book data
        """
        results = []
        seen_isbns = set()

        # If ISBN is provided, try to get specific book data
        if isbn:
            book_data = self.enrich_book_data(isbn)
            if book_data:
                return [book_data]

        # Convert author to authors list if provided
        if author and not authors:
            authors = [author]

        # Search in each source
        for source in self.data_sources:
            try:
                # Get search results from this source
                search_limit = limit - len(results) if limit else None
                if search_limit is not None and search_limit <= 0:
                    break

                raw_results = source.search_books(
                    query=query,
                    title=title,
                    authors=authors,
                    isbn=isbn,
                    limit=search_limit
                )

                for book_data in raw_results:
                    # Convert raw data to BookEnrichmentData
                    if isinstance(source, GoogleBooksService):
                        book = source.to_enrichment_data(book_data)
                    elif isinstance(source, OpenLibraryService):
                        book = source.to_enrichment_data(book_data)
                    else:
                        continue

                    # Skip if we've already seen this ISBN
                    if not book.isbn or book.isbn in seen_isbns:
                        continue

                    # Add to results and mark as seen
                    results.append(book)
                    seen_isbns.add(book.isbn)

                    # Stop if we've reached the limit
                    if limit and len(results) >= limit:
                        break

            except Exception as e:
                logger.error(f"Error searching books in {source.__class__.__name__}: {str(e)}")

        return results

    def get_bestsellers(self, list_name: str = "hardcover-fiction", limit: int = 10) -> List[BookEnrichmentData]:
        """
        Get bestseller list from NY Times and enrich with book data.

        Args:
            list_name: Name of the bestseller list
            limit: Maximum number of results

        Returns:
            List[BookEnrichmentData]: List of enriched bestseller book data
        """
        try:
            # Get bestsellers from NY Times
            bestsellers = self.ny_times.get_bestsellers(list_name)
            if not bestsellers or 'books' not in bestsellers:
                logger.info(f"No bestsellers found for list: {list_name}")
                return []

            results = []
            books = bestsellers.get('books', [])[:limit]

            # Enrich each bestseller with detailed book data
            for book in books:
                # Get ISBNs from bestseller entry
                primary_isbn = book.get('primary_isbn13') or book.get('primary_isbn10', '')

                if primary_isbn:
                    # Try to get enriched data
                    enriched_data = self.enrich_book_data(primary_isbn)

                    if enriched_data:
                        # Add bestseller rank
                        enriched_data.rank = book.get('rank', 0)
                        enriched_data.weeks_on_list = book.get('weeks_on_list', 0)
                        results.append(enriched_data)
                    else:
                        # Create minimal data from bestseller info
                        author_name = book.get('author', '')
                        authors_list = [author_name] if author_name else []
                        minimal_data = BookEnrichmentData(
                            isbn=primary_isbn,
                            title=book.get('title', ''),
                            authors=authors_list,
                            description=book.get('description', ''),
                            source='NY Times Bestsellers'
                        )
                        results.append(minimal_data)

            return results

        except Exception as e:
            logger.error(f"Error retrieving bestsellers: {str(e)}")
            return []
