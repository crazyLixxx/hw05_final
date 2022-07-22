import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Follow, Group, Post

User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PagesAndContext(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        User.objects.create_user(username='hanson')
        Group.objects.create(
            title='Название группы',
            slug='group_slug',
            description='Описание группы на 500 символов'
        )
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        Post.objects.create(
            author=User.objects.get(username='hanson'),
            text='пост про зефирных морячков',
            group=Group.objects.get(id=1),
            image=uploaded
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        cache.clear()
        self.guest_client = Client()
        self.user_author = User.objects.get(username='hanson')
        self.authorized_user_author = Client()
        self.authorized_user_author.force_login(self.user_author)
        self.post = Post.objects.get(id=1)
        self.group = Group.objects.get(slug='group_slug')

    def test_pages_uses_correct_template(self):
        '''Тестируем, что имена из namespace вызывают правильные шаблоны'''

        test_objects = {
            reverse('posts:index'): 'posts/index.html',
            reverse(
                'posts:group_list', kwargs={'slug': self.group.slug}
            ): 'posts/group_list.html',
            reverse(
                'posts:profile', kwargs={'username': self.user_author.username}
            ): 'posts/profile.html',
            reverse(
                'posts:post_detail', kwargs={'post_id': self.post.id}
            ): 'posts/post_detail.html',
            reverse(
                'posts:post_edit', kwargs={'post_id': self.post.id}
            ): 'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html'
        }

        for name, template in test_objects.items():
            with self.subTest(name=name):
                response = self.authorized_user_author.get(name)
                self.assertTemplateUsed(response, template)

    def test_pages_with_posts_show_correct_context(self):
        '''Тестируем элементы поста при выводе на страницах'''

        test_objects = [
            self.authorized_user_author.get(
                reverse('posts:index')
            ).context['page_obj'][0],
            self.authorized_user_author.get(
                reverse(
                    'posts:group_list',
                    kwargs={'slug': 'group_slug'})
            ).context['page_obj'][0],
            self.authorized_user_author.get(
                reverse(
                    'posts:profile',
                    kwargs={'username': 'hanson'})
            ).context['page_obj'][0],
            self.authorized_user_author.get(
                reverse(
                    'posts:post_detail',
                    kwargs={'post_id': '1'})
            ).context['article'],
        ]

        for test_post in test_objects:
            with self.subTest(test_post=test_post):
                self.assertEqual(test_post.author, self.post.author)
                self.assertEqual(test_post.text, self.post.text)
                self.assertEqual(test_post.group, self.post.group)
                self.assertEqual(test_post.created, self.post.created)
                self.assertTrue(
                    test_post.image,
                    'На странице не выводится картинка поста'
                )

    def test_page_paginator(self):
        '''Тестируем, что пагинатор отдаёт корректное количество постов'''

        Post.objects.bulk_create([
            Post(
                text=f'Текст поста {i + 1}',
                author=self.user_author,
                group=self.group
            )
            for i in range(15)
        ])
        test_objects = [
            (reverse('posts:index'),
                'page_obj'),
            (reverse(
                'posts:group_list', kwargs={'slug': self.group.slug}
            ),
                'page_obj'),
            (reverse(
                'posts:profile', kwargs={'username': self.user_author.username}
            ),
                'page_obj'),
        ]

        for page, posts in test_objects:
            response_1 = self.authorized_user_author.get(page)
            response_2 = self.authorized_user_author.get(page + '?page=2')
            self.assertEqual(
                len(response_1.context[posts]),
                10,
                f'ошибка в выдаче первой страницы пагинации на {page}')
            self.assertEqual(
                len(response_2.context[posts]),
                6,
                f'ошибка в выдаче второй страницы пагинации на {page}')

    def test_index_page_show_all_posts_from_defferent_groups(self):
        '''
        Тестируем, что главная страница отображает все посты, в том
        числе их разных групп
        '''

        group_2 = Group.objects.create(
            title='Название группы 2',
            slug='group_slug_2',
            description='Описание группы 2 на 500 символов'
        )
        Post.objects.create(
            text='Небольшой текст',
            author=self.user_author,
            group=group_2
        )
        response = self.authorized_user_author.get(reverse('posts:index'))
        test_posts_count = len(response.context['page_obj'])
        all_posts_count = Post.objects.count()

        self.assertEqual(test_posts_count, all_posts_count)

    def test_group_page_show_posts_only_from_one_group(self):
        '''
        Тестируем, что на странице группы отображаются посты только этой группы
        '''

        new_group = Group.objects.create(
            title='Название группы 2',
            slug='new_group',
            description='Описание группы 2 на 500 символов'
        )
        Post.objects.create(
            text='Небольшой текст',
            author=self.user_author,
            group=new_group
        )
        response_old_group = self.authorized_user_author.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug})
        )
        posts_in_old_group = response_old_group.context['page_obj']

        for post in posts_in_old_group:
            with self.subTest(post=post):
                self.assertEqual(post.group.slug, self.group.slug)

    def test_profile_page_show_posts_from_one_user(self):
        '''
        Тестируем, что в профиле отображаются только посты пользователя
        '''

        author_2 = User.objects.create(username='tom')
        Post.objects.create(
            text='небольшой текст',
            author=author_2
        )
        response = self.authorized_user_author.get(
            reverse('posts:profile', kwargs={'username': author_2.username})
        )
        posts = response.context['page_obj']

        for post in posts:
            with self.subTest(post=post):
                self.assertEqual(
                    post.author.username, author_2.username)

    def test_create_post_and_check_it_availability(self):
        '''
        Проверяем создание поста и его появление вначале
        главной, страницы группы и профиля пользователя
        '''
        test_post = Post.objects.create(
            author=self.user_author,
            text='тестовый тост',
            group=self.group
        )
        test_objects = [
            (
                'Новый пост не появляется на главной странице',
                reverse('posts:index'),
                'page_obj'),
            (
                'Новый пост не появляется на странице присвоенной ему группы',
                reverse(
                    'posts:group_list', kwargs={'slug': self.group.slug}
                ),
                'page_obj'),
            (
                'Новый пост не появляется на странице его автора',
                reverse(
                    'posts:profile',
                    kwargs={'username': self.user_author.username}
                ),
                'page_obj'),
        ]

        for error, page, posts in test_objects:
            with self.subTest(page=page):
                response = self.authorized_user_author.get(page)
                post = response.context[posts][0]
                self.assertEqual(post.id, test_post.id, error)

    def test_only_authorized_user_can_send_comment(self):
        '''
        Провреям, что только авторизованный пользователь
        может оставить коммент к посту
        '''

        test_sessions = [
            (
                (
                    'Неавторизваонный пользователь не перенаправлен '
                    'на страницу авторизации при попытке оставить комментарий'
                ),
                reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
                self.guest_client,
                reverse('users:login') + '?next=/posts/1/comment/'
            ),
            (
                'Авторизваонный пользователь не смог оставить комментарий',
                reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
                self.authorized_user_author,
                reverse('posts:post_detail', kwargs={'post_id': self.post.id}),
            ),
        ]

        for error, add_comment, user, result in test_sessions:
            with self.subTest(add_commnt=add_comment):
                self.assertRedirects(
                    user.get(add_comment),
                    result,
                    302,
                    200,
                    error
                )

    def test_index_page_cache(self):
        '''Проверяем, что главная страница кэшируется'''

        cached_post = Post.objects.create(
            text='ты закэширован',
            author=self.user_author
        )
        visit_1 = self.guest_client.get(reverse('posts:index'))
        cached_post.delete()
        visit_2 = self.guest_client.get(reverse('posts:index'))
        cache.clear()
        visit_3 = self.guest_client.get(reverse('posts:index'))

        self.assertContains(
            visit_1,
            'ты закэширован',
            msg_prefix='Новый пост не добавился на страницу'
        )

        self.assertContains(
            visit_2,
            'ты закэширован',
            msg_prefix='Пост не закеширован'
        )

        self.assertNotContains(
            visit_3,
            'ты закэширован',
            msg_prefix='Пост всё ещё закэширован'
        )


