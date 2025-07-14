from typing import Optional, List, Dict
from books.models import Book
from books.repositories.book_repository import BookRepository

class BookService:
    """Сервис для бизнес-логики работы с книгами."""

    def __init__(self, repository: BookRepository = None):
        self.repository = repository or BookRepository()

    def get_book_by_id(self, book_id: int) -> Optional[Book]:
        """Получение книги по ID."""
        return self.repository.get_by_id(book_id)

    def get_all_books(self) -> List[Book]:
        """Получение списка всех книг."""
        return self.repository.get_all()

    def create_book(self, data: Dict) -> Book:
        """Создание новой книги."""
        return self.repository.create(**data)

    def update_book(self, book_id: int, data: Dict) -> Optional[Book]:
        """Обновление данных книги."""
        return self.repository.update(book_id, **data)

    def delete_book(self, book_id: int) -> bool:
        """Удаление книги."""
        return self.repository.delete(book_id)

    def get_book_by_isbn(self, isbn: str) -> Optional[Book]:
        """Получение книги по ISBN."""
        from books.models import BookISBN
        try:
            book_isbn = BookISBN.objects.get(isbn=isbn)
            return book_isbn.book
        except BookISBN.DoesNotExist:
            return None

    def search_books(self, query: str) -> List[Book]:
        """Поиск книг по названию или автору."""
        return self.repository.search(query)
