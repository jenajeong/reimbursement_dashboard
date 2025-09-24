from .views import OrderListView, OrderCreateView, OrderDetailView
from django.urls import path

urlpatterns = [
    # 주문 목록을 조회하는 URL (GET 요청)
    path('orders/', OrderListView.as_view(), name='order-list'),
    
    # 새로운 주문을 생성하는 URL (POST 요청)
    path('orders/create/', OrderCreateView.as_view(), name='order-create'),
    
    # 특정 주문의 상세 정보 조회, 수정 및 삭제 URL
    # <int:pk>를 사용하여 특정 주문을 식별합니다.
    path('orders/<int:pk>/', OrderDetailView.as_view(), name='order-detail'),
]

