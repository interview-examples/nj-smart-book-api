from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from books.models import Book, Author
from django.utils import timezone


class BookApiTests(APITestCase):
    """Tests for the book API endpoints."""

    def setUp(self):
        """Setup test data."""
        # Create test author
        self.author = Author.objects.create(name="Test Author")

        # Create test book
        self.book = Book.objects.create(
            title="Test Book",
            isbn="9780134494166",
            description="Test description",
            published_date="2023-01-01",
        )
        self.book.authors.add(self.author)

        # URLs for testing
        self.list_url = reverse("books-list")
        self.detail_url = reverse("books-detail", kwargs={"pk": self.book.pk})

    def test_create_book(self):
        """Test creating a new book."""
        initial_count = Book.objects.count()

        # Create author for the new book
        new_author_name = "New Test Author"
        new_author = Author.objects.create(name=new_author_name)

        # Book data with author name as string
        new_book_data = {
            "title": "New Test Book",
            "isbn": "9780201633610",
            "description": "New test description",
            "published_date": "2023-02-02",
            "authors": [new_author_name],  # Pass the author name as string
        }

        response = self.client.post(self.list_url, new_book_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Book.objects.count(), initial_count + 1)

        # Verify book fields
        response_data = response.json()
        self.assertEqual(response_data["title"], new_book_data["title"])
        self.assertEqual(response_data["isbn"], new_book_data["isbn"])
        self.assertEqual(response_data["description"], new_book_data["description"])

        # Verify author relationship
        created_book = Book.objects.get(isbn=new_book_data["isbn"])
        self.assertEqual(created_book.authors.first().name, new_author_name)

    def test_get_book_list(self):
        """Test retrieving a list of books."""
        # Clear all books before test to control the count
        Book.objects.all().delete()

        # Create exactly 2 books for testing
        author = Author.objects.create(name="List Test Author")
        book1 = Book.objects.create(
            title="List Test Book 1",
            isbn="9780306406157",  # Valid ISBN-13 with correct checksum
            published_date="2023-01-01",
        )
        book1.authors.add(author)

        book2 = Book.objects.create(
            title="List Test Book 2",
            isbn="9780134494166",  # Valid ISBN-13 with correct checksum
            published_date="2023-01-02",
        )
        book2.authors.add(author)

        url = reverse("books-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check book count considering possible pagination
        response_data = response.json()
        if "results" in response_data:
            # Paginated response
            self.assertEqual(len(response_data["results"]), 2)
            authors = response_data["results"][0]["authors"]
        else:
            # Direct list response
            self.assertEqual(len(response_data), 2)
            authors = response_data[0]["authors"]

        self.assertEqual(len(authors), 1)
        # Check that authors is a list of objects or a list of strings
        if isinstance(authors[0], dict):
            self.assertEqual(authors[0]["name"], "List Test Author")
        else:
            self.assertEqual(authors[0], "List Test Author")

    def test_get_book_detail(self):
        """Test retrieving a book's details."""
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()
        self.assertEqual(response_data["title"], self.book.title)
        self.assertEqual(response_data["isbn"], self.book.isbn)

        # Check enriched data is present
        self.assertIn("enriched_data", response_data)

    def test_update_book(self):
        """Test updating a book."""
        update_data = {
            "title": "Updated Test Book",
            "description": "Updated description",
            "authors": ["Test Author"],  # Use author name as string
        }

        response = self.client.patch(self.detail_url, update_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Refresh from database
        self.book.refresh_from_db()
        self.assertEqual(self.book.title, update_data["title"])
        self.assertEqual(self.book.description, update_data["description"])

    def test_delete_book(self):
        """Test deleting a book."""
        initial_count = Book.objects.count()
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Book.objects.count(), initial_count - 1)

    def test_get_book_statistics(self):
        """Test retrieving book statistics."""
        stats_url = reverse("book-stats")
        response = self.client.get(stats_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()
        self.assertIn("total_books", response_data)
        self.assertIn("top_authors", response_data)

    def test_search_book(self):
        """Test searching for books."""
        # Create additional books for testing search
        # Create authors first
        john_doe = Author.objects.create(name="John Doe")
        jane_smith = Author.objects.create(name="Jane Smith")

        # Create Python book with John Doe as author
        python_book = Book.objects.create(
            title="Python Programming",
            isbn="9781593279288",
            description="Learn Python programming",
            published_date="2023-01-01",
        )
        python_book.authors.add(john_doe)

        # Create Django book with Jane Smith as author
        django_book = Book.objects.create(
            title="Django Web Development",
            isbn="9781617294136",
            description="Getting started with Django",
            published_date="2023-01-01",
        )
        django_book.authors.add(jane_smith)

        # Search by title
        search_url = f"{self.list_url}?search=Python"
        response = self.client.get(search_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check if response is paginated
        response_data = response.json()
        if "results" in response_data:
            # Paginated response
            self.assertEqual(len(response_data["results"]), 1)
            self.assertEqual(response_data["results"][0]["title"], "Python Programming")
        else:
            # Direct list response
            self.assertEqual(len(response_data), 1)
            self.assertEqual(response_data[0]["title"], "Python Programming")

        # Search by author
        search_url = f"{self.list_url}?search=Smith"
        response = self.client.get(search_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check if response is paginated
        response_data = response.json()
        if "results" in response_data:
            # Paginated response
            self.assertEqual(len(response_data["results"]), 1)
            authors = response_data["results"][0]["authors"]
            self.assertTrue(any("Jane Smith" in str(author) for author in authors))
        else:
            # Direct list response
            self.assertEqual(len(response_data), 1)
            authors = response_data[0]["authors"]
            self.assertTrue(any("Jane Smith" in str(author) for author in authors))

        # Search by description
        search_url = f"{self.list_url}?search=Django"
        response = self.client.get(search_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check if response is paginated
        response_data = response.json()
        if "results" in response_data:
            # Paginated response
            self.assertEqual(len(response_data["results"]), 1)
            self.assertTrue("Django" in response_data["results"][0]["description"])
        else:
            # Direct list response
            self.assertEqual(len(response_data), 1)
            self.assertTrue("Django" in response_data[0]["description"])

    def test_filter_book(self):
        """Test filtering books."""
        # Test filter by author
        author = Author.objects.create(name="Unique Author")
        book2 = Book.objects.create(
            title="Test Book 2",
            isbn="9780306406157",  # Valid ISBN-13 with correct checksum
            published_date="2020-01-01",
        )
        book2.authors.add(author)

        # Filter should search by author name, not author field
        filter_url = reverse("books-list") + "?author=Unique"
        response = self.client.get(filter_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check that response contains only one book with the right author
        response_data = response.json()
        if "results" in response_data:
            # Paginated response
            self.assertEqual(len(response_data["results"]), 1)
            self.assertEqual(response_data["results"][0]["title"], "Test Book 2")
        else:
            # Direct list response
            self.assertEqual(len(response_data), 1)
            self.assertEqual(response_data[0]["title"], "Test Book 2")
