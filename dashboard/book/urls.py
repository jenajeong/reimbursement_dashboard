from rest_framework.routers import DefaultRouter
from django.urls import path, include

from .views import BookListView, BookDetailView, AuthorListView, AuthorCreateView, AuthorDetailView

router = DefaultRouter()

urlpatterns = [
    path('books/', BookListView.as_view(), name='book-list'),  
    path('books/<int:pk>/', BookDetailView.as_view(), name='book-detail'),
    path('authors/', AuthorListView.as_view(), name='author-list'),
    path('authors/create/', AuthorCreateView.as_view(), name='author-create'),
    path('authors/<int:pk>/', AuthorDetailView.as_view(), name='author-detail'),
]