import http

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase

User = get_user_model()


class CoreURLTests(TestCase):

    def setUp(self):
        cache.clear()
        self.guest_client = Client()
        self.user_author = User.objects.create(username='hanson')
        self.authorized_user_author = Client()
        self.authorized_user_author.force_login(self.user_author)

    def test_unexisting_page_are_unavailable(self):
        '''Проверяем, что несуществующая страница отдаёт 404'''
        unexisting_page = '/unexisting_page'
        users = [
            self.guest_client,
            self.authorized_user_author
        ]

        for user in users:
            with self.subTest(user=user):
                self.assertEqual(
                    user.get(unexisting_page).status_code,
                    http.HTTPStatus.NOT_FOUND
                )

    def test_unexisting_page_shown_with_right_template(self):
        '''Проверяем, что у 404-й правильный шаблон'''
        response = self.authorized_user_author.get('/unexisting_page')
        self.assertTemplateUsed(response, 'core/404.html')
