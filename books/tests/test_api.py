from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from books.models import Book

class BookApiTests(APITestCase):
    """Тесты для API эндпоинтов книг."""
    
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
        self.list_url = reverse('books-list')
        self.detail_url = reverse('books-detail', kwargs={'pk': self.book.pk})
    
    def test_create_book(self):
        """Тест создания книги."""
        initial_count = Book.objects.count()
        new_book_data = {
            'title': 'New Test Book',
            'author': 'New Test Author',
            'isbn': '9780987654321',
            'description': 'New test description',
            'published_date': '2023-05-05'
        }
        response = self.client.post(self.list_url, new_book_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Book.objects.count(), initial_count + 1)
        self.assertEqual(response.data['title'], new_book_data['title'])
        self.assertEqual(response.data['author'], new_book_data['author'])
        self.assertEqual(response.data['isbn'], new_book_data['isbn'])
        self.assertEqual(response.data['description'], new_book_data['description'])
    
    def test_get_book_list(self):
        """Тест получения списка книг."""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_get_book_detail(self):
        """Тест получения детальной информации о книге."""
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], self.book_data['title'])
        self.assertEqual(response.data['author'], self.book_data['author'])
        self.assertEqual(response.data['isbn'], self.book_data['isbn'])
    
    def test_update_book(self):
        """Тест обновления информации о книге."""
        update_data = {
            'title': 'Updated Title',
            'description': 'Updated description'
        }
        
        response = self.client.patch(self.detail_url, update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], update_data['title'])
        self.assertEqual(response.data['description'], update_data['description'])
        # Проверяем, что остальные поля не изменились
        self.assertEqual(response.data['author'], self.book_data['author'])
        self.assertEqual(response.data['isbn'], self.book_data['isbn'])
        
        # Проверяем полное обновление
        put_data = {
            'title': 'Completely New Title',
            'author': 'New Author',
            'isbn': '9781122334455',
            'description': 'Brand new description',
            'published_date': '2024-01-01'
        }
        
        response = self.client.put(self.detail_url, put_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for key, value in put_data.items():
            self.assertEqual(response.data[key], value)
    
    def test_delete_book(self):
        """Тест удаления книги."""
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Book.objects.count(), 0)
    
    def test_search_book(self):
        """Тест поиска книг."""
        # Создаем дополнительные книги для тестирования поиска
        Book.objects.create(
            title='Python Programming',
            author='John Doe',
            isbn='9781234567890',
            description='Learn Python programming',
            published_date='2023-01-01'  # Добавляем обязательное поле
        )
        
        Book.objects.create(
            title='Django for Beginners',
            author='Jane Smith',
            isbn='9789876543210',
            description='Getting started with Django',
            published_date='2023-01-01'  # Добавляем обязательное поле
        )
        
        # Поиск по заголовку
        search_url = f"{self.list_url}?search=Python"
        response = self.client.get(search_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['title'], 'Python Programming')
        
        # Поиск по автору
        search_url = f"{self.list_url}?search=Smith"
        response = self.client.get(search_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['author'], 'Jane Smith')
        
        # Поиск по описанию
        search_url = f"{self.list_url}?search=Django"
        response = self.client.get(search_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertTrue('Django' in response.data['results'][0]['description'])
    
    def test_filter_book(self):
        """Тест фильтрации книг."""
        # Создаем дополнительные книги для тестирования фильтрации
        Book.objects.create(
            title='Python Programming',
            author='John Doe',
            isbn='9781234567890',
            published_date='2022-05-05',
            description='Learn Python programming'
        )
        
        Book.objects.create(
            title='Django for Beginners',
            author='Jane Smith',
            isbn='9789876543210',
            published_date='2021-10-10',
            description='Getting started with Django'
        )
        
        # Фильтр по автору
        filter_url = f"{self.list_url}?author=Jane Smith"
        response = self.client.get(filter_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['author'], 'Jane Smith')
        
        # Фильтр по году публикации
        filter_url = f"{self.list_url}?year=2021"
        response = self.client.get(filter_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertTrue('2021' in response.data['results'][0]['published_date'])
