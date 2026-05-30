from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import CommentForm, PostForm, RegistrationForm, UserProfileForm
from .models import Category, Comment, Post

User = get_user_model()

POSTS_PER_PAGE = 10


def get_published_posts(queryset=None):
    if queryset is None:
        queryset = Post.objects.all()
    return queryset.filter(
        is_published=True,
        pub_date__lte=timezone.now(),
        category__is_published=True,
    ).select_related('category', 'location', 'author')


def annotate_comment_count(queryset):
    return queryset.annotate(
        comment_count=Count('comments'),
    ).order_by('-pub_date')


def paginate_posts(request, queryset):
    paginator = Paginator(queryset, POSTS_PER_PAGE)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)


def get_post_for_detail(post_id, user):
    queryset = Post.objects.select_related('category', 'location', 'author')
    if user.is_authenticated:
        post = queryset.filter(pk=post_id, author=user).first()
        if post is not None:
            return post
    return get_object_or_404(get_published_posts(), pk=post_id)


def index(request):
    post_list = annotate_comment_count(get_published_posts())
    page_obj = paginate_posts(request, post_list)
    return render(request, 'blog/index.html', {'page_obj': page_obj})


def post_detail(request, id):
    post = get_post_for_detail(id, request.user)
    comments = post.comments.select_related('author')
    context = {
        'post': post,
        'comments': comments,
        'form': CommentForm(),
    }
    return render(request, 'blog/detail.html', context)


def category_posts(request, category_slug):
    category = get_object_or_404(
        Category,
        slug=category_slug,
        is_published=True,
    )
    post_list = annotate_comment_count(
        get_published_posts(category.posts.all()),
    )
    page_obj = paginate_posts(request, post_list)
    return render(
        request,
        'blog/category.html',
        {'category': category, 'page_obj': page_obj},
    )


@login_required
def own_profile(request):
    return redirect('blog:profile', username=request.user.username)


def profile(request, username):
    profile_user = get_object_or_404(User, username=username)
    if request.user == profile_user:
        post_list = Post.objects.filter(author=profile_user).order_by('-pub_date')
    else:
        post_list = get_published_posts().filter(author=profile_user)
    post_list = annotate_comment_count(
        post_list.select_related('category', 'location', 'author'),
    )
    page_obj = paginate_posts(request, post_list)
    return render(
        request,
        'blog/profile.html',
        {'profile': profile_user, 'page_obj': page_obj},
    )


def registration(request):
    form = RegistrationForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect('login')
    return render(
        request,
        'registration/registration_form.html',
        {'form': form},
    )


@login_required
def edit_profile(request):
    form = UserProfileForm(
        request.POST or None,
        instance=request.user,
    )
    if form.is_valid():
        form.save()
        return redirect('blog:profile', username=request.user.username)
    return render(request, 'blog/user.html', {'form': form})


@login_required
def create_post(request):
    form = PostForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('blog:profile', username=request.user.username)
    return render(request, 'blog/create.html', {'form': form})


@login_required
def edit_post(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:
        return redirect('blog:post_detail', id=post_id)
    form = PostForm(
        request.POST or None,
        request.FILES or None,
        instance=post,
    )
    if form.is_valid():
        form.save()
        return redirect('blog:post_detail', id=post_id)
    return render(request, 'blog/create.html', {'form': form})


@login_required
def delete_post(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:
        return redirect('blog:post_detail', id=post_id)
    form = PostForm(instance=post)
    if request.method == 'POST':
        post.delete()
        return redirect('blog:index')
    return render(request, 'blog/create.html', {'form': form})


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(get_published_posts(), pk=post_id)
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('blog:post_detail', id=post_id)


@login_required
def edit_comment(request, post_id, comment_id):
    post = get_object_or_404(Post, pk=post_id)
    comment = get_object_or_404(Comment, pk=comment_id, post=post)
    if comment.author != request.user:
        return redirect('blog:post_detail', id=post_id)
    form = CommentForm(request.POST or None, instance=comment)
    if form.is_valid():
        form.save()
        return redirect('blog:post_detail', id=post_id)
    return render(
        request,
        'blog/comment.html',
        {'form': form, 'comment': comment},
    )


@login_required
def delete_comment(request, post_id, comment_id):
    post = get_object_or_404(Post, pk=post_id)
    comment = get_object_or_404(Comment, pk=comment_id, post=post)
    if comment.author != request.user:
        return redirect('blog:post_detail', id=post_id)
    if request.method == 'POST':
        comment.delete()
        return redirect('blog:post_detail', id=post_id)
    return render(request, 'blog/comment.html', {'comment': comment})
