from django.shortcuts import render
from .models import Order, OrderItem
from django.db.models import Q
import datetime
from django.db import models
from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.filters import SearchFilter
from .serializers import (
    OrderSerializer, 
    AddressLookupSerializer,
    BookSearchSerializer
)

from book.models import Book

def order_list(request):
    """
    주문 목록 조회 (HTMX 기반 검색, 필터, 정렬)
    """
    
    # 1. GET 파라미터 가져오기
    search_field = request.GET.get('search_field', 'all')
    search_query = request.GET.get('search_query', '')
    start_date_str = request.GET.get('start_date', '')
    end_date_str = request.GET.get('end_date', '')
    order_source = request.GET.get('order_source', 'all')
    
    # 정렬 기준
    sort_by = request.GET.get('sort', 'order_date') # 기본 정렬: 주문일
    direction = request.GET.get('direction', 'desc') # 기본 방향: 내림차순

    # 2. 기본 QuerySet 생성
    # N+1 문제를 피하기 위해 select_related로 연관 모델을 함께 조회합니다.
    queryset = OrderItem.objects.select_related(
        'order', 
        'order__customer', 
        'book'
    ).all()

    # 3. 검색 필터링
    if search_query:
        if search_field == 'book_title':
            queryset = queryset.filter(book__title_korean__icontains=search_query)
        elif search_field == 'customer_name':
            queryset = queryset.filter(order__customer__name__icontains=search_query)
        elif search_field == 'phone':
            queryset = queryset.filter(order__customer__contact_number__icontains=search_query)
        elif search_field == 'all':
            queryset = queryset.filter(
                Q(book__title_korean__icontains=search_query) |
                Q(order__customer__name__icontains=search_query) |
                Q(order__customer__contact_number__icontains=search_query)
            )

    # 4. 날짜 필터링 (DateTimeField 기준)
    if start_date_str:
        # YYYY-MM-DD 00:00:00 부터
        start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d')
        queryset = queryset.filter(order__order_date__gte=start_date)
        
    if end_date_str:
        # YYYY-MM-DD 23:59:59.999... 까지 (다음날 00:00:00 보다 작음)
        end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d') + datetime.timedelta(days=1)
        queryset = queryset.filter(order__order_date__lt=end_date)

    # 5. 주문처 필터링
    if order_source and order_source != 'all':
        queryset = queryset.filter(order__order_source__iexact=order_source)

    # 6. 정렬 로직
    # 템플릿에서 다음 클릭 시 사용할 방향
    next_direction = 'asc' if direction == 'desc' else 'desc'
    
    # 정렬 필드 매핑
    order_by_field = 'order__order_date' # 기본값
    if sort_by == 'order_date':
        order_by_field = 'order__order_date'
    elif sort_by == 'shipping_date':
        order_by_field = 'order__delivery_date'
    elif sort_by == 'customer':
        order_by_field = 'order__customer__name'
        
    # 정렬 방향 적용
    if direction == 'desc':
        order_by_field = f'-{order_by_field}'
        
    # null 값을 가진 필드 정렬 시 (예: delivery_date) null을 마지막으로 보내기
    if sort_by == 'shipping_date':
         queryset = queryset.order_by(models.F(order_by_field).desc(nulls_last=True))
    else:
         queryset = queryset.order_by(order_by_field)


    # 7. 컨텍스트 데이터 준비
    context = {
        'order_items': queryset,
        
        # 검색/필터 값 유지를 위해 다시 전달
        'search_field': search_field,
        'search_query': search_query,
        'start_date': start_date_str,
        'end_date': end_date_str,
        'order_source': order_source,
        
        # 정렬 아이콘 및 다음 정렬 URL에 사용
        'current_sort': sort_by,
        'current_direction': direction,
        'next_direction': next_direction,
    }

    # 8. HTMX 요청 분기 처리
    if request.htmx:
        # HTMX 요청이면 테이블 본문(tbody) 부분 템플릿만 렌더링
        template_name = 'order/partials/order_table_body.html'
    else:
        # 일반 요청이면 페이지 전체 템플릿 렌더링
        template_name = 'order/order_list.html'

    return render(request, template_name, context)

def add_order(request):
    return render(request, 'order/add_order.html')

class OrderCreateAPIView(APIView):
    """
    [POST] /order/add/
    새로운 주문을 생성합니다. (요청사항 #1, #3, #4, #5, #6 처리)
    
    JSON 데이터를 받아 OrderSerializer를 통해 주문을 생성합니다.
    - 고객 정보 (customer_info_data)
    - 주문 기본 정보 (order_source, payment_method 등)
    - 주문 상품 목록 (order_items)
    """
    def post(self, request):
        serializer = OrderSerializer(data=request.data)
        if serializer.is_valid():
            # serializer의 create 메소드가 모든 것을 처리합니다.
            # (고객 생성/업데이트, 주문 생성, 가격 계산, 주문 상품 생성)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        # 유효성 검사 실패 시 (예: CustomerSerializer의 연락처 형식 오류 등)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AddressLookupAPIView(APIView):
    """
    [POST] /order/lookup-address/
    주문자명과 연락처로 기존 주소를 조회합니다. (요청사항 #7 처리)
    """
    def post(self, request):
        # AddressLookupSerializer를 사용합니다.
        serializer = AddressLookupSerializer(data=request.data)
        if serializer.is_valid():
            # validate() 메소드에서 조회된 주소가 'recommended_address'에 담겨옵니다.
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BookSearchAPIView(generics.ListAPIView):
    """
    [GET] /order/book-search/?search=...
    '책 DB'에서 상품을 검색합니다. (요청사항 #1 처리)
    """
    queryset = Book.objects.all()
    serializer_class = BookSearchSerializer
    filter_backends = [SearchFilter]
    search_fields = ['title_korean', 'title_original'] # 'title_korean' 또는 'title_original'로 검색


class AdditionalItemPriceAPIView(APIView):
    """
    [GET] /order/additional-item-price/?name=...
    추가 상품명을 기반으로 기존 가격을 조회합니다. (요청사항 #2 처리)
    """
    def get(self, request):
        item_name = request.GET.get('name')
        if not item_name:
            return Response(
                {"error": "추가 상품명('name' 쿼리 파라미터)이 필요합니다."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # 입력된 이름과 일치하는 가장 마지막 주문 항목을 찾습니다.
        last_item = OrderItem.objects.filter(additional_item=item_name).order_by('-id').first()

        if last_item:
            # 기존 가격을 반환합니다.
            return Response(
                {"name": last_item.additional_item, "price": last_item.additional_price},
                status=status.HTTP_200_OK
            )
        else:
            # 일치하는 항목이 없으면 404
            return Response(
                {"error": "일치하는 추가 상품 이력이 없습니다."},
                status=status.HTTP_404_NOT_FOUND
            )