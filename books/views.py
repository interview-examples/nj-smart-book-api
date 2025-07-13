from rest_framework import viewsets
from drf_spectacular.utils import extend_schema, extend_schema_view
from .models import Book
from .serializers import BookSerializer


@extend_schema_view(
    list=extend_schema(
        summary="List all books",
        description="Returns a paginated list of all books in the system.",
        responses={200: BookSerializer(many=True)},
    ),
    retrieve=extend_schema(
        summary="Retrieve book by ID",
        description="Returns detailed information about a book, including enriched fields.",
        responses={200: BookSerializer},
    ),
    create=extend_schema(
        summary="Create a new book",
        description="Adds a new book to the database. ISBN must be unique.",
        responses={201: BookSerializer},
    ),
    update=extend_schema(
        summary="Update an existing book",
        description="Replaces all fields of the book with new values.",
        responses={200: BookSerializer},
    ),
    partial_update=extend_schema(
        summary="Partially update a book",
        description="Updates only selected fields of a book.",
        responses={200: BookSerializer},
    ),
    destroy=extend_schema(
        summary="Delete a book",
        description="Removes the book from the database by ID.",
        responses={204: None},
    ),
)
class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer

