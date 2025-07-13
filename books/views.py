from rest_framework import viewsets, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.request import Request
from django.db.models import Q
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from .models import Book
from .serializers import (
    BookSerializer,
    EnrichedBookSerializer,
    BookSearchSerializer,
    BookCreateUpdateSerializer
)
from .services.external_apis import BookEnrichmentService
from typing import List, Dict, Any, Type


class BookPagination(PageNumberPagination):
    """Кастомная пагинация для книг"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class BookViewSet(viewsets.ModelViewSet):
    """ViewSet для работы с книгами"""

    queryset = Book.objects.all()
    pagination_class = BookPagination

    def get_serializer_class(self) -> Type[serializers.ModelSerializer]:
        """Выбор сериализатора в зависимости от действия"""
        if self.action in ['create', 'update', 'partial_update']:
            return BookCreateUpdateSerializer
        elif self.action == 'retrieve':
            return EnrichedBookSerializer
        return BookSerializer

    def get_queryset(self) -> List[Book]:
        """Фильтрация и поиск"""
        queryset = Book.objects.all()

        # Поиск по названию, автору или ISBN
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(author__icontains=search) |
                Q(isbn__icontains=search)
            )

        # Фильтрация по автору
        author = self.request.query_params.get('author', None)
        if author:
            queryset = queryset.filter(author__icontains=author)

        # Фильтрация по году публикации
        year = self.request.query_params.get('year', None)
        if year:
            queryset = queryset.filter(published_date__year=year)

        return queryset.order_by('-id')

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='search',
                description='Поиск по названию, автору или ISBN',
                required=False,
                type=OpenApiTypes.STR,
            ),
            OpenApiParameter(
                name='author',
                description='Фильтрация по автору',
                required=False,
                type=OpenApiTypes.STR,
            ),
            OpenApiParameter(
                name='year',
                description='Фильтрация по году публикации',
                required=False,
                type=OpenApiTypes.INT,
            ),
        ],
        responses={200: BookSerializer(many=True)},
    )
    def list(self, request: Request, *args, **kwargs) -> Response:
        """Список книг с возможностью поиска и фильтрации"""
        return super().list(request, *args, **kwargs)

    @extend_schema(
        responses={200: EnrichedBookSerializer},
    )
    def retrieve(self, request: Request, *args, **kwargs) -> Response:
        """Получение книги с обогащенными данными"""
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        request=BookSearchSerializer,
        responses={200: BookSearchSerializer},
    )
    @action(detail=False, methods=['post'])
    def search_external(self, request: Request) -> Response:
        """Поиск книг во внешних API"""
        serializer = BookSearchSerializer(data=request.data)
        if serializer.is_valid():
            results = serializer.search_books()

            # Преобразуем результаты в удобный формат
            response_data = []
            for book_data in results:
                response_data.append({
                    'isbn': book_data.isbn,
                    'title': book_data.title,
                    'author': book_data.author,
                    'description': book_data.description,
                    'published_date': book_data.published_date,
                    'page_count': book_data.page_count,
                    'language': book_data.language,
                    'categories': book_data.categories,
                    'thumbnail': book_data.thumbnail,
                    'preview_link': book_data.preview_link,
                    'rating': book_data.rating,
                    'reviews_count': book_data.reviews_count,
                    'source': book_data.source
                })

            return Response({
                'query': serializer.validated_data['query'],
                'results': response_data,
                'count': len(response_data)
            })

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='isbn',
                description='ISBN книги для обогащения',
                required=True,
                type=OpenApiTypes.STR,
            ),
        ],
        responses={200: dict},
    )
    @action(detail=False, methods=['get'])
    def enrich_by_isbn(self, request: Request) -> Response:
        """Получение обогащенных данных по ISBN"""
        isbn = request.query_params.get('isbn')

        if not isbn:
            return Response(
                {'error': 'ISBN parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        enrichment_service = BookEnrichmentService()
        enriched_data = enrichment_service.enrich_book_data(isbn)

        if enriched_data:
            return Response({
                'isbn': enriched_data.isbn,
                'title': enriched_data.title,
                'author': enriched_data.author,
                'description': enriched_data.description,
                'published_date': enriched_data.published_date,
                'page_count': enriched_data.page_count,
                'language': enriched_data.language,
                'categories': enriched_data.categories,
                'thumbnail': enriched_data.thumbnail,
                'preview_link': enriched_data.preview_link,
                'rating': enriched_data.rating,
                'reviews_count': enriched_data.reviews_count,
                'ny_times_review': enriched_data.ny_times_review,
                'source': enriched_data.source
            })

        return Response(
            {'error': 'Book not found in external APIs'},
            status=status.HTTP_404_NOT_FOUND
        )

    @extend_schema(
        responses={200: dict},
    )
    @action(detail=False, methods=['get'])
    def stats(self, request: Request) -> Response:
        """Статистика по книгам"""
        total_books = Book.objects.count()

        # Группировка по годам
        from django.db.models import Count
        books_by_year = Book.objects.values('published_date__year').annotate(
            count=Count('id')
        ).order_by('published_date__year')

        # Топ авторов
        top_authors = Book.objects.values('author').annotate(
            count=Count('id')
        ).order_by('-count')[:10]

        return Response({
            'total_books': total_books,
            'books_by_year': list(books_by_year),
            'top_authors': list(top_authors)
        })
