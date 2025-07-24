"""
Google Books API service implementation.
Provides methods to search for books and retrieve book data from Google Books.
"""

import logging
import requests
import json
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


class GoogleBooksService(BookDataService):
    """
    Service for interacting with Google Books API.
    Implements methods to search and retrieve book data.
    """

    BASE_URL = "https://www.googleapis.com/books/v1"
    CACHE_TIMEOUT = getattr(
        settings, "GOOGLE_BOOKS_CACHE_TIMEOUT", 14400
    )  # 4 hours default

    def __init__(self):
        """Initialize the Google Books service with API key from settings."""
        self.api_key = getattr(settings, "GOOGLE_BOOKS_API_KEY", None)

    def _make_request(
        self,
        url: str,
        params: Dict[str, Any] = None,
        headers: Dict[str, str] = None,
        timeout: int = 10,
    ) -> Any:
        """
        Make a request to Google Books API with error handling.

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
        # Add API key to params if available
        if self.api_key:
            params = params or {}
            params["key"] = self.api_key

        try:
            response = requests.get(
                url, params=params, headers=headers, timeout=timeout
            )
            response.raise_for_status()
            return response.json()

        except requests.Timeout as e:
            raise APITimeoutException(
                message=f"Request to Google Books API timed out after {timeout}s",
                source="GoogleBooksAPI",
                original_error=e,
            )

        except requests.HTTPError as e:
            status_code = e.response.status_code if hasattr(e, "response") else None
            raise APIResponseException(
                message=f"HTTP error from Google Books API: {str(e)}",
                source="GoogleBooksAPI",
                original_error=e,
                status_code=status_code,
            )

        except requests.RequestException as e:
            raise APIException(
                message=f"Request error: {str(e)}",
                source="GoogleBooksAPI",
                original_error=e,
            )

    @cached_api_call(cache_timeout=CACHE_TIMEOUT)
    def get_book_data(self, isbn: str) -> Optional[Dict[str, Any]]:
        """
        Get book data from Google Books API by ISBN.

        Args:
            isbn: ISBN of the book to retrieve

        Returns:
            Optional[Dict[str, Any]]: Raw book data or None if not found
        """
        url = f"{self.BASE_URL}/volumes"
        params = {"q": f"isbn:{isbn}", "maxResults": 1}

        try:
            data = self._make_request(url, params)
            if not data or not data.get("items"):
                logger.info(f"No book found for ISBN {isbn} in Google Books API")
                return None

            # Return the first item's volumeInfo
            return data["items"][0].get("volumeInfo", {})

        except APIException as e:
            logger.error(f"Error retrieving book data for ISBN {isbn}: {str(e)}")
            return None

    @cached_api_call(cache_timeout=CACHE_TIMEOUT)
    def search_books(
        self,
        query: str = "",
        title: str = "",
        author: str = "",
        authors: List[str] = None,
        publisher: str = "",
        subject: str = "",
        isbn: str = "",
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search for books in Google Books API.

        Args:
            query: General search query
            title: Book title
            author: Book author (legacy parameter, use authors instead)
            authors: List of book authors
            publisher: Book publisher
            subject: Book subject/category
            isbn: Book ISBN
            limit: Maximum number of results (default: 10)

        Returns:
            List[Dict[str, Any]]: List of raw book data
        """
        url = f"{self.BASE_URL}/volumes"
        search_query = []

        if query:
            search_query.append(query)
        if title:
            search_query.append(f"intitle:{title}")
        if authors:
            # Use the new authors list parameter
            for author_name in authors:
                if author_name:
                    search_query.append(f"inauthor:{author_name}")
        elif (
            author
        ):  # Fallback to legacy author parameter if authors list is not provided
            search_query.append(f"inauthor:{author}")
        if publisher:
            search_query.append(f"inpublisher:{publisher}")
        if subject:
            search_query.append(f"subject:{subject}")
        if isbn:
            search_query.append(f"isbn:{isbn}")

        if not search_query:
            logger.warning("No search criteria provided for Google Books search")
            return []

        params = {
            "q": " ".join(search_query),
            "maxResults": min(limit, 40),  # Google Books API has a limit of 40 results
        }

        try:
            data = self._make_request(url, params)
            if not data or not data.get("items"):
                return []

            # Extract volumeInfo from each item
            return [item.get("volumeInfo", {}) for item in data["items"]]

        except APIException as e:
            logger.error(f"Error in search_books: {str(e)}")
            return []

    def to_enrichment_data(
        self, volume_info: Dict[str, Any], base_isbn: str = ""
    ) -> BookEnrichmentData:
        """
        Convert Google Books API volume info to BookEnrichmentData.

        Args:
            volume_info: Volume info from Google Books API
            base_isbn: ISBN to use if none found in volume_info

        Returns:
            BookEnrichmentData: Converted enrichment data
        """
        # Extract industry identifiers
        identifiers = []
        for identifier in volume_info.get("industryIdentifiers", []):
            id_type = identifier.get("type", "")
            # Convert Google's identifier types to our standard format
            if id_type == "ISBN_10":
                id_type = "ISBN-10"
            elif id_type == "ISBN_13":
                id_type = "ISBN-13"

            identifiers.append(
                IndustryIdentifier(
                    type=id_type, identifier=identifier.get("identifier", "")
                )
            )

        # Get primary ISBN
        isbn = base_isbn
        if not isbn and identifiers:
            # Prefer ISBN-13 if available
            for id_obj in identifiers:
                if id_obj.type == "ISBN-13":
                    isbn = id_obj.identifier
                    break
            # Fall back to ISBN-10 if no ISBN-13
            if not isbn:
                for id_obj in identifiers:
                    if id_obj.type == "ISBN-10":
                        isbn = id_obj.identifier
                        break

        # Parse date to get just the year
        published_date = volume_info.get("publishedDate")
        if published_date:
            try:
                # Extract just the year from the date string
                published_date = published_date.split("-")[0]
            except Exception as e:
                logger.error(f"Error parsing date '{published_date}': {str(e)}")

        # Get thumbnail URL if available
        thumbnail = None
        if "imageLinks" in volume_info and "thumbnail" in volume_info["imageLinks"]:
            thumbnail = volume_info["imageLinks"]["thumbnail"]

        # Handle description - return None instead of empty string
        description = volume_info.get("description")
        if description == "":
            description = None

        # Create BookEnrichmentData object
        return BookEnrichmentData(
            isbn=isbn,
            title=volume_info.get("title"),
            subtitle=volume_info.get("subtitle"),
            authors=volume_info.get("authors", []),
            description=description,
            publisher=volume_info.get("publisher"),
            published_date=published_date,
            page_count=volume_info.get("pageCount"),
            language=volume_info.get("language"),
            categories=volume_info.get("categories", []),
            thumbnail=thumbnail,
            preview_link=volume_info.get("previewLink"),
            rating=volume_info.get("averageRating"),
            reviews_count=volume_info.get("ratingsCount"),
            source="Google Books",
            industry_identifiers=identifiers,
        )
