from typing import Optional, List
from django.db.models import Q
from books.models import Book, BookISBN
from books.repositories.base import BaseRepository
import logging

logger = logging.getLogger(__name__)


class BookRepository(BaseRepository):
    """Repository for working with the Book model through Django ORM."""

    def get_by_id(self, id: int) -> Optional[Book]:
        """
        Get a book by its ID.

        Args:
            id: Book ID

        Returns:
            Optional[Book]: Book object or None if not found
        """
        try:
            return Book.objects.get(id=id)
        except Book.DoesNotExist:
            return None

    def get_all(self) -> List[Book]:
        """
        Get all books.

        Returns:
            List[Book]: List of all book objects
        """
        return list(Book.objects.all())

    def create(self, **kwargs) -> Book:
        """
        Create a new book.

        Args:
            **kwargs: Book attributes

        Returns:
            Book: Created book object
        """
        authors = kwargs.pop("authors", None)
        book = Book.objects.create(**kwargs)

        # Set authors after book is created
        if authors:
            book.authors.set(authors)

        return book

    def update(self, id: int, **kwargs) -> Optional[Book]:
        """
        Update a book by ID.

        Args:
            id: Book ID
            **kwargs: Book attributes to update

        Returns:
            Optional[Book]: Updated book object or None if not found
        """
        try:
            book = Book.objects.get(id=id)

            authors = kwargs.pop("authors", None)

            for key, value in kwargs.items():
                setattr(book, key, value)

            book.save()

            # Set authors if provided
            if authors:
                book.authors.set(authors)

            return book
        except Book.DoesNotExist:
            logger.warning(f"Book with ID {id} not found for update")
            return None

    def delete(self, id: int) -> bool:
        """
        Delete a book by ID.

        Args:
            id: Book ID

        Returns:
            bool: True if deletion was successful, False otherwise
        """
        try:
            book = Book.objects.get(id=id)
            book.delete()
            return True
        except Book.DoesNotExist:
            return False

    def get_by_isbn(self, isbn: str) -> Optional[Book]:
        """
        Get a book by ISBN.

        Args:
            isbn: ISBN to search for

        Returns:
            Optional[Book]: Book object or None if not found
        """
        try:
            book_isbn = BookISBN.objects.get(isbn=isbn)
            return book_isbn.book
        except BookISBN.DoesNotExist:
            return None

    def search(self, query: str) -> List[Book]:
        """
        Search for books by title or author.

        Args:
            query: Search query string

        Returns:
            List[Book]: List of matching book objects
        """
        return list(
            Book.objects.filter(Q(title__icontains=query) | Q(author__icontains=query))
        )

    def create_isbn(
        self, book: Book, isbn_value: str, isbn_type: str
    ) -> Optional[BookISBN]:
        """
        Create an additional ISBN record for a book.

        Args:
            book: Book instance
            isbn_value: ISBN value
            isbn_type: ISBN type (ISBN-10 or ISBN-13)

        Returns:
            Optional[BookISBN]: Created BookISBN object or None if the object already exists
        """
        try:
            # Check if ISBN exists before creating
            if not BookISBN.objects.filter(book=book, isbn=isbn_value).exists():
                return BookISBN.objects.create(
                    book=book, isbn=isbn_value, type=isbn_type
                )
            return None
        except Exception as e:
            # Log the error
            from django.core.exceptions import ValidationError

            if isinstance(e, ValidationError):
                # More detailed logging for validation errors
                logger.warning(
                    f"Validation error creating ISBN {isbn_value} for book {book.id}: {str(e)}"
                )
            else:
                # General logging for other exceptions
                logger.error(
                    f"Error creating ISBN {isbn_value} for book {book.id}: {str(e)}"
                )
            return None
