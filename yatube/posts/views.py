from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404, redirect
from .models import Post, Group, User, Follow
from .forms import PostForm, CommentForm
from django.urls import reverse


def pagination(queryset, request):
    """Пагинатор."""
    paginator = Paginator(queryset, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return page_obj


def index(request):
    """Функционал главной страницы сайта."""
    context = {
        'page_obj': pagination(Post.objects.all(), request)
    }
    return render(request, 'posts/index.html', context)


def group_posts(request, slug):
    """Записи группы."""
    group = get_object_or_404(Group, slug=slug)
    context = {
        'group': group,
        'page_obj': (pagination(Post.objects.select_related('group').all(),
                                request))
    }
    return render(request, 'posts/group_list.html', context)


def profile(request, username):
    """Профиль пользователя."""
    author = get_object_or_404(User, username=username)
    following = (
        request.user.is_authenticated and author.following.filter(
            user=request.user).exists()
    )
    profile = author
    context = {
        'author': author,
        'page_obj': pagination(author.posts.all(), request),
        'following': following,
        'profile': profile
    }
    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    """Станица поста с информацией."""
    post_user = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST or None)
    comments = post_user.comments.all()
    context = {
        'post': post_user,
        'form': form,
        'comments': comments
    }
    return render(request, 'posts/post_detail.html', context)


@login_required
def post_create(request):
    """Добавление поста."""
    form = PostForm(request.POST or None, files=request.FILES or None)
    if form.is_valid():
        form = form.save(commit=False)
        form.author = request.user
        form.save()
        return redirect('posts:profile', request.user)
    return render(request, 'posts/create_post.html', {'form': form})


@login_required
def post_edit(request, post_id):
    """Редактирование поста."""
    post = get_object_or_404(Post, id=post_id)
    if request.user != post.author:
        return redirect('posts:post_detail', post_id=post.pk)
    form = PostForm(
        request.POST or None, files=request.FILES or None, instance=post
    )
    if form.is_valid():
        form.save()
        return redirect('posts:post_detail', post_id=post.pk)
    context = {
        'form': form,
        'is_edit': True,
    }
    return render(request, 'posts/create_post.html', context)


def page_not_found(request):
    """Станица 404"""
    return render(
        request, 'posts/404.html', {'path': request.path}, status=404
    )


@login_required
def add_comment(request, post_id):
    """Добавление комментария"""
    form = CommentForm(request.POST or None)
    post = get_object_or_404(Post, id=post_id)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    """Текущие подписки."""
    post_list = Post.objects.filter(author__following__user=request.user)
    paginator = Paginator(post_list, 20)
    page_namber = request.GET.get('page_obj')
    page = paginator.get_page(page_namber)
    context = {'page_obj': page}
    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    """Подписка."""
    author = get_object_or_404(User, username=username)
    if request.user != author:
        Follow.objects.get_or_create(user=request.user, author=author)
    return redirect(reverse('posts:profile', args=[username]))


@login_required
def profile_unfollow(request, username):
    """Отписка."""
    author = get_object_or_404(User, username=username)
    Follow.objects.filter(user=request.user, author=author).delete()
    return redirect('posts:profile', username=author)
