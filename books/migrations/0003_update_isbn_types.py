from django.db import migrations, models


def convert_isbn_types(apps, schema_editor):
    """
    Конвертирует старые значения типов ISBN в новые (с подчеркивания на дефисы).
    """
    BookISBN = apps.get_model("books", "BookISBN")

    # Обновляем все записи ISBN_10 на ISBN-10
    BookISBN.objects.filter(type="ISBN_10").update(type="ISBN-10")

    # Обновляем все записи ISBN_13 на ISBN-13
    BookISBN.objects.filter(type="ISBN_13").update(type="ISBN-13")


class Migration(migrations.Migration):

    dependencies = [
        ("books", "0002_alter_book_description_alter_book_isbn_bookisbn"),
    ]

    operations = [
        # Сначала конвертируем данные
        migrations.RunPython(convert_isbn_types, migrations.RunPython.noop),
        # Затем обновляем определение модели
        migrations.AlterField(
            model_name="bookisbn",
            name="type",
            field=models.CharField(
                choices=[("ISBN-10", "ISBN-10"), ("ISBN-13", "ISBN-13")],
                default="ISBN-13",
                max_length=7,
            ),
        ),
        # Изменяем длину поля ISBN без валидатора на этом этапе
        migrations.AlterField(
            model_name="bookisbn",
            name="isbn",
            field=models.CharField(max_length=13, unique=True),
        ),
        # Добавляем verbose_name и verbose_name_plural в Meta
        migrations.AlterModelOptions(
            name="bookisbn",
            options={
                "verbose_name": "ISBN книги",
                "verbose_name_plural": "ISBN книг",
                "indexes": [models.Index(fields=["isbn"], name="books_isbn_index")],
                "unique_together": {("book", "isbn")},
            },
        ),
    ]
