import shutil
import tempfile

from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..constants import PAGI_INDEX_LAST_PAGE, PAGI_INDEX_PER_PAGE
from ..forms import CommentForm, PostForm
from ..models import Comment, Follow, Group, Post, User

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.uploaded = SimpleUploadedFile(
            name="small.gif",
            content=(
                b"\x47\x49\x46\x38\x39\x61\x02\x00"
                b"\x01\x00\x80\x00\x00\x00\x00\x00"
                b"\xFF\xFF\xFF\x21\xF9\x04\x00\x00"
                b"\x00\x00\x00\x2C\x00\x00\x00\x00"
                b"\x02\x00\x01\x00\x00\x02\x02\x0C"
                b"\x0A\x00\x3B"
            ),
            content_type="image/gif",
        )
        cls.user = User.objects.create_user(username='test_user')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание',
        )
        cls.group_two = Group.objects.create(
            title='Тестовая группа 2',
            slug='test_slug_two',
            description='Тестовое описание 2',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            group=cls.group,
            text='Тестовый пост',
        )
        cls.comment = Comment.objects.create(
            text='Тестовый коммент',
            author=cls.user,
            post=cls.post,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def check_post(self, obj):
        """Функция проверки объекта по id, group, author, text, image."""

        self.assertEqual(obj.id, self.post.id)
        self.assertEqual(obj.group, self.group)
        self.assertEqual(obj.author, self.user)
        self.assertEqual(obj.text, self.post.text)

        if obj.image:
            self.assertEqual(obj.image.name, self.post.image.name)

    def create_post_with_img(self):
        """Функция создания нового поста с картинкой."""

        return Post.objects.create(
            text='Новый тестовый пост',
            author=self.user,
            group=self.group,
            image=self.uploaded,
        )

    def create_new_post(self):
        """Функция создания нового тестового поста."""

        return Post.objects.create(
            text='Новый тестовый пост',
            author=self.user,
            group=self.group,
        )

    def check_new_post(self, obj, expected_obj):
        """Функция, проверяющая новый пост по атрибутам id, text, author."""

        self.assertEqual(obj.id, expected_obj.id)
        self.assertEqual(obj.text, expected_obj.text)
        self.assertEqual(obj.author, expected_obj.author)
        self.assertEqual(obj.group, expected_obj.group)

        if obj.image:
            self.assertEqual(obj.image.name, expected_obj.image.name)

    def test_pages_uses_correct_template(self):
        """
        Тестируем, URL-адрес использует соответствующий шаблон.
        """
        pages_names_templates = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list', kwargs={'slug': self.group.slug}):
                'posts/group_list.html',
            reverse('posts:profile', kwargs={'username': self.user.username}):
                'posts/profile.html',
            reverse(
                'posts:post_detail',
                kwargs={
                    'post_id': f'{self.post.id}',
                }): 'posts/post_detail.html',
            reverse('posts:post_edit',
                    kwargs={'post_id': f'{self.post.id}'}):
                'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html',
        }

        for reverse_name, template in pages_names_templates.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    @override_settings(CACHES={
        'default': {'BACKEND': 'django.core.cache.backends.dummy.DummyCache', }
    })
    def test_index_page_show_correct_context(self):
        """Тестируем корректное отображение контекста главной страницы."""

        response = self.authorized_client.get(reverse('posts:index'))
        first_object = response.context['page_obj'][0]
        self.check_post(first_object)

    def test_group_list_page_show_correct_context(self):
        """Тестируем корректное отображение контекста страницы группы."""

        response = self.authorized_client.get(reverse(
            'posts:group_list',
            kwargs={'slug': self.group.slug}))
        first_object = response.context['page_obj'][0]
        group_posts = response.context['group']
        self.check_post(first_object)
        self.assertEqual(group_posts.id, self.group.id)
        self.assertEqual(group_posts.title, self.group.title)
        self.assertEqual(group_posts.slug, self.group.slug)
        self.assertEqual(group_posts.description, self.group.description)

    def test_profile_page_show_correct_context(self):
        """Тестируем корректное отображение контекста профайла."""

        response = self.authorized_client.get(reverse(
            'posts:profile',
            kwargs={'username': self.user.username}))
        first_object = response.context['page_obj'][0]
        author = response.context['author']
        self.check_post(first_object)
        self.assertEqual(author.id, self.user.id)
        self.assertEqual(author.username, self.user.username)
        self.assertIn('following', response.context)
        self.assertIsInstance(response.context['following'], bool)

    def test_post_detail_page_show_correct_context(self):
        """Тестируем корректное отображение контекста post_detail."""

        response = self.authorized_client.get(reverse(
            'posts:post_detail',
            kwargs={'post_id': self.post.id}))
        context_post = response.context.get('post')
        context_comment = response.context['comments'][0]
        self.check_post(context_post)
        self.assertIn('comments', response.context)
        self.assertEqual(context_comment.id, self.comment.id)
        self.assertEqual(context_comment.text, self.comment.text)
        self.assertEqual(context_comment.author, self.comment.author)
        self.assertIn('form', response.context)
        self.assertIsInstance(response.context['form'], CommentForm)

    def test_post_create_show_correct_context(self):
        """Тестируем корректное отображение контекста формы post_create."""

        response = self.authorized_client.get(reverse('posts:post_create'))
        self.assertIn('form', response.context)
        self.assertIsInstance(response.context['form'], PostForm)

    def test_post_edit_and_create_form_show_correct_context(self):
        """Тестируем корректное отображение контекста формы post_edit."""

        response = self.authorized_client.get(reverse(
            'posts:post_edit', kwargs={'post_id': self.post.id}))

        self.assertIn('form', response.context)
        self.assertIsInstance(response.context['form'], PostForm)

        self.assertIn('is_edit', response.context)
        is_edit = response.context['is_edit']
        self.assertIsInstance(is_edit, bool)

    def test_post_do_not_shows_in_another_group(self):
        """Тестируем корректное отсутсвие поста в контексте другой группы."""

        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group_two.slug})
        )
        self.assertEqual(len(response.context['page_obj']), 0)

    def test_post_shows_on_main_page(self):
        """Тестируем корректное отображение поста на главной странице"""

        new_post = self.create_new_post()
        response = self.authorized_client.get(reverse('posts:index'))
        first_object = response.context['page_obj'][0]
        self.check_new_post(first_object, new_post)

    def test_post_shows_on_group_page(self):
        """Тестируем, что пост появится в контексте страницы группы."""

        new_post = self.create_new_post()
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug})
        )
        first_object = response.context['page_obj'][0]
        self.check_new_post(first_object, new_post)

    def test_post_show_on_profile_page(self):
        """Тестируем, что пост появится в контексте профайла."""

        new_post = self.create_new_post()
        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': self.user.username})
        )
        first_object = response.context['page_obj'][0]
        self.check_new_post(first_object, new_post)

    @override_settings(
        MEDIA_ROOT=TEMP_MEDIA_ROOT,
        CACHES={
            'default': {
                'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
            }
        }
    )
    def test_index_show_correct_context_with_img(self):
        """
        Тестируем корректное отображение контекста
        с картинкой главной страницы.
        """
        new_post_img = self.create_post_with_img()
        response = self.authorized_client.get(reverse('posts:index'))
        first_object = response.context['page_obj'][0]
        self.check_new_post(first_object, new_post_img)

    @override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
    def test_profile_show_correct_context_with_img(self):
        """
        Тестируем корректное отображение контекста с картинкой профайла.
        """
        new_post_img = self.create_post_with_img()
        response = self.authorized_client.get(reverse(
            'posts:profile',
            kwargs={'username': self.user.username}))
        first_object = response.context['page_obj'][0]
        author = response.context['author']
        self.assertEqual(author.id, self.user.id)
        self.assertEqual(author.username, self.user.username)
        self.check_new_post(first_object, new_post_img)

    @override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
    def test_group_page_show_correct_context_with_img(self):
        """
        Тестируем корректное отображение контекста с картинкой страницы группы.
        """
        new_post_img = self.create_post_with_img()
        response = self.authorized_client.get(reverse(
            'posts:group_list',
            kwargs={'slug': self.group.slug}))
        first_object = response.context['page_obj'][0]
        group = response.context['group']
        self.check_new_post(first_object, new_post_img)
        self.assertEqual(group.id, self.group.id)
        self.assertEqual(group.title, self.group.title)
        self.assertEqual(group.slug, self.group.slug)
        self.assertEqual(group.description, self.group.description)

    @override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
    def test_post_detail_page_show_correct_context_with_img(self):
        """
        Тестируем корректное отображение контекста с картинкой post_detail.
        """

        new_post_img = self.create_post_with_img()
        response = self.authorized_client.get(reverse(
            'posts:post_detail',
            kwargs={'post_id': new_post_img.id}))
        first_object = response.context['post']
        self.check_new_post(first_object, new_post_img)
        self.assertIn('form', response.context)
        self.assertIsInstance(response.context['form'], CommentForm)


