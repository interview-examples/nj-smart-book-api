import uuid
from django.test import TestCase
from django.core.exceptions import ValidationError
from books.models import Book, BookISBN

class BookModelTests(TestCase):
    """Тесты для модели Book."""

    def setUp(self):
        """Настройка тестовых данных."""
        self.book_data = {
            'title': 'Test Book',
            'author': 'Test Author',
            'isbn': '9781234567897',
            'description': 'Test description of the book',
            'published_date': '2023-01-01'
        }

    def test_create_book(self):
        """Тест создания книги с валидными данными."""
        book = Book.objects.create(**self.book_data)
        self.assertEqual(book.title, self.book_data['title'])
        self.assertEqual(book.author, self.book_data['author'])
        self.assertEqual(book.isbn, self.book_data['isbn'])
        self.assertEqual(book.description, self.book_data['description'])
        self.assertEqual(str(book.published_date), self.book_data['published_date'])
        self.assertIsNotNone(book.id)

    def test_string_representation(self):
        """Тест строкового представления модели."""
        book = Book.objects.create(**self.book_data)
        expected_string = f"{self.book_data['title']} - {self.book_data['author']}"
        self.assertEqual(str(book), expected_string)

    def test_isbn_validation(self):
        """Тест валидации ISBN."""
        # Некорректный ISBN (неверная длина)
        invalid_data = self.book_data.copy()
        invalid_data['isbn'] = '123456'

        book = Book(**invalid_data)
        with self.assertRaises(ValidationError):
            book.full_clean()

        # Корректный ISBN-10
        valid_data = self.book_data.copy()
        valid_data['isbn'] = '1234567890'

        book = Book(**valid_data)
        try:
            book.full_clean()
        except ValidationError:
            self.fail("Валидация ISBN-10 некорректно выдает ошибку")

        # Корректный ISBN-13
        valid_data = self.book_data.copy()
        valid_data['isbn'] = '9781234567897'

        book = Book(**valid_data)
        try:
            book.full_clean()
        except ValidationError:
            self.fail("Валидация ISBN-13 некорректно выдает ошибку")

    def test_book_with_minimal_fields(self):
        """Тест создания книги с минимальным набором полей."""
        minimal_data = {
            'title': 'Minimal Book',
            'author': 'Minimal Author',
            'isbn': '9781234567890',  # ISBN обязателен согласно валидатору
            'published_date': '2023-01-01'  # Добавляем обязательное поле
        }

        book = Book.objects.create(**minimal_data)
        self.assertEqual(book.title, minimal_data['title'])
        self.assertEqual(book.author, minimal_data['author'])
        self.assertEqual(book.isbn, minimal_data['isbn'])
        from datetime import datetime
        expected_date = datetime.strptime(minimal_data['published_date'], '%Y-%m-%d').date()
        self.assertEqual(book.published_date, expected_date)
        self.assertEqual(book.description, '')  # Описание может быть пустым
        self.assertIsNotNone(book.id)

    def test_book_validation_fails_without_isbn(self):
        """Тест проверяет, что валидация не пропускает книгу без ISBN."""
        minimal_data = {
            'title': 'Book Without ISBN',
            'author': 'Test Author',
            'published_date': '2023-01-01'
        }

        # Создаем объект, но НЕ сохраняем в БД
        book = Book(**minimal_data)

        # Явно запускаем валидацию - должно выбрасывать исключение
        with self.assertRaises(ValidationError):
            book.full_clean()

    def test_book_validation_fails_with_invalid_isbn(self):
        """Тест проверяет, что валидация не пропускает книгу с некорректным ISBN."""
        invalid_data = {
            'title': 'Book With Invalid ISBN',
            'author': 'Test Author',
            'isbn': '12345',  # Слишком короткий ISBN
            'published_date': '2023-01-01'
        }

        # Создаем объект, но НЕ сохраняем в БД
        book = Book(**invalid_data)

        # Явно запускаем валидацию - должно выбрасывать исключение
        with self.assertRaises(ValidationError):
            book.full_clean()


class BookISBNModelTest(TestCase):
    def setUp(self):
        self.book = Book.objects.create(
            title="Test Book",
            author="Test Author",
            isbn="1234567890123",  # Основной ISBN (для обратной совместимости)
            published_date="2023-01-01"
        )

    def test_create_multiple_isbns(self):
        """Тестирование создания нескольких ISBN для одной книги."""
        isbn_13 = BookISBN.objects.create(book=self.book, isbn="1234567890123", type="ISBN-13")
        isbn_10 = BookISBN.objects.create(book=self.book, isbn="1234567890", type="ISBN-10")

        self.assertEqual(self.book.isbns.count(), 2)
        self.assertEqual(isbn_13.type, "ISBN-13")
        self.assertEqual(isbn_10.type, "ISBN-10")

    def test_unique_isbn(self):
        """Тестирование уникальности ISBN."""
        BookISBN.objects.create(book=self.book, isbn="1234567890123", type="ISBN-13")
        with self.assertRaises(Exception):  # Должно вызвать IntegrityError
            BookISBN.objects.create(book=self.book, isbn="1234567890123", type="ISBN-13")

    def test_str_method(self):
        """Тестирование метода __str__ для BookISBN."""
        isbn = BookISBN.objects.create(book=self.book, isbn="1234567890123", type="ISBN-13")
        self.assertEqual(str(isbn), "1234567890123 (ISBN-13)")
