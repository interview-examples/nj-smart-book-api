# Generated by Django 5.2.4 on 2025-07-14 19:12

import books.models
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("books", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="book",
            name="description",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AlterField(
            model_name="book",
            name="isbn",
            field=models.CharField(
                max_length=13, unique=True, validators=[books.models.validate_isbn]
            ),
        ),
        migrations.CreateModel(
            name="BookISBN",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("isbn", models.CharField(max_length=17, unique=True)),
                (
                    "type",
                    models.CharField(
                        choices=[("ISBN_10", "ISBN-10"), ("ISBN_13", "ISBN-13")],
                        default="ISBN_13",
                        max_length=10,
                    ),
                ),
                (
                    "book",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="isbns",
                        to="books.book",
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(fields=["isbn"], name="books_booki_isbn_03d832_idx")
                ],
                "unique_together": {("book", "isbn")},
            },
        ),
    ]
