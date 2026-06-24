"""Views for the blog application."""
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q

from .models import Post, Category, Tag, Comment, Subscriber


class PostListView(ListView):
    """List all published posts."""

    model = Post
    template_name = "blog/post_list.html"
    context_object_name = "posts"
    paginate_by = 10

    def get_queryset(self):
        return Post.objects.filter(status=Post.STATUS_PUBLISHED)


class PostDetailView(DetailView):
    """View a single post."""

    model = Post
    template_name = "blog/post_detail.html"
    context_object_name = "post"

    def get_object(self):
        obj = super().get_object()
        # Increment view count
        obj.view_count += 1
        obj.save()
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["comments"] = self.object.comments.filter(is_approved=True)
        context["related_posts"] = self.object.get_related_posts()
        return context


class CategoryPostListView(ListView):
    """List posts in a category."""

    model = Post
    template_name = "blog/category_posts.html"
    context_object_name = "posts"
    paginate_by = 10

    def get_queryset(self):
        self.category = get_object_or_404(Category, slug=self.kwargs["slug"])
        return Post.objects.filter(
            category=self.category,
            status=Post.STATUS_PUBLISHED
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["category"] = self.category
        return context


# Duplicate view - similar to CategoryPostListView
class TagPostListView(ListView):
    """List posts with a tag."""

    model = Post
    template_name = "blog/tag_posts.html"
    context_object_name = "posts"
    paginate_by = 10

    def get_queryset(self):
        self.tag = get_object_or_404(Tag, slug=self.kwargs["slug"])
        return Post.objects.filter(
            tags=self.tag,
            status=Post.STATUS_PUBLISHED
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tag"] = self.tag
        return context


def search_posts(request):
    """Search posts by title and content."""
    query = request.GET.get("q", "")
    posts = []

    if query:
        posts = Post.objects.filter(
            Q(title__icontains=query) | Q(content__icontains=query),
            status=Post.STATUS_PUBLISHED
        )

    # Manual pagination - should use Paginator class
    page = request.GET.get("page", 1)
    per_page = 10
    start = (int(page) - 1) * per_page
    end = start + per_page
    posts_page = posts[start:end]

    return render(request, "blog/search_results.html", {
        "posts": posts_page,
        "query": query,
        "total": posts.count(),
    })


def add_comment(request, slug):
    """Add a comment to a post."""
    post = get_object_or_404(Post, slug=slug)

    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        content = request.POST.get("content")

        # Missing validation
        comment = Comment.objects.create(
            post=post,
            author_name=name,
            author_email=email,
            content=content,
        )
        messages.success(request, "Comment submitted for moderation.")
        return redirect("post_detail", slug=slug)

    return redirect("post_detail", slug=slug)


def subscribe(request):
    """Subscribe to newsletter."""
    if request.method == "POST":
        email = request.POST.get("email")

        # Missing validation
        if email:
            subscriber, created = Subscriber.objects.get_or_create(email=email)
            if created:
                messages.success(request, "Successfully subscribed!")
            else:
                messages.info(request, "You are already subscribed.")
        else:
            messages.error(request, "Please provide an email address.")

    return redirect(request.META.get("HTTP_REFERER", "/"))


# TODO: Add author profile view
# FIXME: Search is slow on large datasets

def get_popular_posts():
    """Get most viewed posts."""
    return Post.objects.filter(
        status=Post.STATUS_PUBLISHED
    ).order_by("-view_count")[:5]


def get_recent_posts():
    """Get most recent posts."""
    return Post.objects.filter(
        status=Post.STATUS_PUBLISHED
    ).order_by("-created_at")[:5]


# Unused function
def old_archive_view(request, year, month):
    """Archive view - deprecated."""
    posts = Post.objects.filter(
        created_at__year=year,
        created_at__month=month,
        status=Post.STATUS_PUBLISHED
    )
    return render(request, "blog/archive.html", {"posts": posts})
