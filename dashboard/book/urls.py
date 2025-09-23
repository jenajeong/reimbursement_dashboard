from rest_framework.routers import DefaultRouter
from django.urls import path, include

from .views import BookListView, BookDetailView

router = DefaultRouter()

urlpatterns = [
    path('books/', BookListView.as_view(), name='book-list'),  
    path('books/<int:pk>/', BookDetailView.as_view(), name='book-detail'),
]