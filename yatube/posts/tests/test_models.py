from django.test import TestCase

from ..constants import POST_STR_LIM
from ..models import Group, Post, User


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Тестовый слаг',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
        )

    def test_models_have_correct_object_names(self):
        """Тестируем корректный вывод __str__ объектов моделей."""

        objects_methods_expected_results = {
            str(PostModelTest.group): PostModelTest.group.title,
            str(PostModelTest.post): PostModelTest.post.text[:POST_STR_LIM],
        }

        for object_method, result in objects_methods_expected_results.items():
            with self.subTest(object_method=object_method):
                self.assertEqual(object_method, result)

    def test_models_have_correct_verbose_names(self):
        """Тестируем корректность verbose_name объектов моделей."""

        post = PostModelTest.post
        fields_verbose_names = {
            'text': 'текст поста',
            'group': 'группа постов',
        }

        for field, verbose_name in fields_verbose_names.items():
            with self.subTest(field=field):
                self.assertEqual(
                    post._meta.get_field(field).verbose_name,
                    verbose_name
                )

        fields_help_texts = {
            'text': 'Введите текст поста',
            'group': 'Группа, к которой будет относиться пост',
        }
        for field, help_text in fields_help_texts.items():
            with self.subTest(field=field):
                self.assertEqual(
                    post._meta.get_field(field).help_text,
                    help_text
                )

        post_expected_object_name = post.text[:POST_STR_LIM]
        self.assertEqual(post_expected_object_name, str(post))
