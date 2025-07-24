from typing import Optional, List
from books.models import Book, BookISBN, Author

class EnrichmentService:
    """Simple service for enriching book data from external sources."""

    def __init__(self):
        # Import here to avoid circular imports
        try:
            from books.services.enrichment.service import BookEnrichmentService
            self.external_service = BookEnrichmentService()
        except ImportError:
            self.external_service = None

    def enrich_book_by_isbn(self, isbn: str) -> Optional[Book]:
        """Enrich book data by ISBN."""
        if not isbn or not self.external_service:
            return None
            
        try:
            enriched_data = self.external_service.enrich_book_data(isbn)
            if not enriched_data:
                return None
                
            # Try to find existing book
            clean_isbn = isbn.replace('-', '').replace(' ', '')
            try:
                book_isbn = BookISBN.objects.get(isbn__iexact=clean_isbn)
                book = book_isbn.book
                # Update existing book
                if enriched_data.title:
                    book.title = enriched_data.title
                if enriched_data.description:
                    book.description = enriched_data.description
                if enriched_data.published_date:
                    book.published_date = enriched_data.published_date
                book.save()
            except BookISBN.DoesNotExist:
                # Create new book
                book = Book.objects.create(
                    title=enriched_data.title or 'Unknown Title',
                    description=enriched_data.description or '',
                    published_date=enriched_data.published_date
                )
                
                # Add authors
                if hasattr(enriched_data, 'authors') and enriched_data.authors:
                    for author_name in enriched_data.authors:
                        if isinstance(author_name, str):
                            author, _ = Author.objects.get_or_create(name=author_name)
                            book.authors.add(author)
                
                # Add ISBN
                isbn_type = 'ISBN-13' if len(clean_isbn) == 13 else 'ISBN-10'
                BookISBN.objects.get_or_create(book=book, isbn=clean_isbn, defaults={'type': isbn_type})
            
            return book
        except Exception as e:
            # Log error and return None
            print(f"Error enriching book: {e}")
            return None

    def search_external(self, query: str, limit: int = 10) -> List[dict]:
        """Search for books in external APIs."""
        if not query or not self.external_service:
            return []
            
        try:
            results = self.external_service.search_books(query=query, limit=limit)
            return [self._format_book_data(result) for result in results if result]
        except Exception as e:
            print(f"Error searching external APIs: {e}")
            return []

    def _format_book_data(self, enriched_data) -> dict:
        """Format enriched data for API response."""
        try:
            return {
                'title': getattr(enriched_data, 'title', ''),
                'authors': getattr(enriched_data, 'authors', []) or [],
                'description': getattr(enriched_data, 'description', ''),
                'published_date': getattr(enriched_data, 'published_date', ''),
                'isbn': getattr(enriched_data, 'isbn', ''),
                'cover_url': getattr(enriched_data, 'cover_url', ''),
                'data_source': getattr(enriched_data, 'data_source', 'unknown')
            }
        except Exception:
            return {
                'title': 'Unknown',
                'authors': [],
                'description': '',
                'published_date': '',
                'isbn': '',
                'cover_url': '',
                'data_source': 'unknown'
            }
