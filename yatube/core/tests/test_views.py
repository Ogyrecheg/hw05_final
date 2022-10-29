from django.test import Client, TestCase, override_settings


class TestPageNotFound(TestCase):
    def setUp(self):
        self.guest_client = Client()

    @override_settings(DEBUG=False)
    def test_404_page_use_correct_template(self):
        """Тестируем page not found использует корректный шаблон."""

        response = self.guest_client.get('/unexistings_page/')
        self.assertTemplateUsed(response, 'core/404.html')
