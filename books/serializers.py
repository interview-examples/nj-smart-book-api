from rest_framework import serializers
from .models import Book, Author
from .services.enrichment.service import BookEnrichmentService
from typing import Dict, Any


class BookSerializer(serializers.ModelSerializer):
    """Main serializer for the Book model"""

    authors = serializers.StringRelatedField(many=True, read_only=True)

    class Meta:
        model = Book
        fields = ["id", "title", "authors", "isbn", "description", "published_date"]

    def validate_isbn(self, value: str) -> str:
        """
        Validate ISBN format

        Args:
            value: ISBN string to validate

        Returns:
            Cleaned ISBN string

        Raises:
            ValidationError: If ISBN format is invalid
        """
        # Remove all non-digit characters except X
        cleaned_isbn = "".join(
            char for char in value if char.isdigit() or char.upper() == "X"
        )

        if len(cleaned_isbn) not in [10, 13]:
            raise serializers.ValidationError("ISBN must contain 10 or 13 characters")

        return cleaned_isbn


class EnrichedBookSerializer(serializers.ModelSerializer):
    """Serializer with enriched data from external sources"""

    authors = serializers.StringRelatedField(many=True, read_only=True)
    enriched_data = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = [
            "id",
            "title",
            "authors",
            "isbn",
            "description",
            "published_date",
            "enriched_data",
        ]

    def get_enriched_data(self, obj: Book) -> Dict[str, Any]:
        """
        Get enriched data from external sources

        Args:
            obj: Book instance

        Returns:
            Dictionary with enriched book data
        """
        enrichment_service = BookEnrichmentService()
        enriched = enrichment_service.enrich_book_data(obj.isbn)

        if enriched:
            return {
                "external_title": enriched.title,
                "external_subtitle": enriched.subtitle,
                "external_authors": enriched.authors,
                "external_description": enriched.description,
                "publisher": enriched.publisher,
                "publication_year": (
                    enriched.published_date if enriched.published_date else None
                ),
                "page_count": enriched.page_count if enriched.page_count else 0,
                "language": enriched.language,
                "categories": enriched.categories,
                "thumbnail": enriched.thumbnail,
                "preview_link": enriched.preview_link,
                "rating": enriched.rating,
                "reviews_count": enriched.reviews_count,
                "ny_times_review": enriched.ny_times_review,
                "data_source": enriched.source,
            }

        return {}


class BookSearchSerializer(serializers.Serializer):
    """Serializer for searching books through external APIs"""

    query = serializers.CharField(max_length=255)
    limit = serializers.IntegerField(default=10, min_value=1, max_value=50)

    def search_books(self):
        """
        Search books through external APIs

        Returns:
            List of book search results
        """
        query = self.validated_data["query"]
        limit = self.validated_data["limit"]

        enrichment_service = BookEnrichmentService()
        return enrichment_service.search_books(query, limit)


class BookCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating books"""

    auto_fill = serializers.BooleanField(default=False, write_only=True)
    authors = serializers.ListField(
        child=serializers.CharField(max_length=255), write_only=True, required=True
    )
    published_date = serializers.CharField(required=False)

    class Meta:
        model = Book
        fields = [
            "title",
            "authors",
            "isbn",
            "description",
            "published_date",
            "auto_fill",
        ]

    def validate_isbn(self, value: str) -> str:
        """
        Validate ISBN format

        Args:
            value: ISBN string to validate

        Returns:
            Cleaned ISBN string

        Raises:
            ValidationError: If ISBN format is invalid
        """
        # Remove all non-digit characters except X
        cleaned_isbn = "".join(
            char for char in value if char.isdigit() or char.upper() == "X"
        )

        if len(cleaned_isbn) not in [10, 13]:
            raise serializers.ValidationError("ISBN must contain 10 or 13 characters")

        return cleaned_isbn

    def validate_published_date(self, value: str) -> str:
        """
        Validate and format published_date

        Args:
            value: Published date as string

        Returns:
            Formatted date string YYYY-MM-DD

        Raises:
            ValidationError: If date format is invalid
        """
        import re
        from datetime import datetime

        # If only year is provided (e.g. "2022")
        if re.match(r"^\d{4}$", value):
            return f"{value}-01-01"

        # If year and month are provided (e.g. "2022-05")
        if re.match(r"^\d{4}-\d{1,2}$", value):
            year, month = value.split("-")
            return f"{year}-{int(month):02d}-01"

        # If full date is provided, validate format
        try:
            date_obj = datetime.strptime(value, "%Y-%m-%d")
            return date_obj.strftime("%Y-%m-%d")
        except ValueError:
            try:
                # Try alternative formats
                for fmt in ("%d.%m.%Y", "%m/%d/%Y", "%Y/%m/%d"):
                    try:
                        date_obj = datetime.strptime(value, fmt)
                        return date_obj.strftime("%Y-%m-%d")
                    except ValueError:
                        continue
                raise serializers.ValidationError(
                    "Invalid date format. Use YYYY-MM-DD, YYYY, YYYY-MM, DD.MM.YYYY, or MM/DD/YYYY."
                )
            except Exception:
                raise serializers.ValidationError(
                    "Invalid date format. Use YYYY-MM-DD, YYYY, YYYY-MM, DD.MM.YYYY, or MM/DD/YYYY."
                )

    def create(self, validated_data: Dict[str, Any]) -> Book:
        """
        Create a new book instance

        Args:
            validated_data: Validated data for book creation

        Returns:
            Created Book instance
        """
        auto_fill = validated_data.pop("auto_fill", False)
        authors_data = validated_data.pop("authors", [])

        # First create or get authors
        authors = []
        for author_name in authors_data:
            author, _ = Author.objects.get_or_create(name=author_name)
            authors.append(author)

        if auto_fill:
            # Try to get data from external APIs
            enrichment_service = BookEnrichmentService()
            enriched_data = enrichment_service.enrich_book_data(validated_data["isbn"])

            if enriched_data:
                # Fill empty fields with data from external sources
                if not validated_data.get("title") and enriched_data.title:
                    validated_data["title"] = enriched_data.title

                if not validated_data.get("description") and enriched_data.description:
                    validated_data["description"] = enriched_data.description

                if (
                    not validated_data.get("published_date")
                    and enriched_data.published_date
                ):
                    # Parse date from string
                    try:
                        from datetime import datetime

                        # Try different date formats
                        for fmt in ["%Y-%m-%d", "%Y", "%Y-%m"]:
                            try:
                                date_obj = datetime.strptime(
                                    enriched_data.published_date, fmt
                                )
                                validated_data["published_date"] = date_obj.date()
                                break
                            except ValueError:
                                continue
                    except (ValueError, TypeError, AttributeError) as e:
                        pass

        validated_data["authors"] = authors
        return super().create(validated_data)

    def update(self, instance: Book, validated_data: Dict[str, Any]) -> Book:
        """
        Update a book with optional auto-filling from external sources

        Args:
            instance: Book instance to update
            validated_data: Validated data for updating the book

        Returns:
            Updated Book instance
        """
        auto_fill = validated_data.pop("auto_fill", False)
        authors_data = validated_data.pop("authors", [])

        # First create or get authors
        authors = []
        for author_name in authors_data:
            author, _ = Author.objects.get_or_create(name=author_name)
            authors.append(author)

        if auto_fill:
            # Try to get data from external APIs
            enrichment_service = BookEnrichmentService()
            enriched_data = enrichment_service.enrich_book_data(
                validated_data.get("isbn", instance.isbn)
            )

            if enriched_data:
                # Fill empty fields with data from external sources
                if (
                    not validated_data.get("title")
                    and not instance.title
                    and enriched_data.title
                ):
                    validated_data["title"] = enriched_data.title

                if (
                    not validated_data.get("description")
                    and not instance.description
                    and enriched_data.description
                ):
                    validated_data["description"] = enriched_data.description

                if (
                    not validated_data.get("published_date")
                    and not instance.published_date
                    and enriched_data.published_date
                ):
                    # Parse date from string
                    try:
                        from datetime import datetime

                        # Try different date formats
                        for fmt in ["%Y-%m-%d", "%Y", "%Y-%m"]:
                            try:
                                date_obj = datetime.strptime(
                                    enriched_data.published_date, fmt
                                )
                                validated_data["published_date"] = date_obj.date()
                                break
                            except ValueError:
                                continue
                    except (ValueError, TypeError, AttributeError) as e:
                        pass

        validated_data["authors"] = authors
        return super().update(instance, validated_data)
