"""
Enhanced book enrichment service.
Uses adapter pattern for unified access to multiple book data sources.
"""

import logging
from typing import Dict, Any, List, Optional, Type, Union

from django.conf import settings

from books.services.models.data_models import BookEnrichmentData, IndustryIdentifier
from books.services.caching.decorators import cached_api_call
from books.services.enrichment.adapters import (
    BookDataAdapter, GoogleBooksAdapter, OpenLibraryAdapter, NYTimesReviewAdapter
)

logger = logging.getLogger(__name__)


class EnhancedBookEnrichmentService:
    """
    Enhanced service for enriching book data from multiple external sources.
    Uses adapter pattern for unified access to various book data sources.
    """

    def __init__(
        self,
        adapters: Optional[List[BookDataAdapter]] = None,
        review_adapter: Optional[NYTimesReviewAdapter] = None
    ):
        """
        Initialize the enrichment service with provided adapters or create default instances.

        Args:
            adapters: List of book data adapters
            review_adapter: Adapter for book reviews
        """
        # Initialize default adapters if none provided
        if adapters is None:
            self.adapters = [
                GoogleBooksAdapter(),
                OpenLibraryAdapter()
            ]
        else:
            self.adapters = adapters

        # Initialize review adapter
        self.review_adapter = review_adapter or NYTimesReviewAdapter()

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

        # Try to get book data from each adapter
        enriched_data = None

        for adapter in self.adapters:
            try:
                # Get enrichment data from this adapter
                adapter_data = adapter.get_book_data(isbn)

                if adapter_data:
                    # Merge with existing data if any, or use this as the base
                    if enriched_data:
                        enriched_data = enriched_data.merge(adapter_data)
                    else:
                        enriched_data = adapter_data

                    logger.info(f"Retrieved book data for ISBN {isbn} from {adapter.__class__.__name__}")

            except Exception as e:
                logger.error(f"Error retrieving book data from {adapter.__class__.__name__}: {str(e)}", exc_info=True)

        # If we found book data, try to add a review
        if enriched_data:
            try:
                review = self.review_adapter.get_book_review(isbn)
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
            Optional[BookEnrichmentData]: Enriched book data from all ISBNs,
                                         or None if no data found for any ISBN
        """
        if not isbns:
            logger.warning("Cannot enrich book data: No ISBNs provided")
            return None

        # Try each ISBN and merge results
        enriched_data = None
        found_isbns = []

        for isbn in isbns:
            book_data = self.enrich_book_data(isbn)
            if book_data:
                if enriched_data:
                    # Merge with existing data
                    enriched_data = enriched_data.merge(book_data)
                else:
                    enriched_data = book_data

                found_isbns.append(isbn)
                logger.info(f"Found book data for ISBN {isbn}")

        if enriched_data:
            logger.info(f"Successfully enriched book data using ISBNs: {found_isbns}")

            # Make sure all ISBNs are properly stored in industry_identifiers
            for isbn in isbns:
                # Determine ISBN type (ISBN_10 or ISBN_13)
                isbn_type = "ISBN_13" if len(isbn.replace('-', '')) == 13 else "ISBN_10"

                # Check if this ISBN is already in industry_identifiers
                if not any(identifier.type == isbn_type and identifier.identifier == isbn
                           for identifier in enriched_data.industry_identifiers):
                    # Add this ISBN to industry_identifiers
                    enriched_data.industry_identifiers.append(
                        IndustryIdentifier(type=isbn_type, identifier=isbn)
                    )
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

        # Search in each adapter
        for adapter in self.adapters:
            try:
                # Calculate remaining limit
                search_limit = limit - len(results) if limit else None
                if search_limit is not None and search_limit <= 0:
                    break

                # Get search results from this adapter
                adapter_results = adapter.search_books(
                    query=query,
                    title=title,
                    author=author,
                    authors=authors,
                    isbn=isbn,
                    limit=search_limit
                )

                for book in adapter_results:
                    # Skip if no ISBN or we've already seen this ISBN
                    if not book.isbn or book.isbn in seen_isbns:
                        continue

                    # Add to results and mark as seen
                    results.append(book)
                    seen_isbns.add(book.isbn)

                    # Stop if we've reached the limit
                    if limit and len(results) >= limit:
                        break

            except Exception as e:
                logger.error(f"Error searching books in {adapter.__class__.__name__}: {str(e)}", exc_info=True)

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
            bestsellers = self.review_adapter.get_bestsellers(list_name)
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
                        enriched_data = self.review_adapter.enrich_with_bestseller_data(enriched_data, book)
                        results.append(enriched_data)
                    else:
                        # Create minimal data from bestseller info
                        minimal_data = BookEnrichmentData(
                            isbn=primary_isbn,
                            title=book.get('title', ''),
                            authors=[book.get('author', '')],
                            description=book.get('description', ''),
                            source='NY Times Bestsellers'
                        )
                        minimal_data = self.review_adapter.enrich_with_bestseller_data(minimal_data, book)
                        results.append(minimal_data)

            return results

        except Exception as e:
            logger.error(f"Error retrieving bestsellers: {str(e)}", exc_info=True)
            return []

    def get_list_names(self) -> List[str]:
        """
        Get all available bestseller list names.

        Returns:
            List[str]: List of available bestseller list names
        """
        try:
            return self.review_adapter.service.get_list_names()
        except Exception as e:
            logger.error(f"Error retrieving list names: {str(e)}", exc_info=True)
            return []
