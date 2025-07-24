from django.db import models
from django.core.exceptions import ValidationError
import re
import logging

logger = logging.getLogger(__name__)


def validate_isbn(value):
    """
    ISBN validator.

    Validates ISBN format and calculates checksum for ISBN-10 and ISBN-13.
    ISBN-10 format: XXXXXXXXXX (where X is a digit or 'X' for the last position)
    ISBN-13 format: XXXXXXXXXXXXX (where X is a digit)

    Args:
        value: ISBN string to validate

    Raises:
        ValidationError: If ISBN format is invalid or checksum is incorrect
    """
    # Remove all non-digit characters and 'X'
    clean_isbn = re.sub(r"[^0-9X]", "", value.upper())

    # Check for ISBN-10 or ISBN-13
    if len(clean_isbn) == 10:
        # Validate ISBN-10 format
        if not re.match(r"^[0-9]{9}[0-9X]$", clean_isbn):
            raise ValidationError(
                "ISBN-10 must contain 9 digits and a digit or X as the check character."
            )

        # Validate ISBN-10 checksum
        # Algorithm: (sum(d[i] * (10 - i) for i in range(9)) + d[9]) % 11 == 0, where d[9] = 10 if X
        try:
            sum_val = 0
            for i in range(9):
                sum_val += int(clean_isbn[i]) * (10 - i)

            if clean_isbn[9] == "X":
                sum_val += 10
            else:
                sum_val += int(clean_isbn[9])

            if sum_val % 11 != 0:
                raise ValidationError(f"Invalid ISBN-10 checksum: {value}")
        except (ValueError, IndexError) as e:
            logger.error(f"ISBN-10 validation error: {str(e)}")
            raise ValidationError(f"Error validating ISBN-10: {value}")

    elif len(clean_isbn) == 13:
        # Validate ISBN-13 format
        if not re.match(r"^[0-9]{13}$", clean_isbn):
            raise ValidationError("ISBN-13 must contain 13 digits.")

        # Validate ISBN-13 checksum
        # Algorithm: sum(d[i] * (1 if i % 2 == 0 else 3) for i in range(12)) + d[12] must be divisible by 10
        try:
            sum_val = 0
            for i in range(12):
                weight = 1 if i % 2 == 0 else 3
                sum_val += int(clean_isbn[i]) * weight

            check_digit = (
                10 - (sum_val % 10)
            ) % 10  # Last % 10 is needed for cases when sum_val % 10 == 0

            if int(clean_isbn[12]) != check_digit:
                raise ValidationError(f"Invalid ISBN-13 checksum: {value}")
        except (ValueError, IndexError) as e:
            logger.error(f"ISBN-13 validation error: {str(e)}")
            raise ValidationError(f"Error validating ISBN-13: {value}")
    else:
        raise ValidationError("ISBN must contain 10 or 13 characters.")


class Author(models.Model):
    """
    Author model representing book authors.
    """

    name = models.CharField(max_length=255, unique=True)

    def __str__(self) -> str:
        return self.name

    class Meta:
        ordering = ["name"]


class Book(models.Model):
    """
    Book model representing the main book entity with core attributes.
    """

    title = models.CharField(max_length=255)
    isbn = models.CharField(max_length=21, unique=True, validators=[validate_isbn])
    description = models.TextField(blank=True, default="")
    published_date = models.DateField()
    authors = models.ManyToManyField("Author", related_name="books")

    def __str__(self):
        # Avoid recursion by not accessing related objects at all
        return f"{self.title} (ID: {self.id})"

    def save(self, *args, **kwargs) -> None:
        """Override save method to run validation before saving."""
        self.full_clean()
        super().save(*args, **kwargs)


class BookISBN(models.Model):
    """
    BookISBN model for storing multiple ISBN formats for a single book.
    """

    book = models.ForeignKey("Book", on_delete=models.CASCADE, related_name="isbns")
    isbn = models.CharField(max_length=21, unique=True, validators=[validate_isbn])
    type = models.CharField(
        max_length=10,
        choices=[("ISBN-10", "ISBN-10"), ("ISBN-13", "ISBN-13")],
        default="ISBN-13",
    )

    class Meta:
        unique_together = ("book", "isbn")
        indexes = [models.Index(fields=["isbn"], name="books_isbn_index")]
        verbose_name = "Book's ISBN"
        verbose_name_plural = "Books' ISBNs"

    def __str__(self):
        return f"{self.isbn} ({self.type})"

    def save(self, *args, **kwargs) -> None:
        """Normalize ISBN before validation and saving."""
        # Remove any non-digit characters before saving (except 'X' for ISBN-10)
        if self.isbn:
            self.isbn = re.sub(r"[^0-9X]", "", self.isbn.upper())
        self.full_clean()
        super().save(*args, **kwargs)
