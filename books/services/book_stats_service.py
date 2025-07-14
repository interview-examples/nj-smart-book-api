from typing import Dict, List, Any
from datetime import datetime, timedelta
from django.db.models import Count, Q
from books.repositories.book_repository import BookRepository

class BookStatsService:
    """Сервис для получения статистики по книгам."""

    def __init__(self, repository: BookRepository = None):
        self.repository = repository or BookRepository()

    def get_stats(self) -> Dict[str, Any]:
        """Получение полной статистики по книгам."""
        books = self.repository.get_all()
        total_books = len(books)

        # Статистика по жанрам
        books_by_genre = (
            books.values('genre')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        # Статистика по авторам (топ-10)
        books_by_author = (
            books.values('author')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )

        # Статистика по датам добавления (за последний месяц)
        last_month = datetime.now() - timedelta(days=30)
        recent_books_count = books.filter(
            Q(created_at__gte=last_month) if hasattr(books.model, 'created_at') else Q()
        ).count()

        return {
            'total_books': total_books,
            'books_by_genre': list(books_by_genre),
            'top_authors': list(books_by_author),
            'recent_books_count': recent_books_count
        }

    def get_genre_distribution(self) -> Dict[str, int]:
        """Распределение книг по жанрам."""
        books_qs = self.repository.get_all()  # Предполагается, что возвращается QuerySet
        genre_counts = (books_qs.values('genre').annotate(count=Count('id')))
        return {item['genre'] or 'Unknown': item['count'] for item in genre_counts}

    def get_top_authors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Топ авторов по количеству книг."""
        books_qs = self.repository.get_all()  # Предполагается, что возвращается QuerySet
        author_counts = (books_qs.values('author').annotate(count=Count('id')).order_by('-count')[:limit])
        return [{'author': item['author'], 'book_count': item['count']} for item in author_counts]

    def get_recently_added_count(self, days: int = 30) -> int:
        """Количество книг, добавленных за последние N дней."""
        threshold_date = datetime.now() - timedelta(days=days)
        books_qs = self.repository.get_all()  # Предполагается, что возвращается QuerySet
        if hasattr(books_qs.model, 'created_at'):
            return books_qs.filter(created_at__gte=threshold_date).count()
        return 0  # Если поле created_at отсутствует, возвращаем 0
