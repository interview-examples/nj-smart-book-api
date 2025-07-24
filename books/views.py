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
    """Custom pagination for books"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class BookViewSet(viewsets.ModelViewSet):
    """ViewSet for CRUD operations with books."""
    queryset = Book.objects.all().order_by('title', 'published_date')
    pagination_class = BookPagination
    service = BookService()

    def get_serializer_class(self) -> type:
        """Select serializer based on the action"""
        if self.action in ['create', 'update', 'partial_update']:
            return BookCreateUpdateSerializer
        elif self.action == 'retrieve':
            return EnrichedBookSerializer
        return BookSerializer

    def get_queryset(self):
        """Get the base QuerySet for books depending on the action."""
        ordering = ('title', 'published_date')
        queryset = Book.objects.all().order_by(*ordering)
        
        action = getattr(self, 'action', None)
        if action == 'search_by_isbn':
            isbn = self.request.query_params.get('isbn', '')
            if isbn:
                book = self.service.get_book_by_isbn(isbn)
                queryset = Book.objects.filter(id=book.id).order_by(*ordering) if book else Book.objects.none()
            else:
                queryset = Book.objects.none()
        else:
            # Apply filters based on query parameters
            search = self.request.query_params.get('search')
            author = self.request.query_params.get('author')
            year = self.request.query_params.get('year')
            
            if search:
                queryset = queryset.filter(
                    Q(title__icontains=search) |
                    Q(authors__name__icontains=search) |
                    Q(isbn__icontains=search)
                ).distinct()
            elif author:
                queryset = queryset.filter(authors__name__icontains=author).distinct()
            elif year and year.isdigit():
                queryset = queryset.filter(published_date__year=year)
        
        return queryset

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='search',
                description='Search by title, author or ISBN',
                required=False,
                type=OpenApiTypes.STR,
            ),
            OpenApiParameter(
                name='author',
                description='Filter by author',
                required=False,
                type=OpenApiTypes.STR,
            ),
            OpenApiParameter(
                name='year',
                description='Filter by publication year',
                required=False,
                type=OpenApiTypes.INT,
            ),
        ],
        responses={200: BookSerializer(many=True)},
        description="List books with search and filtering capabilities"
    )
    def list(self, request: Request, *args, **kwargs) -> Response:
        """List books with search and filtering capabilities"""
        return super().list(request, *args, **kwargs)

    @extend_schema(
        responses={200: EnrichedBookSerializer},
        description="Get a book with enriched data from external sources"
    )
    def retrieve(self, request: Request, *args, **kwargs) -> Response:
        """Get a book with enriched data from external sources"""
        book = self.service.get_book_by_id(int(kwargs.get('pk')))
        if not book:
            return Response({'error': 'Book not found'}, status=status.HTTP_404_NOT_FOUND)
        serializer = self.get_serializer(book)
        return Response(serializer.data)

    @extend_schema(
        request=BookCreateUpdateSerializer,
        responses={201: BookSerializer},
        description="Create a new book"
    )
    def create(self, request, *args, **kwargs):
        """Create a new book"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        book = self.service.create_book(serializer.validated_data)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        request=BookCreateUpdateSerializer,
        responses={200: BookSerializer},
        description="Update an existing book"
    )
    def update(self, request, *args, **kwargs):
        """Update an existing book"""
        book = self.service.update_book(int(kwargs.get('pk')), request.data)
        if not book:
            return Response({'error': 'Book not found'}, status=status.HTTP_404_NOT_FOUND)
        serializer = self.get_serializer(book)
        return Response(serializer.data)

    @extend_schema(
        responses={204: None},
        description="Delete a book"
    )
    def destroy(self, request, *args, **kwargs):
        """Delete a book"""
        success = self.service.delete_book(int(kwargs.get('pk')))
        if not success:
            return Response({'error': 'Book not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='q',
                description='Search query for title, author or ISBN',
                required=False,
                type=OpenApiTypes.STR,
            ),
        ],
        responses={200: BookSerializer(many=True)},
        description="Search books by title, author or ISBN"
    )
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search books by title, author or ISBN"""
        query = self.request.query_params.get('q', '')
        books = self.service.search_books(query)
        page = self.paginate_queryset(books)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(books, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='isbn/(?P<isbn>[^/.]+)')
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='isbn',
                description='ISBN-10 or ISBN-13 of the book (with or without hyphens)',
                required=True,
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
            ),
        ],
        responses={
            200: EnrichedBookSerializer,
            404: OpenApiTypes.OBJECT,
        },
        description="Get a book by its ISBN"
    )
    def get_by_isbn(self, request, isbn=None):
        """
        Get a book by its ISBN-10 or ISBN-13.
        Returns enriched book data with information from external sources.
        """
        book = self.service.get_book_by_isbn(isbn)
        if not book:
            return Response({'error': 'Book not found'}, status=status.HTTP_404_NOT_FOUND)
        serializer = EnrichedBookSerializer(book)
        return Response(serializer.data)


class EnrichmentViewSet(viewsets.ViewSet):
    """ViewSet for enriching book data from external sources."""
    
    service = EnrichmentService(BookService())
    
    def get_permissions(self):
        pass

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='isbn',
                description='ISBN of the book to enrich',
                required=True,
                type=OpenApiTypes.STR,
            ),
        ],
        responses={200: dict},
        description="Enrich book data using ISBN from external sources"
    )
    @action(detail=False, methods=['get'])
    def enrich_by_isbn(self, request):
        """Enrich book data using ISBN from external sources"""
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
        description="Search for books in external sources"
    )
    @action(detail=False, methods=['post'])
    def search_external(self, request):
        """Search for books in external sources"""
        query = request.data.get('query', '')
        if not query:
            return Response({'error': 'Query parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
        results = self.service.search_external(query)
        return Response(results)

class StatsView(generics.GenericAPIView):
    """View for getting book statistics."""
    service = BookStatsService()

    @extend_schema(
        responses={200: dict},
        description="Get statistics about books in the database"
    )
    def get(self, request, *args, **kwargs):
        """Get statistics about books in the database"""
        stats = self.service.get_stats()
        return Response(stats)
