from django.shortcuts import render
from django.db.models import Q
from rest_framework import generics
from datetime import datetime, time
from rest_framework.permissions import IsAdminUser
from .models import Order
from .serializers import OrderListSerializer, OrderSerializer

class OrderListView(generics.ListAPIView):
    """
    모든 주문 목록을 조회하는 뷰입니다.
    - GET 요청: OrderListSerializer를 사용하여 주문 정보를 반환합니다.
    """
    queryset = Order.objects.all()
    serializer_class = OrderListSerializer
    permission_classes = [IsAdminUser]


class OrderCreateView(generics.CreateAPIView):
    """
    새로운 주문을 생성하는 뷰입니다.
    - POST 요청: OrderSerializer를 사용하여 주문 데이터를 생성합니다.
    """
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAdminUser]


class OrderDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    특정 주문의 상세 정보 조회, 수정 및 삭제를 위한 뷰입니다.
    - GET 요청: OrderSerializer를 사용하여 상세 정보를 조회합니다.
    - PUT/PATCH 요청: 주문 정보를 수정합니다.
    - DELETE 요청: 주문을 삭제합니다.
    """
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAdminUser]

def order_list_view(request):
   # 정렬 기능은 이전과 동일
    sort_by = request.GET.get('sort', 'order_date')
    direction = request.GET.get('direction', 'desc')
    db_sort = f'-{sort_by}' if direction == 'desc' else sort_by
    
    # 검색 및 필터링 기능
    search_query = request.GET.get('search_query', '')
    search_field = request.GET.get('search_field', 'book_title')
    
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    order_source = request.GET.get('order_source')

    orders = Order.objects.all().order_by(db_sort)
    
    # 검색어가 있을 경우
    if search_query:
        if search_field == 'book_title':
            orders = orders.filter(
                order_items__book__title_korean__icontains=search_query
            ).distinct()
        elif search_field == 'customer_name': # 주문자 이름 검색
            orders = orders.filter(
                customer__name__icontains=search_query
            ).distinct()
        elif search_field == 'phone': # 휴대폰 번호 검색
            orders = orders.filter(
                customer__contact_number__icontains=search_query
            ).distinct()
        elif search_field == 'all': # 전체 필드 검색 (예시)
            orders = orders.filter(
                Q(order_items__book__title_korean__icontains=search_query) |
                Q(customer__name__icontains=search_query) |
                Q(customer__contact_number__icontains=search_query)
            ).distinct()

    # 주문일 기간 필터링
    if start_date and end_date:
        # 시간대를 고려하여 하루의 시작과 끝을 설정
        start_datetime = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_datetime = datetime.strptime(end_date, '%Y-%m-%d').date()
        orders = orders.filter(order_date__date__range=(start_datetime, end_datetime))
    
    # 주문처 필터링
    if order_source and order_source != 'all':
        orders = orders.filter(order_source=order_source)

    context = {
        'orders': orders,
        'current_sort': sort_by,
        'next_direction': 'asc' if direction == 'desc' else 'desc',
        'search_query': search_query,
        'search_field': search_field,
    }

    if request.headers.get('HX-Request'):
        return render(request, 'order/partials/order_table_body.html', context)
    
    return render(request, 'order/order_list.html', context)
