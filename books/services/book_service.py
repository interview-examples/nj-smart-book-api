from typing import Optional, List, Dict, Any
from books.models import Book, BookISBN, Author
from books.repositories.book_repository import BookRepository
from datetime import datetime

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

    def create_book(self, data: dict) -> Book:
        """
        Создает новую книгу на основе предоставленных данных.
        Args:
            data: Данные для создания книги.
        Returns:
            Book: Созданный объект книги.
        """
        data.pop('auto_fill', None)  # Удаляем неподдерживаемое поле
        return self.repository.create(**data)

    def update_book(self, book_id: int, data: Dict) -> Optional[Book]:
        """
        Обновляет существующую книгу на основе предоставленных данных.
        Args:
            book_id: ID книги для обновления.
            data: Данные для обновления книги.
        Returns:
            Optional[Book]: Обновленный объект книги или None, если книга не найдена.
        """
        if 'published_date' not in data or data['published_date'] is None:
            data['published_date'] = datetime.now().date()
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

    def get_book_by_all_isbns(self, isbn: str) -> Optional[Book]:
        """Получение книги по любому из связанных ISBN."""
        from books.models import BookISBN
        book_isbn = BookISBN.objects.filter(isbn=isbn).first()
        if book_isbn:
            return book_isbn.book
        return None

    def enrich_book_data(self, book: Book, enrichment_service) -> Any:
        """Enriching book data using the enrichment service."""
        enrichment_data = enrichment_service.enrich_book_data(book.isbn)
        if not enrichment_data:
            return None

        # Update book fields with enriched data using a mapping
        field_mappings = [
            ("title", "title"),
            ("subtitle", "subtitle"),
            ("description", "description"),
            ("published_date", "published_date"),
            ("publisher", "publisher"),
            ("page_count", "page_count"),
            ("language", "language"),
            ("cover_image_url", "thumbnail"),
            ("preview_url", "preview_link"),
            ("rating", "rating"),
            ("reviews_count", "reviews_count"),
        ]
        for book_field, enrich_field in field_mappings:
            enrich_value = getattr(enrichment_data, enrich_field, None)
            if enrich_value is not None:
                setattr(book, book_field, enrich_value)

        # Handle authors - clear existing and add new ones
        if enrichment_data.authors:
            book.authors.clear()
            for author_name in enrichment_data.authors:
                author, _ = Author.objects.get_or_create(name=author_name)
                book.authors.add(author)

        book.categories = enrichment_data.categories or book.categories

        book.save()
        return enrichment_data

    def search_books(self, query: str) -> List[Book]:
        """Поиск книг по названию или автору."""
        return self.repository.search(query)
