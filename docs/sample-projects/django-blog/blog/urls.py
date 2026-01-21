"""URL configuration for the blog application."""
from django.urls import path
from . import views

urlpatterns = [
    path("", views.PostListView.as_view(), name="post_list"),
    path("post/<slug:slug>/", views.PostDetailView.as_view(), name="post_detail"),
    path("post/<slug:slug>/comment/", views.add_comment, name="add_comment"),
    path("category/<slug:slug>/", views.CategoryPostListView.as_view(), name="category_posts"),
    path("tag/<slug:slug>/", views.TagPostListView.as_view(), name="tag_posts"),
    path("search/", views.search_posts, name="search"),
    path("subscribe/", views.subscribe, name="subscribe"),
]
