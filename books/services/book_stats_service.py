from typing import Dict, List, Any
from datetime import datetime, timedelta
from django.db.models import Count
from books.models import Book
from books.repositories.book_repository import BookRepository


class BookStatsService:
    """Service for retrieving book statistics."""

    def __init__(self, repository: BookRepository = None):
        self.repository = repository or BookRepository()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive book statistics.

        Returns:
            Dict[str, Any]: Dictionary containing various statistics
        """
        # Get books from repository
        books = self.repository.get_all()
        total_books = len(books)

        # Author statistics (top 10)
        top_authors = self.get_top_authors(10)

        # Format authors data for response
        authors_data = [
            {"author": item["author"], "count": item["book_count"]}
            for item in top_authors
        ]

        # Statistics by addition date (last month)
        recent_books_count = self.get_recently_added_count(30)

        # Calculate statistics by publication year
        books_by_year = self.get_publication_year_distribution(books)

        return {
            "total_books": total_books,
            "books_by_publication_year": books_by_year,
            "top_authors": authors_data,
            "recent_books_count": recent_books_count,
        }

    def get_publication_year_distribution(self, books=None) -> List[Dict[str, Any]]:
        """
        Get distribution of books by publication year.

        Args:
            books: Optional list of books. If None, gets all books from repository.

        Returns:
            List[Dict[str, Any]]: List of dictionaries with years and counts
        """
        if books is None:
            books = self.repository.get_all()

        publication_years = []

        for book in books:
            if book.published_date:
                # Extract the year from published_date if it exists
                try:
                    if isinstance(book.published_date, str):
                        year = book.published_date.split("-")[0]
                    else:
                        year = book.published_date.year
                    publication_years.append(str(year))
                except (AttributeError, IndexError):
                    continue

        # Count books per publication year
        year_counts = {}
        for year in publication_years:
            if year in year_counts:
                year_counts[year] += 1
            else:
                year_counts[year] = 1

        # Sort by year (descending) and convert to list of dicts
        return [
            {"year": k, "count": v}
            for k, v in sorted(
                year_counts.items(), key=lambda item: item[0], reverse=True
            )
        ]

    def get_top_authors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get top authors by number of books.

        Args:
            limit: Maximum number of authors to return

        Returns:
            List[Dict[str, Any]]: List of dictionaries with author names and book counts
        """
        # Get books from repository
        books = self.repository.get_all()
        authors_stats = []

        # Collect all author names
        for book in books:
            for author in book.authors.all():
                authors_stats.append(author.name)

        # Count occurrences
        author_counts = {}
        for author in authors_stats:
            if author in author_counts:
                author_counts[author] += 1
            else:
                author_counts[author] = 1

        # Sort by count (descending) and limit results
        sorted_authors = sorted(
            author_counts.items(), key=lambda x: x[1], reverse=True
        )[:limit]
        return [
            {"author": author, "book_count": count} for author, count in sorted_authors
        ]

    def get_recently_added_count(self, days: int = 30) -> int:
        """
        Get count of books added in the last N days.

        Args:
            days: Number of days to look back

        Returns:
            int: Count of recently added books
        """
        # Get threshold date
        threshold_date = datetime.now() - timedelta(days=days)

        # Use model directly to check if created_at field exists
        if not hasattr(Book, "created_at"):
            return 0

        # Get books from repository
        books = self.repository.get_all()

        # Count books added after threshold date
        return sum(
            1
            for book in books
            if hasattr(book, "created_at")
            and book.created_at
            and book.created_at >= threshold_date
        )
