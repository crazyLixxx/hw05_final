import http

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from ..models import Group, Post

User = get_user_model()
PUBLIC_URLS = {
    '': 'posts/index.html',
    '/group/group_slug/': 'posts/group_list.html',
    '/profile/hanson/': 'posts/profile.html',
    '/posts/1/': 'posts/post_detail.html'
}
PRIVAT_URLS = {
    '/create/': 'posts/create_post.html',
    '/follow/': 'posts/follow.html',
    '/posts/1/edit/': 'posts/create_post.html'
}


class DynamicURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        User.objects.create_user(username='hanson')
        Group.objects.create(
            title='Название группы',
            slug='group_slug',
            description='Описание группы на 500 символов'
        )
        Post.objects.create(
            author=User.objects.get(username='hanson'),
            text='тут текст гениального поста про стенс'
        )

    def setUp(self):
        self.guest_client = Client()
        self.user_author = User.objects.get(username='hanson')
        self.authorized_user_author = Client()
        self.authorized_user_author.force_login(self.user_author)
        self.post = Post.objects.get(id=1)

    def test_urls_public_urls_available_for_all(self):
        '''Проверяем, что публичные страницы доступны всем'''

        for url in PUBLIC_URLS:
            with self.subTest(url=url):
                self.assertEqual(
                    self.guest_client.get(url).status_code,
                    http.HTTPStatus.OK
                )

    def test_privat_urls_not_available_for_guest_users(self):
        '''Проверяем, что приватные страницы не доступны
        неавторизованным пользователям'''

        for url in PRIVAT_URLS:
            with self.subTest(url=url):
                self.assertRedirects(
                    self.guest_client.get(url),
                    '/auth/login/' + f'?next={url}',
                    http.HTTPStatus.FOUND,
                    http.HTTPStatus.OK
                )

    def test_privat_urls_available_for_authorised_users(self):
        '''Проверяем, что приватные страницы доступны
        авторизованным пользователям'''

        for url in PRIVAT_URLS:
            with self.subTest(url=url):
                self.assertEqual(
                    self.authorized_user_author.get(url).status_code,
                    http.HTTPStatus.OK
                )

    def test_post_edit_available_only_for_author(self):
        '''Проверяем, что редактирование поста доступно
        только его автору'''
        reader = User.objects.create(username='tom')
        reader_authorized = Client()
        reader_authorized.force_login(reader)

        self.assertRedirects(
            reader_authorized.get('/posts/1/edit/'),
            '/posts/1/',
            http.HTTPStatus.FOUND,
            http.HTTPStatus.OK
        )

    def test_pages_uses_correct_template(self):
        '''Проверяем, что страницы используют правильный шаблон'''
        test_objects = [
            PUBLIC_URLS,
            PRIVAT_URLS,
        ]
        for session in test_objects:
            for address, template in session.items():
                with self.subTest(address=address):
                    response = self.authorized_user_author.get(address)
                    self.assertTemplateUsed(response, template)
