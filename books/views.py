from rest_framework import viewsets, status, generics
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
from .services.book_service import BookService
from .services.enrichment_service import EnrichmentService
from .services.book_stats_service import BookStatsService


class BookPagination(PageNumberPagination):
    """Кастомная пагинация для книг"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class BookViewSet(viewsets.ModelViewSet):
    """ViewSet для CRUD операций с книгами."""
    queryset = Book.objects.all().order_by('title', 'author', 'published_date')
    pagination_class = BookPagination
    service = BookService()

    def get_serializer_class(self) -> type:
        """Выбор сериализатора в зависимости от действия"""
        if self.action in ['create', 'update', 'partial_update']:
            return BookCreateUpdateSerializer
        elif self.action == 'retrieve':
            return EnrichedBookSerializer
        return BookSerializer

    def get_queryset(self):
        """
        Получает базовый QuerySet для книг в зависимости от действия.
        Для списка возвращает все книги, для поиска по ISBN - фильтрует по ISBN.
        """
        # Определяем базовое упорядочивание, которое будет применяться ко всем queryset
        ordering = ('title', 'author', 'published_date')
        
        action = getattr(self, 'action', None)
        if action == 'search_by_isbn':
            isbn = self.request.query_params.get('isbn', '')
            if isbn:
                book = self.service.get_book_by_isbn(isbn)
                if book:
                    return Book.objects.filter(id=book.id).order_by(*ordering)
                return Book.objects.none()
            return Book.objects.none()
        
        # Поиск по названию, автору или ISBN
        search = self.request.query_params.get('search', None)
        if search:
            return Book.objects.filter(
                Q(title__icontains=search) |
                Q(author__icontains=search) |
                Q(isbn__icontains=search)
            ).order_by(*ordering)

        # Фильтрация по автору
        author = self.request.query_params.get('author', None)
        if author:
            return Book.objects.filter(author__icontains=author).order_by(*ordering)

        # Фильтрация по году публикации
        year = self.request.query_params.get('year', None)
        if year and year.isdigit():
            return Book.objects.filter(published_date__year=year).order_by(*ordering)

        return super().get_queryset()

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
        book = self.service.get_book_by_id(int(kwargs.get('pk')))
        if not book:
            return Response({'error': 'Book not found'}, status=status.HTTP_404_NOT_FOUND)
        serializer = self.get_serializer(book)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        book = self.service.create_book(serializer.validated_data)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        book = self.service.update_book(int(kwargs.get('pk')), request.data)
        if not book:
            return Response({'error': 'Book not found'}, status=status.HTTP_404_NOT_FOUND)
        serializer = self.get_serializer(book)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        success = self.service.delete_book(int(kwargs.get('pk')))
        if not success:
            return Response({'error': 'Book not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='q',
                description='Поиск по названию, автору или ISBN',
                required=False,
                type=OpenApiTypes.STR,
            ),
        ],
        responses={200: BookSerializer(many=True)},
    )
    @action(detail=False, methods=['get'])
    def search(self, request):
        query = self.request.query_params.get('q', '')
        books = self.service.search_books(query)
        page = self.paginate_queryset(books)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(books, many=True)
        return Response(serializer.data)

class EnrichmentViewSet(viewsets.ViewSet):
    """ViewSet для обогащения данных о книгах из внешних источников."""
    
    service = EnrichmentService(BookService())
    
    def get_permissions(self):
        pass

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
    def enrich_by_isbn(self, request):
        isbn = request.GET.get('isbn', '')
        if not isbn:
            return Response({'error': 'ISBN parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
        enriched_data = self.service.enrich_book_by_isbn(isbn)
        if not enriched_data:
            return Response({'error': 'Failed to enrich book data'}, status=status.HTTP_404_NOT_FOUND)
        return Response(enriched_data)

    @extend_schema(
        request=BookSearchSerializer,
        responses={200: BookSearchSerializer},
    )
    @action(detail=False, methods=['post'])
    def search_external(self, request):
        query = request.data.get('query', '')
        if not query:
            return Response({'error': 'Query parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
        results = self.service.search_external(query)
        return Response(results)

class StatsView(generics.GenericAPIView):
    """View для получения статистики по книгам."""
    service = BookStatsService()

    def get(self, request, *args, **kwargs):
        stats = self.service.get_stats()
        return Response(stats)
