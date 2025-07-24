"""
Data models for service layer.
Contains data transfer objects (DTOs) used to transfer data between services.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import date


@dataclass
class IndustryIdentifier:
    """
    Represents a book identifier like ISBN-10 or ISBN-13.
    """

    type: str
    identifier: str


@dataclass
class BookEnrichmentData:
    """
    Data transfer object (DTO) for enriched book data.
    Aggregates data from multiple external sources.
    """

    isbn: str
    title: Optional[str] = None
    authors: List[str] = field(default_factory=list)
    subtitle: Optional[str] = None
    description: Optional[str] = None
    published_date: Optional[str] = None
    publisher: Optional[str] = None
    page_count: Optional[int] = None
    language: Optional[str] = None
    categories: List[str] = field(default_factory=list)
    thumbnail: Optional[str] = None
    preview_link: Optional[str] = None
    rating: Optional[float] = None
    reviews_count: Optional[int] = None
    ny_times_review: Optional[str] = None
    source: Optional[str] = None
    industry_identifiers: List[IndustryIdentifier] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BookEnrichmentData":
        """
        Create a BookEnrichmentData instance from a dictionary.

        Args:
            data: Dictionary containing book data

        Returns:
            BookEnrichmentData: A new instance
        """
        identifiers = []
        raw_identifiers = data.get("industryIdentifiers") or data.get(
            "industry_identifiers", []
        )

        if isinstance(raw_identifiers, list):
            for identifier in raw_identifiers:
                if (
                    isinstance(identifier, dict)
                    and "type" in identifier
                    and "identifier" in identifier
                ):
                    identifiers.append(
                        IndustryIdentifier(
                            type=identifier["type"], identifier=identifier["identifier"]
                        )
                    )

        # Handle categories which might be a list or a string
        categories = data.get("categories", [])
        if isinstance(categories, str):
            categories = [categories]
        elif not isinstance(categories, list):
            categories = []

        # Create the instance with all available data
        return cls(
            isbn=data.get("isbn", ""),
            title=data.get("title"),
            authors=data.get("authors", []),
            subtitle=data.get("subtitle"),
            description=data.get("description"),
            published_date=data.get("published_date"),
            publisher=data.get("publisher"),
            page_count=data.get("page_count"),
            language=data.get("language"),
            categories=categories,
            thumbnail=data.get("thumbnail"),
            preview_link=data.get("preview_link"),
            rating=data.get("rating"),
            reviews_count=data.get("reviews_count"),
            ny_times_review=data.get("ny_times_review"),
            source=data.get("source"),
            industry_identifiers=identifiers,
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the BookEnrichmentData instance to a dictionary.

        Returns:
            Dict[str, Any]: Dictionary representation of the data
        """
        return {
            "isbn": self.isbn,
            "title": self.title,
            "authors": self.authors,
            "description": self.description,
            "published_date": self.published_date,
            "page_count": self.page_count,
            "language": self.language,
            "categories": self.categories,
            "thumbnail": self.thumbnail,
            "preview_link": self.preview_link,
            "rating": self.rating,
            "reviews_count": self.reviews_count,
            "ny_times_review": self.ny_times_review,
            "source": self.source,
            "industry_identifiers": [
                {"type": i.type, "identifier": i.identifier}
                for i in self.industry_identifiers
            ],
        }

    def get_isbn_by_type(self, isbn_type: str) -> Optional[str]:
        """
        Get ISBN by type (ISBN-10 or ISBN-13).

        Args:
            isbn_type: Type of ISBN to retrieve ('ISBN-10' or 'ISBN-13')

        Returns:
            Optional[str]: ISBN if found, None otherwise
        """
        for identifier in self.industry_identifiers:
            if identifier.type == isbn_type:
                return identifier.identifier
        return None

    def merge(self, other: "BookEnrichmentData") -> "BookEnrichmentData":
        """
        Merge data from another BookEnrichmentData instance.
        Preserves this instance's data if both have the same field populated.

        Args:
            other: Another BookEnrichmentData instance to merge with

        Returns:
            BookEnrichmentData: A new merged instance
        """
        result = BookEnrichmentData(
            isbn=self.isbn or other.isbn,
            title=self.title or other.title,
            authors=list(set(self.authors + other.authors)),
            description=self.description or other.description,
            published_date=self.published_date or other.published_date,
            page_count=self.page_count or other.page_count,
            language=self.language or other.language,
            thumbnail=self.thumbnail or other.thumbnail,
            preview_link=self.preview_link or other.preview_link,
            rating=self.rating or other.rating,
            reviews_count=self.reviews_count or other.reviews_count,
            ny_times_review=self.ny_times_review or other.ny_times_review,
            source=(
                f"{self.source},{other.source}"
                if self.source and other.source
                else (self.source or other.source)
            ),
        )

        # Merge categories without duplicates
        result.categories = list(set(self.categories + other.categories))

        # Merge industry identifiers without duplicates
        existing_identifiers = {
            (i.type, i.identifier) for i in self.industry_identifiers
        }
        result.industry_identifiers = self.industry_identifiers.copy()

        for i in other.industry_identifiers:
            if (i.type, i.identifier) not in existing_identifiers:
                result.industry_identifiers.append(i)

        return result
