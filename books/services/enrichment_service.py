from typing import Optional, Dict, Any, List
from books.services.external_apis import BookEnrichmentService
from books.models import Book, BookISBN
from books.services.book_service import BookService

class EnrichmentService:
    """Сервис для обогащения данных о книгах из внешних источников."""

    def __init__(self, book_service: BookService):
        self.book_service = book_service
        self.external_service = BookEnrichmentService()

    def enrich_book_by_isbn(self, isbn: str) -> Optional[Book]:
        """
        Обогащает данные о книге по ISBN, используя внешний сервис.
        Если книга уже существует, обновляет ее; если нет - создает новую.
        Args:
            isbn: ISBN книги для обогащения.
        Returns:
            Optional[Book]: Обогащенный объект книги или None, если обогащение не удалось.
        """
        book = self.book_service.get_book_by_isbn(isbn)
        enriched_data = self.external_service.enrich_book_data(isbn)
        if not enriched_data:
            return None
        # Проверяем, является ли enriched_data словарем или объектом с методом dict()
        if hasattr(enriched_data, 'dict'):
            enriched_dict = enriched_data.dict()
        else:
            enriched_dict = vars(enriched_data) if not isinstance(enriched_data, dict) else enriched_data
        # Фильтруем только поддерживаемые поля для модели Book
        valid_fields = {field.name for field in Book._meta.get_fields()}
        filtered_data = {k: v for k, v in enriched_dict.items() if k in valid_fields}
        if book:
            updated_book = self.book_service.update_book(book.id, filtered_data)
            if updated_book:
                self.create_additional_isbns(book, enriched_dict.get('industryIdentifiers', []))
            return updated_book
        else:
            new_book = self.book_service.create_book(filtered_data)
            if new_book:
                self.create_additional_isbns(new_book, enriched_dict.get('industryIdentifiers', []))
            return new_book

    def search_external(self, query: str) -> List[Dict[str, Any]]:
        """Поиск книг во внешних источниках."""
        results = []
        # Здесь можно реализовать поиск через несколько внешних API
        google_results = self.external_service.google_books.search_books(query)
        if google_results:
            results.extend(google_results)
        open_library_results = self.external_service.open_library.search_books(query)
        if open_library_results:
            results.extend(open_library_results)
        return results

    def _format_book_data(self, book: Book) -> Dict[str, Any]:
        """Форматирование данных книги для ответа API."""
        return {
            'id': book.id,
            'title': book.title,
            'author': book.author,
            'isbn': book.isbn,
            'description': book.description,
            'published_date': book.published_date,
            # Добавьте другие поля, если они есть в модели
        }

    def create_additional_isbns(self, book: Book, isbn_list: List[Dict[str, str]]) -> None:
        """Создание записей ISBN для новой книги."""
        if not isbn_list:  # Защита от None и пустых списков
            return
            
        for isbn_data in isbn_list:
            isbn_value = isbn_data.get('identifier', '')
            isbn_type = isbn_data.get('type', '').replace('ISBN_', 'ISBN-')
            if isbn_value and isbn_type in ['ISBN-10', 'ISBN-13']:
                # Проверяем наличие ISBN перед созданием
                if not BookISBN.objects.filter(book=book, isbn=isbn_value).exists():
                    BookISBN.objects.create(book=book, isbn=isbn_value, type=isbn_type)
