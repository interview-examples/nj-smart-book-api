from abc import ABC, abstractmethod
from typing import Optional, List, Any

class BaseRepository(ABC):
    """Абстрактный базовый класс для всех репозиториев."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[Any]:
        """Получение объекта по ID."""
        pass

    @abstractmethod
    def get_all(self) -> List[Any]:
        """Получение всех объектов."""
        pass

    @abstractmethod
    def create(self, **kwargs) -> Any:
        """Создание нового объекта."""
        pass

    @abstractmethod
    def update(self, id: int, **kwargs) -> Optional[Any]:
        """Обновление объекта по ID."""
        pass

    @abstractmethod
    def delete(self, id: int) -> bool:
        """Удаление объекта по ID."""
        pass
