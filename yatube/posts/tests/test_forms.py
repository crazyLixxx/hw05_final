import shutil
import tempfile

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Group, Post

User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostCreationAndEditFormsTests(TestCase):
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
            text='Мой первый пост'
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.user_author = User.objects.get(username='hanson')
        self.authorized_user_author = Client()
        self.authorized_user_author.force_login(self.user_author)
        self.post = Post.objects.get(id=1)
        self.group = Group.objects.get(slug='group_slug')

    def test_post_forms(self):
        '''
        Тестируем формы на страницах создания и редактирования
        поста выводится форма
        '''
        test_objects = [
            (reverse('posts:post_edit', kwargs={'post_id': self.post.id})),
            (reverse('posts:post_create')),
        ]
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField
        }

        for page in test_objects:
            response = self.authorized_user_author.get(page)
            for value, expected in form_fields.items():
                with self.subTest(value=value):
                    form_field = response.context.get('form').fields.get(value)
                    self.assertIsInstance(form_field, expected)

    def test_post_edit_page_show_correct_post(self):
        '''
        Проверяем, что в форму редактирования поста передаётся пост
        , соответсвующий урлу
        '''
        response = self.authorized_user_author.get(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id})
        )
        post_id = response.context['form'].instance.id

        self.assertEqual(post_id, self.post.id)

    def test_sending_valid_form_create_post(self):
        '''Проверяем, что валидная форма создаёт пост'''

        posts_count = Post.objects.count()
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
        form_data = {
            'text': 'тестовый текст поста',
            'image': uploaded
        }
        self.authorized_user_author.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)

    def test_sending_valid_form_edit_post(self):
        '''Проверяем, что происходит редактирование поста'''

        form_data = {
            'text': 'забыл добавить группу',
            'group': self.group.id
        }
        self.authorized_user_author.post(
            reverse('posts:post_edit', args=(1,)),
            data=form_data
        )
        post = Post.objects.get(id=1)
        self.assertEqual(post.text, 'забыл добавить группу')
        self.assertEqual(post.group, self.group)

    def test_comment_show_on_post_page_after_add(self):
        '''
        Проверяем, что после успешного добавления на странице
        поста появляется комментарий
        '''
        post_id = 1
        comment_data = {
            'text': 'крутое фото!',
            'post': Post.objects.get(id=post_id),
        }
        self.authorized_user_author.post(
            reverse('posts:add_comment', args=(post_id,)),
            data=comment_data
        )
        response = self.authorized_user_author.get(
            reverse('posts:post_detail', kwargs={'post_id': post_id})
        )
        comment = response.context['comments'][0]
        self.assertEqual(comment.text, 'крутое фото!')
