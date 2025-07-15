from typing import Optional, Dict, Any, List
from books.services.enrichment.service import BookEnrichmentService
from books.models import Book, BookISBN
from books.services.book_service import BookService
from books.repositories.book_repository import BookRepository

class EnrichmentService:
    """Service for enriching book data from external sources."""

    def __init__(self, book_service: BookService, external_service=None, book_repository=None):
        """
        Initialize the service with dependency injection.
        
        Args:
            book_service: Service for working with books
            external_service: Service for enriching book data. If None, a default instance is created.
            book_repository: Repository for working with books. If None, a default instance is created.
        """
        self.book_service = book_service
        self.external_service = external_service or BookEnrichmentService()
        self.repository = book_repository or BookRepository()

    def enrich_book_by_isbn(self, isbn: str) -> Optional[Book]:
        """
        Enriches book data by ISBN using an external service.
        If the book already exists, updates it; if not, creates a new one.
        
        Args:
            isbn: ISBN of the book to enrich.
            
        Returns:
            Optional[Book]: Enriched book object or None if enrichment failed.
        """
        book = self.book_service.get_book_by_isbn(isbn)
        enriched_data = self.external_service.enrich_book_data(isbn)
        if not enriched_data:
            return None
        # Check if enriched_data is a dictionary or an object with a dict() method
        if hasattr(enriched_data, 'dict'):
            enriched_dict = enriched_data.dict()
        else:
            enriched_dict = vars(enriched_data) if not isinstance(enriched_data, dict) else enriched_data
        # Filter only supported fields for the Book model
        valid_fields = {field.name for field in Book._meta.get_fields()}
        filtered_data = {k: v for k, v in enriched_dict.items() if k in valid_fields}
        if book:
            updated_book = self.book_service.update_book(book.id, filtered_data)
            if updated_book:
                self.create_additional_isbns(updated_book, enriched_dict.get('industryIdentifiers', []))
            return updated_book
        else:
            new_book = self.book_service.create_book(filtered_data)
            if new_book:
                self.create_additional_isbns(new_book, enriched_dict.get('industryIdentifiers', []))
            return new_book

    def search_external(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for books in external sources.
        
        Args:
            query: Search query string
            
        Returns:
            List[Dict[str, Any]]: List of search results from external APIs
        """
        results = []
        # Here we can implement search through multiple external APIs
        google_results = self.external_service.google_books.search_books(query)
        if google_results:
            results.extend(google_results)
        open_library_results = self.external_service.open_library.search_books(query)
        if open_library_results:
            results.extend(open_library_results)
        return results

    def _format_book_data(self, book: Book) -> Dict[str, Any]:
        """
        Format book data for API response.
        
        Args:
            book: Book object to format
            
        Returns:
            Dict[str, Any]: Formatted book data
        """
        return {
            'id': book.id,
            'title': book.title,
            'author': book.author,
            'isbn': book.isbn,
            'description': book.description,
            'published_date': book.published_date,
            # Add other fields if they exist in the model
        }

    def create_additional_isbns(self, book: Book, isbn_list: List[Dict[str, str]]) -> None:
        """
        Create ISBN records for a book.
        
        Args:
            book: Book object
            isbn_list: List of dictionaries with ISBN data
        """
        if not isbn_list:  # Protection against None and empty lists
            return
            
        for isbn_data in isbn_list:
            isbn_value = isbn_data.get('identifier', '')
            # Ensure consistency in ISBN type format, converting all to hyphenated format
            isbn_type_raw = isbn_data.get('type', '')
            
            # Accept both underscore format (ISBN_10) and hyphenated format (ISBN-10)
            if isbn_type_raw in ['ISBN_10', 'ISBN-10']:
                isbn_type = 'ISBN-10'
            elif isbn_type_raw in ['ISBN_13', 'ISBN-13']:
                isbn_type = 'ISBN-13'
            else:
                continue  # Skip if not a recognized ISBN type
                
            # Create ISBN record if it doesn't exist
            if isbn_value and len(isbn_value) > 0:
                BookISBN.objects.get_or_create(book=book, isbn=isbn_value, isbn_type=isbn_type)
