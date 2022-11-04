from django.contrib.auth import get_user_model
from django.db import models

from core.models import CreatedModel

from .constants import POST_STR_LIM

User = get_user_model()


class Post(CreatedModel):
    """Модель постов."""

    text = models.TextField(
        verbose_name='текст поста',
        help_text='Введите текст поста',
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='posts',
        verbose_name='автор поста',
    )
    group = models.ForeignKey(
        'Group',
        on_delete=models.SET_NULL,
        related_name='posts',
        blank=True,
        null=True,
        verbose_name='группа постов',
        help_text='Группа, к которой будет относиться пост',
    )
    image = models.ImageField(
        'Картинка',
        upload_to='posts/',
        blank=True,
    )

    class Meta:
        ordering = ('-created',)
        verbose_name = 'Пост'
        verbose_name_plural = 'Посты'

    def __str__(self):
        """Метод, позволяющий получить text объекта"""
        return self.text[:POST_STR_LIM]


class Group(models.Model):
    """Модель групп постов."""

    title = models.CharField(max_length=200, verbose_name='заголовок группы')
    slug = models.SlugField(max_length=200, unique=True, verbose_name='слаг')
    description = models.TextField(verbose_name='описание группы')

    def __str__(self):
        """Метод, позволяющий получить title объекта Group."""
        return self.title


class Comment(models.Model):
    """Модель комментариев к постам."""

    text = models.TextField(
        verbose_name='текст комментария',
        help_text='Введите комментарий',
    )
    post = models.ForeignKey(
        'Post',
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='пост комментария',
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='автор комментария'
    )
    created = models.DateTimeField(
        verbose_name='Дата создания',
        auto_now_add=True,
    )


class Follow(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='follower',
        verbose_name='Юзер',
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='following',
        verbose_name='Подписка',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'author'],
                name='uniq_user_and_author'
            )
        ]
