from django.db import models
from django.core.exceptions import ValidationError
import re
import logging

logger = logging.getLogger(__name__)

def validate_isbn(value):
    """
    Валидатор для ISBN.
    
    Проверяет формат ISBN и вычисляет контрольную сумму для ISBN-10 и ISBN-13.
    Формат ISBN-10: XXXXXXXXXX (где X - цифра или 'X' для последней позиции)
    Формат ISBN-13: XXXXXXXXXXXXX (где X - цифра)
    
    Args:
        value: Строка с ISBN для проверки
        
    Raises:
        ValidationError: Если ISBN не соответствует формату или контрольная сумма неверна
    """
    # Удаляем все не цифровые символы и символы 'X'
    clean_isbn = re.sub(r'[^0-9X]', '', value.upper())
    
    # Проверка на ISBN-10 или ISBN-13
    if len(clean_isbn) == 10:
        # Проверка формата ISBN-10
        if not re.match(r'^[0-9]{9}[0-9X]$', clean_isbn):
            raise ValidationError('ISBN-10 должен содержать 9 цифр и цифру или X в качестве контрольного символа.')
        
        # Проверка контрольной суммы ISBN-10
        # Алгоритм: (sum(d[i] * (10 - i) for i in range(9)) + d[9]) % 11 == 0, где d[9] = 10 если X
        try:
            sum_val = 0
            for i in range(9):
                sum_val += int(clean_isbn[i]) * (10 - i)
                
            if clean_isbn[9] == 'X':
                sum_val += 10
            else:
                sum_val += int(clean_isbn[9])
                
            if sum_val % 11 != 0:
                raise ValidationError(f'Неверная контрольная сумма ISBN-10: {value}')
        except (ValueError, IndexError) as e:
            logger.error(f"Ошибка проверки ISBN-10: {str(e)}")
            raise ValidationError(f'Ошибка при проверке ISBN-10: {value}')
            
    elif len(clean_isbn) == 13:
        # Проверка формата ISBN-13
        if not re.match(r'^[0-9]{13}$', clean_isbn):
            raise ValidationError('ISBN-13 должен содержать 13 цифр.')
        
        # Проверка контрольной суммы ISBN-13
        # Алгоритм: sum(d[i] * (1 if i % 2 == 0 else 3) for i in range(12)) + d[12] должно делиться на 10
        try:
            sum_val = 0
            for i in range(12):
                weight = 1 if i % 2 == 0 else 3
                sum_val += int(clean_isbn[i]) * weight
                
            check_digit = (10 - (sum_val % 10)) % 10  # Последнее % 10 нужно для случая, когда sum_val % 10 == 0
            
            if int(clean_isbn[12]) != check_digit:
                raise ValidationError(f'Неверная контрольная сумма ISBN-13: {value}')
        except (ValueError, IndexError) as e:
            logger.error(f"Ошибка проверки ISBN-13: {str(e)}")
            raise ValidationError(f'Ошибка при проверке ISBN-13: {value}')
    else:
        raise ValidationError('ISBN должен содержать 10 или 13 символов.')

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
        self.full_clean()
        super().save(*args, **kwargs)

class BookISBN(models.Model):
    book = models.ForeignKey('Book', on_delete=models.CASCADE, related_name='isbns')
    isbn = models.CharField(
        max_length=13,
        unique=True,
        validators=[validate_isbn]
    )
    type = models.CharField(
        max_length=10,
        choices=[('ISBN-10', 'ISBN-10'), ('ISBN-13', 'ISBN-13')],
        default='ISBN-13'
    )

    class Meta:
        unique_together = ('book', 'isbn')
        indexes = [models.Index(fields=['isbn'], name='books_isbn_index')]
        verbose_name = "Book`s ISBN"
        verbose_name_plural = "Books` ISBN"

    def __str__(self):
        return f"{self.isbn} ({self.type})"

    def save(self, *args, **kwargs) -> None:
        """Переопределяем метод save для запуска валидации перед сохранением."""
        self.full_clean()
        super().save(*args, **kwargs)
