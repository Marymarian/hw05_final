from http import HTTPStatus
from django.test import TestCase, Client

from posts.models import Post, Group, User, Comment


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Luchik')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
        )

    def setUp(self):
        self.guest_client = Client()
        self.user = User.objects.create_user(username='HasNoName')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.authorized_client_author = Client()
        self.authorized_client_author.force_login(PostURLTests.user)

    def test_urls_at_desired_location(self):
        """Проверяем страницы с общим доступом"""
        templates_url_names = {
            '/': ('posts/index.html', HTTPStatus.OK.value),
            '/group/test-slug/': (
                'posts/group_list.html', HTTPStatus.OK.value
            ),
            '/profile/Luchik/': ('posts/profile.html', HTTPStatus.OK.value),
            f'/posts/{self.post.pk}/': (
                'posts/post_detail.html', HTTPStatus.OK.value
            ),
            '/unexisting_page/': (
                'posts/404.html', HTTPStatus.NOT_FOUND.value
            ),
        }
        for address, template in templates_url_names.items():
            with self.subTest(address=address):
                response = self.guest_client.get(address)
                self.assertEqual(response.status_code, template[1])
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template[0])

    # Проверяем доступность страниц для авторизованного пользователя, автора
    def test_post_create_url_exists_at_desired_location(self):
        """Страница /create/ доступна авторизованному пользователю."""
        response = self.authorized_client.get('/create/')
        self.assertEqual(response.status_code, HTTPStatus.OK.value)
        response = self.authorized_client.get('/create/')
        self.assertTemplateUsed(response, 'posts/create_post.html')

    def test_post_edit_url_exists_at_desired_location(self):
        """Страница /posts/<post_id>/edit/ доступна автору."""
        response = self.authorized_client_author.get(
            f'/posts/{self.post.pk}/edit/'
        )
        self.assertEqual(response.status_code, HTTPStatus.OK.value)
        response = self.authorized_client_author.get(
            f'/posts/{self.post.pk}/edit/'
        )
        self.assertTemplateUsed(response, 'posts/create_post.html')

    # Проверяем редиректы для неавторизованного пользователя
    def test_post_create_url_redirect_anonymous_on_admin_login(self):
        """Страница по адресу /create/ перенаправит анонимного
        пользователя на страницу логина.
        """
        response = self.guest_client.get('/create/', follow=True)
        self.assertRedirects(response, '/auth/login/?next=/create/')

    def test_post_edit_url_redirect_anonymous_on_admin_login(self):
        response = self.guest_client.get(
            f'/posts/{self.post.pk}/edit/', follow=True
        )
        self.assertRedirects(
            response, f'/auth/login/?next=/posts/{self.post.pk}/edit/'
        )

    def test_comment_page_redirect_anonymous(self):
        """Комментировать посты может только авторизованный пользователь,
        иначе будет редирект на странцу логина
        """
        response = self.guest_client.get(
            f'/posts/{self.post.pk}/comment/', follow=True
        )
        self.assertRedirects(
            response, f'/auth/login/?next=/posts/{self.post.pk}/comment/'
        )
