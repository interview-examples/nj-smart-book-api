from abc import ABC, abstractmethod
from typing import Optional, List, Any

class BaseRepository(ABC):
    """Abstract base class for all repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[Any]:
        """
        Get an object by ID.
        
        Args:
            id: Object ID
            
        Returns:
            Optional[Any]: Retrieved object or None if not found
        """
        pass

    @abstractmethod
    def get_all(self) -> List[Any]:
        """
        Get all objects.
        
        Returns:
            List[Any]: List of all objects
        """
        pass

    @abstractmethod
    def create(self, **kwargs) -> Any:
        """
        Create a new object.
        
        Args:
            **kwargs: Object attributes
            
        Returns:
            Any: Created object
        """
        pass

    @abstractmethod
    def update(self, id: int, **kwargs) -> Optional[Any]:
        """
        Update an object by ID.
        
        Args:
            id: Object ID
            **kwargs: Object attributes to update
            
        Returns:
            Optional[Any]: Updated object or None if not found
        """
        pass

    @abstractmethod
    def delete(self, id: int) -> bool:
        """
        Delete an object by ID.
        
        Args:
            id: Object ID
            
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        pass