class FollowTesting(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        User.objects.create(username='hanson')
        User.objects.create(username='tom')
        User.objects.create(username='alena')

        Follow.objects.create(
            user=User.objects.get(username='hanson'),
            author=User.objects.get(username='alena')
        )

    def setUp(self):
        cache.clear()
        self.user_author = User.objects.get(username='alena')
        self.subscriber = User.objects.get(username='hanson')
        self.subscriber_authorized = Client()
        self.subscriber_authorized.force_login(self.subscriber)
        self.subscriber_2 = User.objects.get(username='tom')
        self.subscriber_2_authorized = Client()
        self.subscriber_2_authorized.force_login(self.subscriber_2)

    def test_user_can_subscribe_and_unsubscribe_from_author(self):
        '''
        Проверяем, что пользователь может подписаться и отписаться на автора
        '''
        count_followings = Follow.objects.count()
        self.subscriber_2_authorized.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.user_author.username}
            )
        )
        test_subscribe = Follow.objects.all().reverse()[0]

        self.assertEqual(
            Follow.objects.count(),
            count_followings + 1,
            'подписка не создалась'
        )
        self.assertEqual(
            test_subscribe.user,
            self.subscriber,
            'подписка создана не на того пользователя'
        )
        self.assertEqual(
            test_subscribe.author,
            self.user_author,
            'подписка создана не на того автора'
        )

        test_subscribe.delete()
        self.assertEqual(
            Follow.objects.count(),
            count_followings,
            'подписка не удалилась'
        )

    def test_new_post_shown_in_subscribes(self):
        '''Проверяем, что новый пост появляется в подписках'''

        Post.objects.create(
            text='смотри, там собака',
            author=self.user_author
        )
        follower_visit = self.subscriber_authorized.get(
            reverse('posts:follow_index')
        )
        unfollower_visit = self.subscriber_2_authorized.get(
            reverse('posts:follow_index')
        )
        self.assertContains(
            follower_visit,
            'смотри, там собака',
            msg_prefix='Новый пост не появился на странице подписчика'
        )

        self.assertNotContains(
            unfollower_visit,
            'смотри, там собака',
            msg_prefix='Новый пост появился на странице неподписчика'
        )
