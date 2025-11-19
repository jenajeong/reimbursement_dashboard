from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import (
    book_list_view, 
    book_detail_view,
    add_book_page_view,
    book_edit_page_view,
    ajax_search_category2,
    ajax_search_books,
    ajax_search_authors,
    ajax_search_category1,
    ajax_search_category2 ,
    ajax_search_book_titles,
    batch_price_update_view,
    ajax_check_composer
)
from .api_views import BookViewSet, batch_price_update_api

router = DefaultRouter()
router.register(r'api/books', BookViewSet, basename='book-api')
urlpatterns = [
    path('', book_list_view, name='book_list'),
    path('<int:pk>/', book_detail_view, name='book_detail'), 
    path('add/', add_book_page_view, name='add_book_page'),
    path('<int:pk>/edit/', book_edit_page_view, name='book_edit_page'),
    path('ajax-load-category2/', ajax_search_category2, name='ajax_load_category2'), 
    path('ajax-search-category1/', ajax_search_category1, name='ajax_search_category1'),
    path('ajax-search-category2/', ajax_search_category2, name='ajax_search_category2'),
    path('ajax-search-books/', ajax_search_books, name='ajax_search_books'),
    path('ajax-search-authors/', ajax_search_authors, name='ajax_search_authors'),
    path('ajax-search-book-titles/', ajax_search_book_titles, name='ajax_search_book_titles'),
    path('batch-price-update/', batch_price_update_view, name='batch_price_update'),
    path('ajax-check-composer/', ajax_check_composer, name='ajax_check_composer'),
    path('', include(router.urls)),
    path('api/batch-price-update/', batch_price_update_api, name='batch_price_update_api'),
]