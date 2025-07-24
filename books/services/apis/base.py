"""
Base classes and interfaces for all external API services.
Defines the contract for all book data providers and review services.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, TypeVar, Generic

# Defining a generic type for an API result
T = TypeVar("T")


class APIException(Exception):
    """Base exception for all API-related errors."""

    def __init__(
        self,
        message: str,
        source: str = None,
        original_error: Exception = None,
        status_code: int = None,
    ):
        self.message = message
        self.source = source
        self.original_error = original_error
        self.status_code = status_code
        super().__init__(f"{source + ': ' if source else ''}API Error: {message}")


class APITimeoutException(APIException):
    """Exception raised when an API request times out."""

    pass


class APIResponseException(APIException):
    """Exception raised when an API returns an error response."""

    def __init__(self, message: str, status_code: int = None, **kwargs):
        kwargs["status_code"] = status_code
        super().__init__(message, **kwargs)


class BaseAPIService(ABC):
    """Base abstract class for all external API services."""

    @abstractmethod
    def _make_request(
        self,
        url: str,
        params: Dict[str, Any] = None,
        headers: Dict[str, str] = None,
        timeout: int = 10,
    ) -> Any:
        """
        Execute an HTTP request with error handling and logging.

        Args:
            url: URL to make the request to
            params: Query parameters for the request
            headers: HTTP headers to include
            timeout: Request timeout in seconds

        Returns:
            Any: Parsed response data

        Raises:
            APITimeoutException: If the request times out
            APIResponseException: If the API returns an error response
            APIException: For other API-related errors
        """
        pass


class DataProvider(Generic[T], BaseAPIService):
    """Generic interface for any data provider service."""

    @abstractmethod
    def get_data(self, identifier: str) -> Optional[T]:
        """
        Retrieve data by an identifier.

        Args:
            identifier: Unique identifier for the resource

        Returns:
            Optional[T]: Data object or None if not found
        """
        pass


class BookDataService(BaseAPIService):
    """Abstract class for API services that provide book data."""

    @abstractmethod
    def get_book_data(self, isbn: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve book data by ISBN.

        Args:
            isbn: ISBN of the book

        Returns:
            Optional[Dict[str, Any]]: Raw book data or None if not found
        """
        pass

    @abstractmethod
    def search_books(
        self,
        query: str = "",
        title: str = "",
        author: str = "",
        isbn: str = "",
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search for books by various criteria.

        Args:
            query: General search query
            title: Book title
            author: Book author
            isbn: Book ISBN
            limit: Maximum number of results

        Returns:
            List[Dict[str, Any]]: List of raw book data
        """
        pass


class ReviewService(BaseAPIService):
    """Abstract class for API services that provide book reviews."""

    @abstractmethod
    def get_book_review(self, isbn: str) -> Optional[str]:
        """
        Retrieve a book review by ISBN.

        Args:
            isbn: ISBN of the book

        Returns:
            Optional[str]: Book review or None if not found
        """
        pass
