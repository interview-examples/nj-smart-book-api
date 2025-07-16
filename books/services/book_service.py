from typing import Optional, List, Dict, Any, Union
from books.models import Book, BookISBN, Author
from books.repositories.book_repository import BookRepository
from datetime import datetime

class BookService:
    """Service for book business logic operations."""

    def __init__(self, repository: BookRepository = None):
        self.repository = repository or BookRepository()

    def get_book_by_id(self, book_id: int) -> Optional[Book]:
        """
        Get a book by its ID.
        
        Args:
            book_id: ID of the book to retrieve
            
        Returns:
            Optional[Book]: Book object or None if not found
        """
        return self.repository.get_by_id(book_id)

    def get_all_books(self) -> List[Book]:
        """
        Get a list of all books.
        
        Returns:
            List[Book]: List of all book objects
        """
        return self.repository.get_all()
        
    def get_book_by_isbn(self, isbn: str) -> Optional[Book]:
        """
        Get a book by its ISBN.
        
        Args:
            isbn: ISBN of the book to retrieve (ISBN-10 or ISBN-13 format)
            
        Returns:
            Optional[Book]: Book object or None if not found
        """
        if not isbn:
            return None
            
        try:
            # Clean the ISBN by removing hyphens and spaces
            clean_isbn = isbn.replace('-', '').replace(' ', '')
            
            # First try direct match
            try:
                book_isbn = BookISBN.objects.get(isbn=clean_isbn)
                return book_isbn.book
            except BookISBN.DoesNotExist:
                pass
                
            # Try match against Book model's isbn field
            try:
                book = Book.objects.get(isbn=clean_isbn)
                
                # If found, check if this book has other ISBN formats that could be useful
                other_isbns = BookISBN.objects.filter(book=book).values_list('isbn', flat=True)
                if other_isbns:
                    import logging
                    logging.info(f"Book found with ISBN {clean_isbn} also has these ISBNs: {', '.join(other_isbns)}")
                
                return book
            except Book.DoesNotExist:
                pass
                
            # Try case-insensitive search
            book_isbn = BookISBN.objects.filter(isbn__iexact=clean_isbn).first()
            if book_isbn:
                return book_isbn.book
                
            # Try search with different formatting
            book = Book.objects.filter(isbn__iexact=clean_isbn).first()
            if book:
                return book
                
            return None
        except Exception as e:
            import logging
            logging.error(f"Error searching for book by ISBN {isbn}: {str(e)}")
            return None
            
    def _process_book_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process book data before creating or updating a book.
        
        Args:
            data: Book data dictionary
            
        Returns:
            Dict[str, Any]: Processed book data
        """
        # Create a copy to avoid modifying the original
        processed_data = data.copy()
        
        # Remove unsupported fields
        processed_data.pop('auto_fill', None)
        
        # Handle authors properly
        authors = processed_data.get('authors', [])
        if isinstance(authors, list) and authors and not isinstance(authors[0], Author):
            author_objects = []
            for author_data in authors:
                if isinstance(author_data, str):
                    author, _ = Author.objects.get_or_create(name=author_data)
                    author_objects.append(author)
                else:
                    author_objects.append(author_data)
            processed_data['authors'] = author_objects
            
        return processed_data

    def create_book(self, data: dict) -> Book:
        """
        Create a new book based on provided data.
        
        Args:
            data: Data for creating the book
            
        Returns:
            Book: Created book object
        """
        processed_data = self._process_book_data(data)
        return self.repository.create(**processed_data)

    def update_book(self, book_id: int, data: Dict) -> Optional[Book]:
        """
        Update an existing book based on provided data.
        
        Args:
            book_id: ID of the book to update
            data: Data for updating the book
            
        Returns:
            Optional[Book]: Updated book object or None if book not found
        """
        processed_data = self._process_book_data(data)
        
        if 'published_date' not in processed_data or processed_data['published_date'] is None:
            processed_data['published_date'] = datetime.now().date()
            
        return self.repository.update(book_id, **processed_data)

    def delete_book(self, book_id: int) -> bool:
        """
        Delete a book.
        
        Args:
            book_id: ID of the book to delete
            
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        return self.repository.delete(book_id)

    def get_book_by_all_isbns(self, isbn: Union[str, List[str]]) -> Optional[Book]:
        """
        Get a book by any of its associated ISBNs.
        Supports both a single ISBN string or a list of ISBNs.
        
        Args:
            isbn: Single ISBN or list of ISBNs to search for
            
        Returns:
            Optional[Book]: Book found by ISBN or None
        """
        if not isbn:
            return None
            
        # Handle both single ISBN string and list of ISBNs
        if isinstance(isbn, list):
            # If it's a list, try each ISBN in turn
            for single_isbn in isbn:
                book = self.get_book_by_isbn(single_isbn)
                if book:
                    return book
            return None
        else:
            # Clean the ISBN by removing hyphens and spaces
            clean_isbn = isbn.replace('-', '').replace(' ', '')
            
            from books.models import BookISBN
            
            # First try exact match
            book_isbn = BookISBN.objects.filter(isbn=clean_isbn).first()
            if book_isbn:
                return book_isbn.book
                
            # Try case-insensitive match
            book_isbn = BookISBN.objects.filter(isbn__iexact=clean_isbn).first()
            if book_isbn:
                return book_isbn.book
                
            # Try to find similar ISBNs (e.g., conversion between ISBN-10 and ISBN-13)
            # This is a simplified approach - a proper ISBN-10 to ISBN-13 conversion would be better
            if len(clean_isbn) == 10:
                # If it's an ISBN-10, look for ISBN-13 with same ending
                possible_isbn13s = BookISBN.objects.filter(
                    isbn__endswith=clean_isbn,
                    type="ISBN-13"
                )
                if possible_isbn13s.exists():
                    return possible_isbn13s.first().book
            elif len(clean_isbn) == 13 and clean_isbn.startswith('978'):
                # If it's an ISBN-13, look for ISBN-10 with same ending minus the prefix
                possible_isbn10s = BookISBN.objects.filter(
                    isbn__endswith=clean_isbn[3:],
                    type="ISBN-10"
                )
                if possible_isbn10s.exists():
                    return possible_isbn10s.first().book
                    
            return None

    def enrich_book_data(self, book: Book, enrichment_service) -> Any:
        """
        Enrich book data using the enrichment service.
        
        Args:
            book: Book object to enrich
            enrichment_service: Service to use for enrichment
            
        Returns:
            Any: Enriched data or None if enrichment failed
        """
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
        """
        Search for books by title or author.
        
        Args:
            query: Search query
            
        Returns:
            List[Book]: List of matching book objects
        """
        return self.repository.search(query)
