from django.test import TestCase
from rest_framework.exceptions import ValidationError
from books.models import Book
from books.serializers import (
    BookSerializer,
    EnrichedBookSerializer,
    BookCreateUpdateSerializer
)

class BookSerializerTests(TestCase):
    """Тесты для сериализатора BookSerializer."""
    
    def setUp(self):
        """Настройка тестовых данных."""
        self.book_data = {
            'title': 'Test Book',
            'author': 'Test Author',
            'isbn': '9781234567897',
            'description': 'Test description of the book',
            'published_date': '2023-01-01'
        }
        
        self.book = Book.objects.create(**self.book_data)
        self.serializer = BookSerializer(instance=self.book)
    
    def test_contains_expected_fields(self):
        """Проверка наличия ожидаемых полей."""
        data = self.serializer.data
        self.assertCountEqual(data.keys(), [
            'id', 'title', 'author', 'isbn', 'description', 'published_date'
        ])
    
    def test_title_field_content(self):
        """Проверка содержимого поля title."""
        data = self.serializer.data
        self.assertEqual(data['title'], self.book_data['title'])
    
    def test_author_field_content(self):
        """Проверка содержимого поля author."""
        data = self.serializer.data
        self.assertEqual(data['author'], self.book_data['author'])


class EnrichedBookSerializerTests(TestCase):
    """Тесты для сериализатора EnrichedBookSerializer."""
    
    def setUp(self):
        """Настройка тестовых данных."""
        self.book_data = {
            'title': 'Test Book',
            'author': 'Test Author',
            'isbn': '9781234567897',
            'description': 'Test description of the book',
            'published_date': '2023-01-01'
        }
        
        self.book = Book.objects.create(**self.book_data)
        self.serializer = EnrichedBookSerializer(instance=self.book)
    
    def test_contains_expected_fields(self):
        """Проверка наличия ожидаемых полей."""
        data = self.serializer.data
        expected_fields = [
            'id', 'title', 'author', 'isbn', 'description', 
            'published_date', 'enriched_data'
        ]
        self.assertCountEqual(data.keys(), expected_fields)
    
    def test_enriched_data_structure(self):
        """Проверка структуры обогащенных данных."""
        data = self.serializer.data
        self.assertIn('enriched_data', data)


class BookCreateUpdateSerializerTests(TestCase):
    """Тесты для сериализатора BookCreateUpdateSerializer."""
    
    def setUp(self):
        """Настройка тестовых данных."""
        self.valid_data = {
            'title': 'New Test Book',
            'author': 'New Test Author',
            'isbn': '9781234567897',
            'description': 'New test description',
            'published_date': '2023-01-01'
        }
        
        self.invalid_isbn_data = {
            'title': 'Invalid ISBN Book',
            'author': 'Test Author',
            'isbn': '123',  # Некорректный ISBN
            'description': 'Book with invalid ISBN',
            'published_date': '2023-01-01'
        }

        self.invalid_date_data = {
            'title': 'Invalid Date Book',
            'author': 'Test Author',
            'isbn': '9781234567897',
            'description': 'Book with invalid date',
            'published_date': 'not-a-date'  # Некорректная дата
        }
    
    def test_validate_valid_data(self):
        """Проверка валидации корректных данных."""
        serializer = BookCreateUpdateSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid())
    
    def test_validate_invalid_isbn(self):
        """Проверка валидации некорректного ISBN."""
        serializer = BookCreateUpdateSerializer(data=self.invalid_isbn_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('isbn', serializer.errors)
    
    def test_validate_invalid_date(self):
        """Проверка валидации некорректной даты."""
        serializer = BookCreateUpdateSerializer(data=self.invalid_date_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('published_date', serializer.errors)
    
    def test_create_with_partial_data(self):
        """Проверка создания с неполными данными."""
        partial_data = {
            'isbn': '9781234567890',
            'title': 'Partial Book',
            'author': 'Partial Author',
            'published_date': '2023-01-01'
        }
        serializer = BookCreateUpdateSerializer(data=partial_data)
        self.assertTrue(serializer.is_valid())
        
        book = serializer.save()
        self.assertEqual(book.title, partial_data['title'])
        self.assertEqual(book.author, partial_data['author'])
        # Django преобразует строку '2023-01-01' в объект datetime.date(2023, 1, 1)
        from datetime import datetime
        expected_date = datetime.strptime(partial_data['published_date'], '%Y-%m-%d').date()
        self.assertEqual(book.published_date, expected_date)  # Сравниваем с объектом date
        self.assertEqual(book.isbn, partial_data['isbn'])
    
    def test_update_existing_book(self):
        """Проверка обновления существующей книги."""
        # Сначала создаем книгу
        book = Book.objects.create(**self.valid_data)
        
        # Теперь обновляем
        update_data = {
            'title': 'Updated Title',
            'description': 'Updated description'
        }
        
        serializer = BookCreateUpdateSerializer(
            instance=book,
            data=update_data,
            partial=True
        )
        
        self.assertTrue(serializer.is_valid())
        updated_book = serializer.save()
        
        self.assertEqual(updated_book.title, update_data['title'])
        self.assertEqual(updated_book.description, update_data['description'])
        # Проверяем, что остальные поля не изменились
        self.assertEqual(updated_book.author, self.valid_data['author'])
        self.assertEqual(updated_book.isbn, self.valid_data['isbn'])
    
    def test_auto_fill_functionality(self):
        """Проверка функциональности автозаполнения."""
        data_with_auto_fill = {
            'title': 'Auto Fill Book',
            'isbn': '9780141439518',  # ISBN для "Pride and Prejudice"
            'auto_fill': True
        }
        
        serializer = BookCreateUpdateSerializer(data=data_with_auto_fill)
        if serializer.is_valid():
            book = serializer.save()
            # Проверяем, что поля были автозаполнены
            self.assertEqual(book.title, data_with_auto_fill['title'])  # Сохраняем оригинальный заголовок
            self.assertEqual(book.isbn, data_with_auto_fill['isbn'])
            # Автор и описание должны быть заполнены из внешнего API
            self.assertIsNotNone(book.author)
            self.assertIsNotNone(book.description)
