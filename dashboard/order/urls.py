from . import views
from django.urls import path

urlpatterns = [

    path('', views.order_list, name='order_list'),
# --- [주문 추가 API 엔드포인트] ---
    
    # 1. 최종 주문 생성 API (POST)
    path('api/add/', views.OrderCreateAPIView.as_view(), name='api_order_add'),
    
    # 2. 고객 주소 조회 API (POST)
    path('api/lookup-address/', views.AddressLookupAPIView.as_view(), name='api_order_lookup_address'),
    
    # 3. 책 검색 API (GET)
    path('api/book-search/', views.BookSearchAPIView.as_view(), name='api_order_book_search'),
    
    # 4. 추가 상품 가격 조회 API (GET)
    path('api/additional-item-price/', views.AdditionalItemPriceAPIView.as_view(), name='api_order_additional_item_price'),

    path('add/', views.add_order, name='add_order'),
    path('htmx-lookup-address/', views.htmx_lookup_address_modal, name='htmx_lookup_address_modal'),
]

