from rest_framework import serializers
from .models import Book
from .services.external_apis import BookEnrichmentService
from typing import Dict, Any


class BookSerializer(serializers.ModelSerializer):
    """Основной сериализатор для модели Book"""

    class Meta:
        model = Book
        fields = ['id', 'title', 'author', 'isbn', 'description', 'published_date']

    def validate_isbn(self, value: str) -> str:
        """Валидация ISBN"""
        # Убираем все нецифровые символы кроме X
        cleaned_isbn = ''.join(char for char in value if char.isdigit() or char.upper() == 'X')

        if len(cleaned_isbn) not in [10, 13]:
            raise serializers.ValidationError("ISBN должен содержать 10 или 13 символов")

        return cleaned_isbn


class EnrichedBookSerializer(serializers.ModelSerializer):
    """Сериализатор с обогащенными данными"""

    enriched_data = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = ['id', 'title', 'author', 'isbn', 'description', 'published_date', 'enriched_data']

    def get_enriched_data(self, obj: Book) -> Dict[str, Any]:
        """Получение обогащенных данных"""
        enrichment_service = BookEnrichmentService()
        enriched = enrichment_service.enrich_book_data(obj.isbn)

        if enriched:
            return {
                'external_title': enriched.title,
                'external_author': enriched.author,
                'external_description': enriched.description,
                'page_count': enriched.page_count,
                'language': enriched.language,
                'categories': enriched.categories,
                'thumbnail': enriched.thumbnail,
                'preview_link': enriched.preview_link,
                'rating': enriched.rating,
                'reviews_count': enriched.reviews_count,
                'ny_times_review': enriched.ny_times_review,
                'data_source': enriched.source
            }

        return {}


class BookSearchSerializer(serializers.Serializer):
    """Сериализатор для поиска книг"""

    query = serializers.CharField(max_length=255)
    limit = serializers.IntegerField(default=10, min_value=1, max_value=50)

    def search_books(self):
        """Поиск книг через внешние API"""
        query = self.validated_data['query']
        limit = self.validated_data['limit']

        enrichment_service = BookEnrichmentService()
        return enrichment_service.search_books(query, limit)


class BookCreateUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания и обновления книг"""

    auto_fill = serializers.BooleanField(default=False, write_only=True)

    class Meta:
        model = Book
        fields = ['title', 'author', 'isbn', 'description', 'published_date', 'auto_fill']

    def validate_isbn(self, value: str) -> str:
        """Валидация ISBN"""
        # Убираем все нецифровые символы кроме X
        cleaned_isbn = ''.join(char for char in value if char.isdigit() or char.upper() == 'X')

        if len(cleaned_isbn) not in [10, 13]:
            raise serializers.ValidationError("ISBN должен содержать 10 или 13 символов")

        return cleaned_isbn

    def create(self, validated_data: Dict[str, Any]) -> Book:
        """Создание книги с возможностью автозаполнения"""
        auto_fill = validated_data.pop('auto_fill', False)

        if auto_fill:
            # Пытаемся получить данные из внешних API
            enrichment_service = BookEnrichmentService()
            enriched_data = enrichment_service.enrich_book_data(validated_data['isbn'])

            if enriched_data:
                # Заполняем пустые поля данными из внешних источников
                if not validated_data.get('title') and enriched_data.title:
                    validated_data['title'] = enriched_data.title

                if not validated_data.get('author') and enriched_data.author:
                    validated_data['author'] = enriched_data.author

                if not validated_data.get('description') and enriched_data.description:
                    validated_data['description'] = enriched_data.description

                if not validated_data.get('published_date') and enriched_data.published_date:
                    # Парсим дату из строки
                    try:
                        from datetime import datetime
                        # Пробуем разные форматы дат
                        for fmt in ['%Y-%m-%d', '%Y', '%Y-%m']:
                            try:
                                date_obj = datetime.strptime(enriched_data.published_date, fmt)
                                validated_data['published_date'] = date_obj.date()
                                break
                            except ValueError:
                                continue
                    except (ValueError, TypeError, AttributeError) as e:
                        pass

        return super().create(validated_data)

    def update(self, instance: Book, validated_data: Dict[str, Any]) -> Book:
        """Обновление книги с возможностью автозаполнения"""
        auto_fill = validated_data.pop('auto_fill', False)

        if auto_fill:
            # Пытаемся получить данные из внешних API
            enrichment_service = BookEnrichmentService()
            enriched_data = enrichment_service.enrich_book_data(
                validated_data.get('isbn', instance.isbn)
            )

            if enriched_data:
                # Заполняем пустые поля данными из внешних источников
                if not validated_data.get('title') and not instance.title and enriched_data.title:
                    validated_data['title'] = enriched_data.title

                if not validated_data.get('author') and not instance.author and enriched_data.author:
                    validated_data['author'] = enriched_data.author

                if not validated_data.get('description') and not instance.description and enriched_data.description:
                    validated_data['description'] = enriched_data.description

                if not validated_data.get(
                        'published_date') and not instance.published_date and enriched_data.published_date:
                    # Парсим дату из строки
                    try:
                        from datetime import datetime
                        # Пробуем разные форматы дат
                        for fmt in ['%Y-%m-%d', '%Y', '%Y-%m']:
                            try:
                                date_obj = datetime.strptime(enriched_data.published_date, fmt)
                                validated_data['published_date'] = date_obj.date()
                                break
                            except ValueError:
                                continue
                    except (ValueError, TypeError, AttributeError) as e:
                        pass

        return super().update(instance, validated_data)
