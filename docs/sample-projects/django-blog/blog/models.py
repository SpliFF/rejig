"""Django models for the blog application."""
from django.db import models
from django.contrib.auth.models import User


class Category(models.Model):
    """Blog post category."""

    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "blog_category"
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class Tag(models.Model):
    """Blog post tag."""

    name = models.CharField(max_length=50)
    slug = models.SlugField(unique=True)

    class Meta:
        db_table = "blog_tag"

    def __str__(self):
        return self.name


class Post(models.Model):
    """Blog post model."""

    STATUS_DRAFT = "draft"
    STATUS_PUBLISHED = "published"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_PUBLISHED, "Published"),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    content = models.TextField()
    excerpt = models.TextField(blank=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    tags = models.ManyToManyField(Tag, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    view_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "blog_post"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return f"/posts/{self.slug}/"

    # Duplicate logic - should be a manager method
    def get_related_posts(self):
        return Post.objects.filter(
            category=self.category,
            status=self.STATUS_PUBLISHED
        ).exclude(id=self.id)[:5]


class Comment(models.Model):
    """Comment on a blog post."""

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    author_name = models.CharField(max_length=100)
    author_email = models.EmailField()
    content = models.TextField()
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "blog_comment"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Comment by {self.author_name} on {self.post.title}"


# Duplicate model - should be merged with Comment
class Reply(models.Model):
    """Reply to a comment."""

    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name="replies")
    author_name = models.CharField(max_length=100)
    author_email = models.EmailField()
    content = models.TextField()
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "blog_reply"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Reply by {self.author_name}"


class Subscriber(models.Model):
    """Newsletter subscriber."""

    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "blog_subscriber"

    def __str__(self):
        return self.email