class TestPaginator(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test_user')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание',
        )
        Post.objects.bulk_create(
            [Post(
                author=cls.user,
                group=cls.group,
                text=f'Тестовый пост № {i}',
            ) for i in range(13)]
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_first_paginator_page_contains_ten_records(self):
        """
        Тестируем корректное отображение количества постов
        пагинатора первой страницы.
        """

        pages_name_paginator_records = {
            reverse('posts:index'):
                PAGI_INDEX_PER_PAGE,
            reverse('posts:group_list', kwargs={'slug': self.group.slug}):
                PAGI_INDEX_PER_PAGE,
            reverse('posts:profile', kwargs={'username': self.user.username}):
                PAGI_INDEX_PER_PAGE,
        }
        for reverse_name, pag_records in pages_name_paginator_records.items():
            with self.subTest():
                response = self.authorized_client.get(reverse_name)
                self.assertEqual(
                    len(response.context['page_obj']), pag_records)

    def test_second_paginator_page_contains_three_records(self):
        """
        Тестируем корректное отображение количества постов
        пагинатора второй страницы.
        """
        pages_name_paginator_records = {
            reverse('posts:index'):
                PAGI_INDEX_LAST_PAGE,
            reverse('posts:group_list', kwargs={'slug': self.group.slug}):
                PAGI_INDEX_LAST_PAGE,
            reverse('posts:profile', kwargs={'username': self.user.username}):
                PAGI_INDEX_LAST_PAGE,
        }
        for reverse_name, pag_records in pages_name_paginator_records.items():
            with self.subTest():
                response = self.authorized_client.get(reverse_name + '?page=2')
                self.assertEqual(
                    len(response.context['page_obj']), pag_records)

    def test_index_page_cache(self):
        """Тестируем кеш главной страницы."""

        response_one = self.authorized_client.get(reverse('posts:index'))
        Post.objects.create(
            text='Тестовый текст',
            author=self.user,
        )

        response_two = self.authorized_client.get(reverse('posts:index'))
        self.assertEqual(len(response_one.content), len(response_two.content))

        cache.clear()

        response_third = self.authorized_client.get(reverse('posts:index'))
        self.assertNotEqual(
            len(response_third.content),
            len(response_one.content)
        )


class TestFollow(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_one = User.objects.create_user(username='ivanov')
        cls.user_two = User.objects.create_user(username='petrov')
        cls.user_third = User.objects.create_user(username='cidorov')
        cls.post = Post.objects.create(
            text='test text',
            author=TestFollow.user_two,
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(TestFollow.user_one)
        self.third_client = Client()
        self.third_client.force_login(TestFollow.user_third)

    def test_follow_post(self):
        """
        Тестируем, что новый пост подписки отображется в ленте подписчиков.
        """

        Follow.objects.create(
            user=self.user_one,
            author=self.user_two,
        )

        Post.objects.create(
            text='Новый тестовый пост',
            author=self.user_two,
        )

        response = self.authorized_client.get(reverse('posts:follow'))
        self.assertEqual(len(response.context.get('page_obj').object_list), 2)

    def test_follow_post_not_author(self):
        """
        Тестируем, что пост не появился в контексте автора,
        на которого нет подписки.
        """

        response = self.third_client.get(reverse('posts:follow'))
        self.assertEqual(len(response.context.get('page_obj').object_list), 0)

    def test_profile_follow(self):
        """Тест подписки."""

        follows_count = Follow.objects.count()
        self.assertFalse(Follow.objects.filter(
            user=self.user_one,
            author=self.user_third,
        ).exists())
        self.authorized_client.get(
            reverse('posts:profile_follow',
                    kwargs={'username': self.user_third.username})
        )
        self.assertTrue(Follow.objects.filter(
            user=self.user_one,
            author=self.user_third,
        ).exists())
        self.assertEqual(Follow.objects.count(), follows_count + 1)

    def test_profile_unfollow(self):
        """Тест отписки."""

        self.authorized_client.get(
            reverse('posts:profile_follow',
                    kwargs={'username': self.user_third.username})
        )
        self.assertTrue(Follow.objects.filter(
            user=self.user_one,
            author=self.user_third,
        ).exists())
        follows_count = Follow.objects.count()

        self.authorized_client.get(
            reverse('posts:profile_unfollow',
                    kwargs={'username': self.user_third.username})
        )

        self.assertFalse(Follow.objects.filter(
            user=self.user_one,
            author=self.user_third,
        ).exists())
        self.assertEqual(Follow.objects.count(), follows_count - 1)
