from typing import Optional, Dict, Any, List
from books.services.external_apis import BookEnrichmentService as ExternalEnrichmentService
from books.models import Book, BookISBN
from books.services.book_service import BookService

class EnrichmentService:
    """Сервис для обогащения данных книг и поиска во внешних источниках."""

    def __init__(self, external_service: ExternalEnrichmentService = None, book_service: BookService = None):
        self.external_service = external_service or ExternalEnrichmentService()
        self.book_service = book_service or BookService()

    def enrich_book_by_isbn(self, isbn: str) -> Optional[Dict[str, Any]]:
        """Обогащение данных книги по ISBN из внешних источников."""
        # Сначала проверяем, есть ли книга в локальной базе
        book = self.book_service.get_book_by_isbn(isbn)
        enriched_data = self.external_service.enrich_book_data(isbn)
        if enriched_data:
            enriched_dict = enriched_data.__dict__  # Преобразуем в словарь
            # Добавляем логику для сохранения нескольких ISBN
            isbn_list = enriched_dict.get('industryIdentifiers', [])
            if book:
                updated_book = self.book_service.update_book(book.id, enriched_dict)
                if updated_book and isbn_list:
                    # Обновляем список ISBN для существующей книги
                    self._update_book_isbns(updated_book, isbn_list)
                return self._format_book_data(updated_book) if updated_book else None
            else:
                new_book = self.book_service.create_book(enriched_dict)
                if new_book and isbn_list:
                    # Создаем записи ISBN для новой книги
                    self._create_book_isbns(new_book, isbn_list)
                return self._format_book_data(new_book)
        return None

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

    def _create_book_isbns(self, book: Book, isbn_list: List[Dict[str, str]]) -> None:
        """Создание записей ISBN для новой книги."""
        for isbn_data in isbn_list:
            isbn_value = isbn_data.get('identifier', '')
            isbn_type = isbn_data.get('type', '').replace('ISBN_', 'ISBN-')
            if isbn_value and isbn_type in ['ISBN-10', 'ISBN-13']:
                BookISBN.objects.create(book=book, isbn=isbn_value, type=isbn_type)

    def _update_book_isbns(self, book: Book, isbn_list: List[Dict[str, str]]) -> None:
        """Обновление записей ISBN для существующей книги."""
        # Удаляем существующие ISBN, чтобы избежать дубликатов
        book.isbns.all().delete()
        # Создаем новые записи ISBN
        for isbn_data in isbn_list:
            isbn_value = isbn_data.get('identifier', '')
            isbn_type = isbn_data.get('type', '').replace('ISBN_', 'ISBN-')
            if isbn_value and isbn_type in ['ISBN-10', 'ISBN-13']:
                BookISBN.objects.create(book=book, isbn=isbn_value, type=isbn_type)
