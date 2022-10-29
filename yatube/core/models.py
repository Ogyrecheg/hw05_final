from django.db import models


class CreatedModel(models.Model):
    """Абстракная модель, добавляющая дату публикации."""

    created = models.DateTimeField(
        verbose_name='Дата создания',
        auto_now_add=True,
        db_index=True,
    )

    class Meta:
        abstract = True
