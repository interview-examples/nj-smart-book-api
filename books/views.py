from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.request import Request
from django.db.models import Q, Count

from books.models import Book, Author
from books.serializers import BookSerializer, EnrichedBookSerializer, BookCreateUpdateSerializer
from books.services.book_service import BookService
from books.services.enrichment_service import EnrichmentService


class BookViewSet(viewsets.ModelViewSet):
    """Simple ViewSet for Book operations."""
    
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.service = BookService()

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
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

    def list(self, request: Request, *args, **kwargs) -> Response:
        """List books with search and filtering capabilities"""
        return super().list(request, *args, **kwargs)

    def retrieve(self, request: Request, *args, **kwargs) -> Response:
        """Get a book with enriched data from external sources"""
        try:
            book = self.service.get_book_by_id(int(kwargs.get('pk')))
            if not book:
                return Response({'error': 'Book not found'}, status=status.HTTP_404_NOT_FOUND)
            serializer = self.get_serializer(book)
            return Response(serializer.data)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request, *args, **kwargs):
        """Create a new book"""
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        """Update a book"""
        try:
            book = self.service.get_book_by_id(int(kwargs.get('pk')))
            if not book:
                return Response({'error': 'Book not found'}, status=status.HTTP_404_NOT_FOUND)
            serializer = self.get_serializer(book, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        """Delete a book"""
        try:
            success = self.service.delete_book(int(kwargs.get('pk')))
            if not success:
                return Response({'error': 'Book not found'}, status=status.HTTP_404_NOT_FOUND)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search books by query"""
        try:
            query = request.query_params.get('q', '')
            if not query:
                return Response([])
            
            books = self.service.search_books(query)
            page = self.paginate_queryset(books)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            
            serializer = self.get_serializer(books, many=True)
            return Response(serializer.data)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='isbn/(?P<isbn>[^/.]+)')
    def get_by_isbn(self, request, isbn=None):
        """Get book by ISBN with enriched data"""
        try:
            book = self.service.get_book_by_isbn(isbn)
            if not book:
                return Response({'error': 'Book not found'}, status=status.HTTP_404_NOT_FOUND)
            serializer = EnrichedBookSerializer(book)
            return Response(serializer.data)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EnrichmentViewSet(viewsets.ViewSet):
    """Simple ViewSet for book enrichment operations."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.service = EnrichmentService()

    @action(detail=False, methods=['get'])
    def enrich_by_isbn(self, request):
        """Enrich book data by ISBN"""
        try:
            isbn = request.query_params.get('isbn')
            if not isbn:
                return Response({'error': 'ISBN parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            enriched_data = self.service.enrich_book_by_isbn(isbn)
            if not enriched_data:
                return Response({'error': 'Failed to enrich book data'}, status=status.HTTP_404_NOT_FOUND)
            return Response({'message': 'Book enriched successfully'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def search_external(self, request):
        """Search for books in external APIs"""
        try:
            query = request.data.get('query')
            if not query:
                return Response({'error': 'Query parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            results = self.service.search_external(query)
            return Response(results)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StatsView(viewsets.ViewSet):
    """Simple ViewSet for book statistics."""

    @action(detail=False, methods=['get'])
    def get(self, request):
        """Get book statistics"""
        try:
            from django.db.models import Count
            
            # Get top authors
            top_authors = list(
                Author.objects.annotate(
                    book_count=Count('books')
                ).filter(
                    book_count__gt=0
                ).order_by('-book_count')[:5].values('name', 'book_count')
            )
            
            stats = {
                'total_books': Book.objects.count(),
                'total_authors': Book.objects.values('authors').distinct().count(),
                'top_authors': top_authors,
            }
            return Response(stats)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
