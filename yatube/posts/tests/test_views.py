import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..constants import INDEX_PER_PAGE_LIMIT
from ..forms import CommentForm, PostForm
from ..models import Follow, Group, Post

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)
User = get_user_model()


class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test_user')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(PostPagesTests.user)

    def test_pages_uses_correct_template(self):
        """
        Тестируем, URL-адрес использует соответствующий шаблон.
        """
        pages_names_templates = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list', kwargs={'slug': 'test_slug'}):
                'posts/group_list.html',
            reverse('posts:profile', kwargs={'username': 'test_user'}):
                'posts/profile.html',
            reverse(
                'posts:post_detail',
                kwargs={
                    'post_id': f'{PostPagesTests.post.id}',
                }): 'posts/post_detail.html',
            reverse('posts:post_edit',
                    kwargs={'post_id': f'{PostPagesTests.post.id}'}):
                'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html',
        }

        for reverse_name, template in pages_names_templates.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)


class TestPostContext(TestCase):
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
        self.authorized_client.force_login(TestPostContext.user)

    @override_settings(CACHES={
        'default': {'BACKEND': 'django.core.cache.backends.dummy.DummyCache', }
    })
    def test_index_page_show_correct_context(self):
        """Тестируем корректное отображение контекста главной страницы."""

        response = self.authorized_client.get(reverse('posts:index'))
        expected_list = list(Post.objects.all()[:INDEX_PER_PAGE_LIMIT])
        context_list = response.context.get('page_obj').object_list
        self.assertListEqual(context_list, expected_list)

    def test_group_list_page_show_correct_context(self):
        """Тестируем корректное отображение контекста страницы группы."""

        response = self.authorized_client.get(reverse(
            'posts:group_list',
            kwargs={'slug': 'test_slug'}))
        expected_list = list(
            TestPostContext.group.posts.all()[:INDEX_PER_PAGE_LIMIT])
        context_list = response.context.get('page_obj').object_list
        self.assertListEqual(context_list, expected_list)

    def test_profile_page_show_correct_context(self):
        """Тестируем корректное отображение контекста профайла."""

        response = self.authorized_client.get(reverse(
            'posts:profile',
            kwargs={'username': 'test_user'}))
        expected_list = list(
            TestPostContext.user.posts.all()[:INDEX_PER_PAGE_LIMIT])
        context_list = response.context.get('page_obj').object_list
        self.assertListEqual(context_list, expected_list)

    def test_post_detail_page_show_correct_context(self):
        """Тестируем корректное отображение контекста post_detail."""

        response = self.authorized_client.get(reverse(
            'posts:post_detail',
            kwargs={'post_id': 1}))
        expected_post = Post.objects.get(id=1)
        context_post = response.context.get('post')
        self.assertEqual(context_post, expected_post)
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
            'posts:post_edit', kwargs={'post_id': 1}))

        self.assertIn('form', response.context)
        self.assertIsInstance(response.context['form'], PostForm)

        self.assertIn('is_edit', response.context)
        is_edit = response.context['is_edit']
        self.assertIsInstance(is_edit, bool)

    def test_first_paginator_page_contains_ten_records(self):
        """
        Тестируем корректное отображение количества постов
        пагинатора первой страницы.
        """

        pages_name_paginator_records = {
            reverse('posts:index'): 10,
            reverse('posts:group_list', kwargs={'slug': 'test_slug'}): 10,
            reverse('posts:profile', kwargs={'username': 'test_user'}): 10,
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
            reverse('posts:index'): 3,
            reverse('posts:group_list', kwargs={'slug': 'test_slug'}): 3,
            reverse('posts:profile', kwargs={'username': 'test_user'}): 3,
        }
        for reverse_name, pag_records in pages_name_paginator_records.items():
            with self.subTest():
                response = self.authorized_client.get(reverse_name + '?page=2')
                self.assertEqual(
                    len(response.context['page_obj']), pag_records)

    def test_index_page_cache(self):
        """Тестируем кеш главной страницы."""

        queryset_on_delete = Post.objects.filter(id__in=[10, 11, 12, 13])
        queryset_on_delete.delete()

        posts_count = Post.objects.count()
        response = self.authorized_client.get(reverse('posts:index'))
        self.assertEqual(len(response.context['page_obj']), posts_count)

        a = Post.objects.get(id=9)
        a.delete()

        refresh_posts_count = Post.objects.count()
        self.assertEqual(
            len(response.context['page_obj']), refresh_posts_count + 1)


