"""
Open Library API service implementation.
Provides methods to search for books and retrieve book data from Open Library.
"""

import logging
import requests
from typing import Dict, Any, List, Optional

from django.conf import settings

from books.services.apis.base import (
    BookDataService,
    APIException,
    APITimeoutException,
    APIResponseException,
)
from books.services.models.data_models import BookEnrichmentData, IndustryIdentifier
from books.services.caching.decorators import cached_api_call

logger = logging.getLogger(__name__)


class OpenLibraryService(BookDataService):
    """
    Service for interacting with Open Library API.
    Implements methods to search and retrieve book data.
    """

    BASE_URL = "https://openlibrary.org"
    CACHE_TIMEOUT = getattr(
        settings, "OPEN_LIBRARY_CACHE_TIMEOUT", 14400
    )  # 4 hours default

    def __init__(self):
        """Initialize the Open Library service."""
        self.api_key = getattr(settings, "OPEN_LIBRARY_API_KEY", None)

    def _make_request(
        self,
        url: str,
        params: Dict[str, Any] = None,
        headers: Dict[str, str] = None,
        timeout: int = 10,
    ) -> Any:
        """
        Make a request to Open Library API with error handling.

        Args:
            url: URL to make the request to
            params: Query parameters for the request
            headers: HTTP headers to include
            timeout: Request timeout in seconds

        Returns:
            Any: Parsed JSON response

        Raises:
            APITimeoutException: If the request times out
            APIResponseException: If the API returns an error response
            APIException: For other API-related errors
        """
        try:
            response = requests.get(
                url, params=params, headers=headers, timeout=timeout
            )
            response.raise_for_status()
            return response.json()

        except requests.Timeout as e:
            raise APITimeoutException(
                message=f"Request to Open Library API timed out after {timeout}s",
                source="OpenLibraryAPI",
                original_error=e,
            )

        except requests.HTTPError as e:
            status_code = e.response.status_code if hasattr(e, "response") else None
            raise APIResponseException(
                message=f"HTTP error from Open Library API: {str(e)}",
                source="OpenLibraryAPI",
                original_error=e,
                status_code=status_code,
            )

        except requests.RequestException as e:
            raise APIException(
                message=f"Request error: {str(e)}",
                source="OpenLibraryAPI",
                original_error=e,
            )
        except ValueError as e:
            # JSON parsing error
            raise APIException(
                message=f"Invalid JSON response: {str(e)}",
                source="OpenLibraryAPI",
                original_error=e,
            )

    @cached_api_call(cache_timeout=CACHE_TIMEOUT)
    def get_book_data(self, isbn: str) -> Optional[Dict[str, Any]]:
        """
        Get book data from Open Library API by ISBN.

        Args:
            isbn: ISBN of the book to retrieve

        Returns:
            Optional[Dict[str, Any]]: Raw book data or None if not found
        """
        url = f"{self.BASE_URL}/isbn/{isbn}.json"

        try:
            data = self._make_request(url)
            if not data:
                logger.info(f"No book found for ISBN {isbn} in Open Library API")
                return None

            return data

        except APIException as e:
            logger.error(f"Error retrieving book data for ISBN {isbn}: {str(e)}")
            return None

    @cached_api_call(cache_timeout=CACHE_TIMEOUT)
    def search_books(
        self,
        query: str = "",
        title: str = "",
        author: str = "",
        isbn: str = "",
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search for books in Open Library API.

        Args:
            query: General search query
            title: Book title
            author: Book author
            isbn: Book ISBN
            limit: Maximum number of results (default: 10)

        Returns:
            List[Dict[str, Any]]: List of raw book data
        """
        # Handle ISBN search differently as it uses a different API endpoint
        if isbn:
            return self._search_by_isbn(isbn)

        # Build query for general search
        final_query = query
        if not query:
            query_parts = []
            if title:
                query_parts.append(f"title:{title}")
            if author:
                query_parts.append(f"author:{author}")
            final_query = " ".join(query_parts)

        if not final_query:
            logger.warning("No search criteria provided for Open Library search")
            return []

        url = f"{self.BASE_URL}/search.json"
        params = {"q": final_query, "limit": min(limit, 100)}

        try:
            response = self._make_request(url, params)
            if not response or "docs" not in response:
                return []

            results = []
            for doc in response.get("docs", []):
                # For each search result, fetch full book data if ISBN is available
                isbn_list = doc.get("isbn", [])
                if isbn_list and len(isbn_list) > 0:
                    book_data = self.get_book_data(isbn_list[0])
                    if book_data:
                        results.append(book_data)

                # Limit results to requested number
                if len(results) >= limit:
                    break

            return results

        except APIException as e:
            logger.error(f"Error searching books with query '{final_query}': {str(e)}")
            return []

    def _search_by_isbn(self, isbn: str) -> List[Dict[str, Any]]:
        """
        Search for a book by ISBN using the Books API.

        Args:
            isbn: ISBN to search for

        Returns:
            List[Dict[str, Any]]: List containing the book data if found
        """
        params = {"bibkeys": f"ISBN:{isbn}", "format": "json", "jscmd": "data"}
        url = f"{self.BASE_URL}/api/books"

        try:
            response = self._make_request(url, params)
            if not response or f"ISBN:{isbn}" not in response:
                return []

            book_data = response.get(f"ISBN:{isbn}", {})
            return [book_data]

        except APIException as e:
            logger.error(f"Error searching book with ISBN {isbn}: {str(e)}")
            return []

    def _get_author_name(self, author_key: str) -> str:
        """
        Get author name from author key.

        Args:
            author_key: Author key from Open Library API

        Returns:
            str: Author name or empty string if not found
        """
        if not author_key:
            return ""

        url = f"{self.BASE_URL}{author_key}.json"

        try:
            author_data = self._make_request(url)
            if author_data and "name" in author_data:
                return author_data["name"]
            return ""

        except APIException as e:
            logger.error(f"Error retrieving author data for key {author_key}: {str(e)}")
            return ""

    def to_enrichment_data(
        self, book_data: Dict[str, Any], base_isbn: str = ""
    ) -> BookEnrichmentData:
        """
        Convert Open Library API book data to BookEnrichmentData.

        Args:
            book_data: Book data from Open Library API
            base_isbn: ISBN to use if none found in book_data

        Returns:
            BookEnrichmentData: Converted enrichment data
        """
        if not book_data or "title" not in book_data:
            return None

        # Extract ISBN
        isbn = base_isbn
        if not isbn:
            # Try to find ISBN in identifiers
            if "identifiers" in book_data:
                identifiers = book_data["identifiers"]
                if "isbn_13" in identifiers and identifiers["isbn_13"]:
                    isbn = identifiers["isbn_13"][0]
                elif "isbn_10" in identifiers and identifiers["isbn_10"]:
                    isbn = identifiers["isbn_10"][0]

            # If still no ISBN, try other fields
            if not isbn:
                if "isbn_13" in book_data and book_data["isbn_13"]:
                    isbn = book_data["isbn_13"][0]
                elif "isbn_10" in book_data and book_data["isbn_10"]:
                    isbn = book_data["isbn_10"][0]

        # Extract author information
        authors = []
        if "authors" in book_data and book_data["authors"]:
            for author_data in book_data["authors"]:
                author_name = ""
                if "name" in author_data:
                    author_name = author_data["name"]
                elif "key" in author_data:
                    author_name = self._get_author_name(author_data["key"])

                if author_name:
                    authors.append(author_name)

        # If no authors found, use empty list
        if not authors:
            authors = []

        # Extract description
        description = book_data.get("description", "")
        if isinstance(description, dict) and "value" in description:
            description = description["value"]

        # Create industry identifiers
        industry_identifiers = []

        # Add ISBN-13
        if "identifiers" in book_data and "isbn_13" in book_data["identifiers"]:
            for id_val in book_data["identifiers"]["isbn_13"]:
                industry_identifiers.append(
                    IndustryIdentifier(type="ISBN-13", identifier=id_val)
                )

        # Add ISBN-10
        if "identifiers" in book_data and "isbn_10" in book_data["identifiers"]:
            for id_val in book_data["identifiers"]["isbn_10"]:
                industry_identifiers.append(
                    IndustryIdentifier(type="ISBN-10", identifier=id_val)
                )

        # If no industry identifiers but we have an ISBN, add it
        if not industry_identifiers and isbn:
            id_type = (
                "ISBN-13"
                if len(isbn) == 13
                else "ISBN-10" if len(isbn) == 10 else "ISBN"
            )
            industry_identifiers.append(
                IndustryIdentifier(type=id_type, identifier=isbn)
            )

        # Extract subjects/categories
        categories = []
        if "subjects" in book_data:
            for subject in book_data["subjects"]:
                if isinstance(subject, str):
                    categories.append(subject)
                elif isinstance(subject, dict) and "name" in subject:
                    categories.append(subject["name"])

        # Create thumbnail URL if we have an ISBN
        thumbnail = ""
        if isbn:
            thumbnail = f"https://covers.openlibrary.org/b/isbn/{isbn}-M.jpg"
        elif "cover" in book_data:
            cover_id = book_data["cover"]
            if isinstance(cover_id, dict) and "medium" in cover_id:
                thumbnail = cover_id["medium"]
            else:
                thumbnail = f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg"

        # Create preview link
        preview_link = f"https://openlibrary.org/isbn/{isbn}" if isbn else ""

        # Extract publish date
        published_date = book_data.get("publish_date", "")
        if published_date:
            try:
                # Extract just the year from the date string
                published_date = published_date.split(",")[-1].strip()
                if len(published_date) > 4:
                    published_date = published_date[-4:]
            except Exception as e:
                logger.error(f"Error parsing date '{published_date}': {str(e)}")

        # Create BookEnrichmentData
        return BookEnrichmentData(
            isbn=isbn,
            title=book_data.get("title", ""),
            authors=authors,
            description=description,
            published_date=published_date,
            page_count=book_data.get("number_of_pages", 0),
            language=self._extract_language(book_data),
            categories=categories,
            thumbnail=thumbnail,
            preview_link=preview_link,
            rating=0.0,  # Open Library doesn't provide ratings
            reviews_count=0,
            source="Open Library",
            industry_identifiers=industry_identifiers,
        )

    def _extract_language(self, book_data: Dict[str, Any]) -> str:
        """
        Extract language from book data.

        Args:
            book_data: Book data from Open Library API

        Returns:
            str: Language code or empty string
        """
        if "languages" not in book_data or not book_data["languages"]:
            return ""

        language = book_data["languages"][0]
        if isinstance(language, dict):
            if "key" in language:
                return language["key"].split("/")[-1]
            return language.get("name", "")
        return str(language)
