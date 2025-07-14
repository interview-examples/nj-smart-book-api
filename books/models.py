from django.db import models
from django.core.exceptions import ValidationError
import re

def validate_isbn(value):
    """Валидатор для ISBN."""
    # Удаляем все не цифровые символы
    isbn = re.sub(r'[^0-9X]', '', value)
    
    # Проверка на ISBN-10 или ISBN-13
    if len(isbn) != 10 and len(isbn) != 13:
        raise ValidationError('ISBN должен содержать 10 или 13 символов.')
    
    # Дополнительные проверки можно добавить здесь
    # Например, проверка контрольной суммы для ISBN-10 и ISBN-13

class Book(models.Model):
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    isbn = models.CharField(max_length=13, unique=True, validators=[validate_isbn])
    description = models.TextField(blank=True, default='')
    published_date = models.DateField()

    def __str__(self) -> str:
        return f"{self.title} - {self.author}"
    
    def save(self, *args, **kwargs) -> None:
        """Переопределяем метод save для запуска валидации перед сохранением."""
        self.full_clean()  # Запускаем валидаторы
        super().save(*args, **kwargs)
