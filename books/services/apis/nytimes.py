"""
NY Times Books API service implementation.
Provides methods to retrieve book reviews from NY Times Books API.
"""

import logging
import requests
from typing import Dict, Any, Optional, List

from django.conf import settings

from books.services.apis.base import ReviewService, APIException, APITimeoutException, APIResponseException
from books.services.caching.decorators import cached_api_call

logger = logging.getLogger(__name__)


class NYTimesService(ReviewService):
    """
    Service for interacting with NY Times Books API.
    Implements methods to retrieve book reviews.
    """

    BASE_URL = "https://api.nytimes.com/svc/books/v3"
    CACHE_TIMEOUT = getattr(settings, 'NY_TIMES_CACHE_TIMEOUT', 14400)  # 4 hours default

    def __init__(self):
        """Initialize the NY Times Books API service with API key from settings."""
        self.api_key = getattr(settings, 'NY_TIMES_API_KEY', None)
        if not self.api_key:
            logger.warning("No NY Times API key found in settings. Review functionality will be limited.")

    def _make_request(self,
                     url: str,
                     params: Dict[str, Any] = None,
                     headers: Dict[str, str] = None,
                     timeout: int = 10) -> Any:
        """
        Make a request to NY Times API with error handling.

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
        # Add API key to params
        if self.api_key:
            params = params or {}
            params['api-key'] = self.api_key

        try:
            response = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=timeout
            )
            response.raise_for_status()
            return response.json()

        except requests.Timeout as e:
            raise APITimeoutException(
                message=f"Request to NY Times API timed out after {timeout}s",
                source="NYTimesAPI",
                original_error=e
            )

        except requests.HTTPError as e:
            status_code = e.response.status_code if hasattr(e, 'response') else None
            raise APIResponseException(
                message=f"HTTP error from NY Times API: {str(e)}",
                source="NYTimesAPI",
                original_error=e,
                status_code=status_code
            )

        except requests.RequestException as e:
            raise APIException(
                message=f"Request error: {str(e)}",
                source="NYTimesAPI",
                original_error=e
            )

        except ValueError as e:
            # JSON parsing error
            raise APIException(
                message=f"Invalid JSON response: {str(e)}",
                source="NYTimesAPI",
                original_error=e
            )

    @cached_api_call(cache_timeout=CACHE_TIMEOUT)
    def get_book_review(self, isbn: str) -> Optional[str]:
        """
        Get book review from NY Times Books API by ISBN.

        Args:
            isbn: ISBN of the book to get review for

        Returns:
            Optional[str]: Book review summary or None if not found
        """
        if not self.api_key:
            logger.warning("Cannot retrieve NY Times review: No API key configured")
            return None

        url = f"{self.BASE_URL}/reviews.json"
        params = {'isbn': isbn}

        try:
            data = self._make_request(url, params)

            # Check if results were found
            if not data or data.get('num_results', 0) == 0 or not data.get('results'):
                logger.info(f"No NY Times review found for ISBN {isbn}")
                return None

            # Return the summary from the first review
            return data['results'][0].get('summary', None)

        except APIException as e:
            logger.error(f"Error retrieving NY Times review for ISBN {isbn}: {str(e)}")
            return None

    def get_bestsellers(self, list_name: str = "hardcover-fiction") -> Dict[str, Any]:
        """
        Get bestsellers list from NY Times Books API.

        Args:
            list_name: Name of the bestseller list to retrieve

        Returns:
            Dict[str, Any]: Bestseller list data or empty dict if not found
        """
        if not self.api_key:
            logger.warning("Cannot retrieve NY Times bestsellers: No API key configured")
            return {}

        url = f"{self.BASE_URL}/lists/current/{list_name}.json"

        try:
            data = self._make_request(url)
            return data.get('results', {})

        except APIException as e:
            logger.error(f"Error retrieving NY Times bestseller list '{list_name}': {str(e)}")
            return {}

    @cached_api_call(cache_timeout=CACHE_TIMEOUT)
    def get_bestseller_lists(self) -> List[Dict[str, Any]]:
        """
        Get all available bestseller lists from NY Times Books API.
        
        This is different from get_list_names() which only returns the names.
        This method returns full details about each list.

        Returns:
            List[Dict[str, Any]]: List of bestseller lists with full details
        """
        if not self.api_key:
            logger.warning("Cannot retrieve NY Times bestseller lists: No API key configured")
            return []

        url = f"{self.BASE_URL}/lists/names.json"

        try:
            data = self._make_request(url)
            if not data or not data.get('results'):
                return []

            return data.get('results', [])

        except APIException as e:
            logger.error(f"Error retrieving NY Times bestseller lists: {str(e)}")
            return []

    def get_list_names(self) -> list:
        """
        Get all available bestseller list names from NY Times Books API.

        Returns:
            list: List of available bestseller list names
        """
        if not self.api_key:
            logger.warning("Cannot retrieve NY Times list names: No API key configured")
            return []

        url = f"{self.BASE_URL}/lists/names.json"

        try:
            data = self._make_request(url)
            if not data or not data.get('results'):
                return []

            return [result.get('list_name_encoded') for result in data.get('results', [])]

        except APIException as e:
            logger.error(f"Error retrieving NY Times list names: {str(e)}")
            return []
