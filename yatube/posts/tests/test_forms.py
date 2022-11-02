import shutil
import tempfile

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Group, Post, User

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostCreateFormTests(TestCase):
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
        cls.user = User.objects.create(username='test_user')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание',
        )
        cls.group_two = Group.objects.create(
            title='Тестовая группа 2',
            slug='test_slug_two',
            description='Тестовое описание второй группы'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            group=cls.group,
            text='Тестовый пост'
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(PostCreateFormTests.user)

    def test_create_post_page_add_new_row_in_db(self):
        """Тестируем форму, добавляющую новую запись в базу."""

        set_posts_before = set(Post.objects.all())
        form_data = {
            'text': 'Тестовый пост добавлен из формы',
            'group': self.group.id,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
        )
        self.assertRedirects(response,
                             reverse('posts:profile',
                                     kwargs={'username': self.user.username}))

        set_posts_after = set(Post.objects.all())
        dif_set = set_posts_after.difference(set_posts_before)
        self.assertEqual(len(dif_set), 1)

        dif_post = dif_set.pop()
        self.assertEqual(dif_post.group, self.group)
        self.assertEqual(dif_post.text, form_data['text'])
        self.assertEqual(dif_post.author, self.user)

    def test_post_edit_page_make_change_in_post(self):
        """Тестируем форму, изменяющую данные поста."""

        posts_count = Post.objects.count()
        form_data = {
            'text': 'Измененный тестовый пост',
            'group': self.group_two.id,
        }
        response = self.authorized_client.post(
            reverse(
                'posts:post_edit',
                kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(response, reverse(
            'posts:post_detail',
            kwargs={'post_id': self.post.id}))
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertTrue(
            Post.objects.filter(
                id=self.post.id,
                text=form_data['text'],
                group=self.group_two.id,
                author=self.user,
            ).exists()
        )

    def test_comment_form_add_new_comment_in_post(self):
        """Тестируем add_comment, к-ый добавляет комментарий к посту."""

        set_comment_before = set(self.post.comments.all())
        form_data = {
            'text': 'Первыйнах',
        }
        response = self.authorized_client.post(
            reverse(
                'posts:add_comment',
                kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(response, reverse(
            'posts:post_detail',
            kwargs={'post_id': self.post.id}))

        set_comment_after = set(self.post.comments.all())
        dif_comment = set_comment_after.difference(set_comment_before)
        self.assertEqual(len(dif_comment), 1)

        comment = dif_comment.pop()
        self.assertEqual(comment.text, form_data['text'])
        self.assertEqual(comment.post.id, self.post.id)

    @override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
    def test_post_form_create_row_with_image(self):
        """
        Тестируем post_create на создание в db новой записи с картинкой.
        """

        set_posts_before = set(Post.objects.all())
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Тестовый пост с картинкой',
            'group': self.group.id,
            'image': self.uploaded,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
        )

        self.assertRedirects(
            response,
            reverse('posts:profile',
                    kwargs={'username': self.user.username})
        )
        set_posts_after = set(Post.objects.all())
        dif_set = set_posts_after.difference(set_posts_before)
        self.assertEqual(len(dif_set), 1)

        dif_post = dif_set.pop()
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertEqual(dif_post.text, form_data['text'])
        self.assertEqual(dif_post.group, self.group)
        self.assertEqual(dif_post.author, self.user)
        self.assertEqual(dif_post.image.name, 'posts/small.gif')
