from django.test import TestCase, Client
from django.urls import reverse
from django import forms
from posts.models import Post, Group, User, Comment, Follow
from http import HTTPStatus
from django.core.cache import cache

cache.clear()


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Luchik')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        posts = [Post(text=f'Тестовый пост{i}', author=cls.user,
                      group=cls.group) for i in range(13)]

        cls.post = Post.objects.bulk_create(posts)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_first_page_contains_ten_records(self):
        # Проверка: количество постов на первой странице равно 10.
        response = self.client.get(reverse('posts:index'))
        self.assertEqual(len(response.context['page_obj']), 10)

    def test_second_page_contains_three_records(self):
        # Проверка: на второй странице должно быть три поста.
        response = self.client.get(reverse('posts:index') + '?page=2')
        self.assertEqual(len(response.context['page_obj']), 3)


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
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.authorized_client_author = Client()
        self.authorized_client_author.force_login(PostURLTests.user)

    # Проверяем используемые шаблоны
    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list', kwargs={
                'slug': 'test-slug'
            }): 'posts/group_list.html',
            reverse('posts:profile', kwargs={
                'username': 'Luchik'
            }): 'posts/profile.html',
            reverse('posts:post_detail', kwargs={
                'post_id': self.post.pk
            }): 'posts/post_detail.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:post_edit', kwargs={
                'post_id': self.post.pk
            }): 'posts/create_post.html',
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client_author.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_post_create_show_correct_context(self):
        """Шаблон create сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_edit_show_correct_context(self):
        """Шаблон post_edit сформирован с правильным контекстом."""
        response = self.authorized_client_author.get(
            reverse('posts:post_edit', kwargs={'post_id': self.post.pk})
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_index_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:index'))
        self.assertEqual(response.context['page_obj'][0], self.post)

    def test_group_list_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': 'test-slug'})
        )
        self.assertEqual(response.context['group'], self.group)

    def test_profile_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': 'Luchik'})
        )
        self.assertEqual(response.context['author'], self.post.author)

    def test_post_detail_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.pk})
        )
        self.assertEqual(response.context['post'], self.post)


class PostTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Marina')
        cls.post = Post.objects.create(
            author=User.objects.create_user(username='Luchik'),
            text='Тестовый пост 1',
            group=Group.objects.create(
                title='Тестовая группа 1',
                slug='test-slug_1',
            )
        )

        cls.post = Post.objects.create(
            author=User.objects.create_user(username='Kot'),
            text='Тестовый пост 2',
            group=Group.objects.create(
                title='Тестовая группа 2',
                slug='test-slug_2',
            )
        )
        cls.comment = Comment.objects.create(
            post=cls.post,
            author=cls.user,
            text='Комментарий'
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.authorized_client_author = Client()
        self.authorized_client_author.force_login(PostTests.user)

    def test_post_not_another_group(self):
        """Пост не попал в другую группу"""
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': 'test-slug_1'})
        )
        first_object = response.context['page_obj'][0]
        post_text_0 = first_object.text
        self.assertTrue(post_text_0, 'Тестовый пост 2')

    def test_post_on_the_index_page(self):
        """Пост на главной странице"""
        response = self.authorized_client.get(reverse('posts:index'))
        first_object = response.context['page_obj'][0]
        post_text_0 = first_object.text
        post_author_0 = first_object.author.username
        post_group_0 = first_object.group.title
        self.assertEqual(post_text_0, 'Тестовый пост 2')
        self.assertEqual(post_author_0, 'Kot')
        self.assertEqual(post_group_0, 'Тестовая группа 2')

    def test_post_on_the_group_list_page(self):
        """Пост на странице группы"""
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': 'test-slug_2'})
        )
        first_object = response.context['group']
        group_title_0 = first_object.title
        group_slug_0 = first_object.slug
        self.assertEqual(group_title_0, 'Тестовая группа 2')
        self.assertEqual(group_slug_0, 'test-slug_2')

    def test_post_on_the_profile_page(self):
        """Пост в профайле пользователя"""
        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': 'Kot'})
        )
        first_object = response.context['page_obj'][0]
        post_text_0 = first_object.text
        self.assertEqual(response.context['author'].username, 'Kot')
        self.assertEqual(post_text_0, 'Тестовый пост 2')

    def test_context_on_the_post_detail_page(self):
        """Комментарий в контексте передан на страницу поста"""
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.pk})
        )
        first_object = response.context['comments'][0]
        comments_text = first_object.text
        comments_author = first_object.author.username
        comments_post = first_object.post.text
        self.assertEqual(comments_text, 'Комментарий')
        self.assertEqual(comments_author, 'Marina')
        self.assertEqual(comments_post, 'Тестовый пост 2')

    def test_cache_index_page(self):
        """Тест кэширования главной страницы index.html"""
        first_state = self.authorized_client.get(reverse('posts:index'))
        post_1 = Post.objects.get(pk=1)
        post_1.text = 'Измененный текст'
        post_1.save()
        second_state = self.authorized_client.get(reverse('posts:index'))
        self.assertEqual(first_state.content, second_state.content)
        cache.clear()
        third_state = self.authorized_client.get(reverse('posts:index'))
        self.assertNotEqual(first_state.content, third_state.content)


class FollowTests(TestCase):
    def setUp(self):
        self.client_auth_follower = Client()
        self.client_auth_following = Client()
        self.user_follower = User.objects.create_user(username='Luchik')
        self.user_following = User.objects.create_user(username='Kot')
        self.post = Post.objects.create(
            author=self.user_following,
            text='Тестовый пост'
        )
        self.client_auth_follower.force_login(self.user_follower)
        self.client_auth_following.force_login(self.user_following)

    def test_follow(self):
        self.client_auth_follower.get(reverse('posts:profile_follow',
                                              kwargs={'username':
                                                      self.user_following.
                                                      username}))
        self.assertEqual(Follow.objects.all().count(), 1)

    def test_unfollow(self):
        self.client_auth_follower.get(reverse('posts:profile_follow',
                                              kwargs={'username':
                                                      self.user_following.
                                                      username}))
        self.client_auth_follower.get(reverse('posts:profile_unfollow',
                                      kwargs={'username':
                                              self.user_following.username}))
        self.assertEqual(Follow.objects.all().count(), 0)

    def test_subscription_feed(self):
        """Запись появляется в ленте подписчиков"""
        Follow.objects.create(user=self.user_follower,
                              author=self.user_following)
        response = self.client_auth_follower.get('/follow/')
        post_text_0 = response.context['page_obj'][0].text
        self.assertEqual(post_text_0, 'Тестовый пост')
        response = self.client_auth_following.get('/follow/')
        self.assertNotContains(response, 'Тестовый пост')
