from typing import Optional, List
from django.db.models import Q
from books.models import Book, BookISBN
from books.repositories.base import BaseRepository
import logging

logger = logging.getLogger(__name__)

class BookRepository(BaseRepository):
    """Репозиторий для работы с моделью Book через Django ORM."""

    def get_by_id(self, id: int) -> Optional[Book]:
        """Получение книги по ID."""
        try:
            return Book.objects.get(id=id)
        except Book.DoesNotExist:
            return None

    def get_all(self) -> List[Book]:
        """Получение всех книг."""
        return list(Book.objects.all())

    def create(self, **kwargs) -> Book:
        """Создание новой книги."""
        return Book.objects.create(**kwargs)

    def update(self, id: int, **kwargs) -> Optional[Book]:
        """Обновление книги по ID."""
        try:
            book = Book.objects.get(id=id)
            for key, value in kwargs.items():
                setattr(book, key, value)
            book.save()
            return book
        except Book.DoesNotExist:
            return None

    def delete(self, id: int) -> bool:
        """Удаление книги по ID."""
        try:
            book = Book.objects.get(id=id)
            book.delete()
            return True
        except Book.DoesNotExist:
            return False

    def get_by_isbn(self, isbn: str) -> Optional[Book]:
        """Получение книги по ISBN."""
        try:
            book_isbn = BookISBN.objects.get(isbn=isbn)
            return book_isbn.book
        except BookISBN.DoesNotExist:
            return None

    def search(self, query: str) -> List[Book]:
        """Поиск книг по названию или автору."""
        return list(Book.objects.filter(
            Q(title__icontains=query) | Q(author__icontains=query)
        ))

    def create_isbn(self, book: Book, isbn_value: str, isbn_type: str) -> Optional[BookISBN]:
        """
        Создание дополнительной записи ISBN для книги.
        
        Args:
            book: Экземпляр книги
            isbn_value: Значение ISBN
            isbn_type: Тип ISBN (ISBN-10 или ISBN-13)
            
        Returns:
            Optional[BookISBN]: Созданный объект BookISBN или None, если объект уже существует
        """
        try:
            # Проверяем существование ISBN перед созданием
            if not BookISBN.objects.filter(book=book, isbn=isbn_value).exists():
                return BookISBN.objects.create(book=book, isbn=isbn_value, type=isbn_type)
            return None
        except Exception as e:
            # Логируем ошибку
            from django.core.exceptions import ValidationError
            if isinstance(e, ValidationError):
                # Более подробное логирование для ошибок валидации
                logger.warning(f"Validation error creating ISBN {isbn_value} for book {book.id}: {str(e)}")
            else:
                # Общее логирование для других исключений
                logger.error(f"Error creating ISBN {isbn_value} for book {book.id}: {str(e)}")
            return None