class TestOnePost(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test_user')
        cls.group_one = Group.objects.create(
            title='Тестовая группа 1',
            slug='test_slug_one',
            description='Тестовое описание 1',
        )
        cls.group_two = Group.objects.create(
            title='Тестовая группа 2',
            slug='test_slug_two',
            description='Тестовое описание 2',
        )
        Post.objects.bulk_create(
            [Post(
                author=cls.user,
                group=cls.group_one,
                text=f'Тестовый пост № {i}',
            ) for i in range(5)]
        )
        Post.objects.create(
            author=cls.user,
            group=cls.group_two,
            text='Новый тестовый пост',
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(TestOnePost.user)

    def test_pages_show_correct_count_posts(self):
        """Тестируем корректное отображение количества постов на страницах."""

        pages_posts_count = {
            reverse('posts:index'): 6,
            reverse('posts:group_list', kwargs={'slug': 'test_slug_one'}): 5,
            reverse('posts:profile', kwargs={'username': 'test_user'}): 6,
        }
        for page, posts_count in pages_posts_count.items():
            with self.subTest(page=page):
                response = self.authorized_client.get(page)
                self.assertEqual(
                    len(
                        response.context.get('page_obj').object_list
                    ), posts_count)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class TestImagePost(TestCase):
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
        cls.post = Post.objects.create(
            author=cls.user,
            group=cls.group,
            text='Тестовый пост',
            image=cls.uploaded,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.auth_client = Client()
        self.auth_client.force_login(TestImagePost.user)

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

        response = self.guest_client.get(reverse('posts:index'))
        expected_list = list(Post.objects.all()[:INDEX_PER_PAGE_LIMIT])
        context_list = response.context.get('page_obj').object_list
        self.assertListEqual(context_list, expected_list)

    @override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
    def test_profile_show_correct_context_with_img(self):
        """
        Тестируем корректное отображение контекста с картинкой профайла.
        """

        response = self.auth_client.get(reverse(
            'posts:profile',
            kwargs={'username': 'test_user'}))
        expected_list = list(
            TestImagePost.user.posts.all()[:INDEX_PER_PAGE_LIMIT])
        context_list = response.context.get('page_obj').object_list
        self.assertListEqual(context_list, expected_list)

    @override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
    def test_group_page_show_correct_context_with_img(self):
        """
        Тестируем корректное отображение контекста с картинкой страницы группы.
        """

        response = self.auth_client.get(reverse(
            'posts:group_list',
            kwargs={'slug': 'test_slug'}))
        expected_list = list(
            TestImagePost.group.posts.all()[:INDEX_PER_PAGE_LIMIT])
        context_list = response.context.get('page_obj').object_list
        self.assertListEqual(context_list, expected_list)

    @override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
    def test_post_detail_page_show_correct_context_with_img(self):
        """
        Тестируем корректное отображение контекста с картинкой post_detail.
        """
        response = self.auth_client.get(reverse(
            'posts:post_detail',
            kwargs={'post_id': 1}))
        expected_post = Post.objects.get(id=1)
        context_post = response.context.get('post')
        self.assertEqual(context_post, expected_post)


class TestFollow(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_one = User.objects.create_user(username='ivanov')
        cls.user_two = User.objects.create_user(username='petrov')

    def test_follow_post(self):
        """
        Тестируем, что новый пост подписки отображется в ленте подписчиков.
        """

        Follow.objects.create(
            user=TestFollow.user_one,
            author=TestFollow.user_two,
        )

        Post.objects.create(
            text='test text',
            author=TestFollow.user_two,
        )

        post = Post.objects.get(author__following__user=TestFollow.user_one)
        self.assertEqual(post.author, TestFollow.user_two)
        self.assertEqual(post.text, 'test text')

    def test_no_self_follow(self):
        """
        Тестируем невозможность подписаться сам на себя.
        """
