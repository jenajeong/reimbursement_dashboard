from rest_framework.routers import DefaultRouter
from django.urls import path, include

from .views import book_list_view, load_category2, add_book_view #, search_composers_view

router = DefaultRouter()

urlpatterns = [
    path('', book_list_view, name='book_list'),
    path('add/', add_book_view, name='add_book'),
    path('ajax/load-category2/', load_category2, name='ajax_load_category2'),
    # path('ajax/search-composers/', search_composers_view, name='ajax_search_composers'),
]