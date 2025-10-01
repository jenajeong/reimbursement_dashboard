from .views import OrderListView, OrderCreateView, OrderDetailView, order_list_view, get_customer_address, order_add_view, book_search_view
from django.urls import path

urlpatterns = [

    path('', order_list_view, name='order_list'),
    path('add/', order_add_view, name='add_order'), 

    path('api/get-address/', get_customer_address, name='get_customer_address'),
    path('api/book-search/', book_search_view, name='book_search'),

    # 주문 목록을 조회하는 URL (GET 요청)
    path('api/', OrderListView.as_view(), name='order-list'),
    # 새로운 주문을 생성하는 URL (POST 요청)
    path('api/create/', OrderCreateView.as_view(), name='order-create'),
    # 특정 주문의 상세 정보 조회, 수정 및 삭제 URL
    # <int:pk>를 사용하여 특정 주문을 식별합니다.
    path('api/<int:pk>/', OrderDetailView.as_view(), name='order-detail'),
]

