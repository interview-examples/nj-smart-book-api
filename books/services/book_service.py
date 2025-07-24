from typing import Optional, List, Union
from books.models import Book, BookISBN, Author
from datetime import datetime


class BookService:
    """Simple service for book operations."""

    def get_book_by_id(self, book_id: int) -> Optional[Book]:
        """Get a book by its ID."""
        try:
            return Book.objects.get(id=book_id)
        except Book.DoesNotExist:
            return None

    def get_all_books(self) -> List[Book]:
        """Get all books."""
        return list(Book.objects.all())

    def get_book_by_isbn(self, isbn: str) -> Optional[Book]:
        """Get a book by its ISBN."""
        if not isbn:
            return None

        clean_isbn = isbn.replace("-", "").replace(" ", "")

        # Try BookISBN table first (using filter as expected by tests)
        book_isbn = BookISBN.objects.filter(isbn__iexact=clean_isbn).first()
        if book_isbn:
            return book_isbn.book

        # Try to find by main isbn field in Book model
        try:
            return Book.objects.get(isbn__iexact=clean_isbn)
        except Book.DoesNotExist:
            return None

    def get_book_by_all_isbns(self, isbn: Union[str, List[str]]) -> Optional[Book]:
        """Get a book by any of its associated ISBNs."""
        if not isbn:
            return None

        # Handle both single ISBN string and list of ISBNs
        if isinstance(isbn, list):
            for single_isbn in isbn:
                book = self.get_book_by_isbn(single_isbn)
                if book:
                    return book
            return None
        else:
            return self.get_book_by_isbn(isbn)

    def create_book(
        self,
        data=None,
        title: str = None,
        authors: List[str] = None,
        isbn: str = None,
        description: str = None,
        published_date: str = None,
    ) -> Book:
        """Create a new book - supports both dict and kwargs."""
        # Handle legacy dict format
        if data and isinstance(data, dict):
            title = data.get("title", title)
            authors = data.get("authors", authors or [])
            isbn = data.get("isbn", isbn)
            description = data.get("description", description)
            published_date = data.get("published_date", published_date)

        # ISBN is required for any book
        if not isbn:
            raise ValueError("ISBN is required for creating a book")

        # Handle published_date conversion
        parsed_date = None
        if published_date:
            try:
                if isinstance(published_date, str):
                    parsed_date = datetime.strptime(published_date, "%Y-%m-%d").date()
                else:
                    parsed_date = published_date
            except ValueError:
                parsed_date = None

        # Use default date if none provided (required field)
        if not parsed_date:
            parsed_date = datetime.now().date()

        # Clean the provided ISBN
        clean_isbn = isbn.replace("-", "").replace(" ", "")

        book = Book.objects.create(
            title=title or "Unknown Title",
            isbn=clean_isbn,
            description=description or "",
            published_date=parsed_date,
        )

        # Add authors
        if authors:
            for author_name in authors:
                if isinstance(author_name, str):
                    author, _ = Author.objects.get_or_create(name=author_name)
                    book.authors.add(author)
                elif hasattr(author_name, "name"):  # Author object
                    book.authors.add(author_name)

        # Add ISBN if provided
        isbn_type = "ISBN-13" if len(clean_isbn) == 13 else "ISBN-10"
        BookISBN.objects.get_or_create(
            book=book, isbn=clean_isbn, defaults={"type": isbn_type}
        )

        return book

    def update_book(self, book_id: int, data=None, **kwargs) -> Optional[Book]:
        """Update an existing book - supports both dict and kwargs."""
        try:
            book = Book.objects.get(id=book_id)

            # Handle legacy dict format
            if data and isinstance(data, dict):
                kwargs.update(data)

            # Handle special fields
            if "authors" in kwargs:
                authors = kwargs.pop("authors")
                book.authors.clear()
                if authors:
                    for author_name in authors:
                        if isinstance(author_name, str):
                            author, _ = Author.objects.get_or_create(name=author_name)
                            book.authors.add(author)
                        elif hasattr(author_name, "name"):  # Author object
                            book.authors.add(author_name)

            if "published_date" in kwargs:
                published_date = kwargs["published_date"]
                if isinstance(published_date, str):
                    try:
                        kwargs["published_date"] = datetime.strptime(
                            published_date, "%Y-%m-%d"
                        ).date()
                    except ValueError:
                        kwargs.pop("published_date")

            # Update other fields
            for field, value in kwargs.items():
                if hasattr(book, field) and value is not None:
                    setattr(book, field, value)

            book.save()
            return book
        except Book.DoesNotExist:
            return None

    def delete_book(self, book_id: int) -> bool:
        """Delete a book."""
        try:
            book = Book.objects.get(id=book_id)
            book.delete()
            return True
        except Book.DoesNotExist:
            return False

    def search_books(self, query: str) -> List[Book]:
        """Search books by title or author."""
        if not query:
            return []

        try:
            return list(
                Book.objects.filter(title__icontains=query)
                .union(Book.objects.filter(authors__name__icontains=query))
                .distinct()
            )
        except Exception:
            # Fallback to simple search if union fails
            return list(Book.objects.filter(title__icontains=query).distinct())

    def enrich_book_data(self, book: Book, enrichment_service) -> any:
        """Enrich book data using the enrichment service."""
        try:
            enrichment_data = enrichment_service.enrich_book_data(book.isbn)
            if not enrichment_data:
                return None
            return enrichment_data
        except Exception:
            return None
