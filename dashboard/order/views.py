from django.shortcuts import render, get_object_or_404
from .models import Order, OrderItem
from django.db.models import Q
import datetime
from django.db import models
from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Sum
from rest_framework.filters import SearchFilter
from .serializers import (
    OrderSerializer, 
    AddressLookupSerializer,
    BookSearchSerializer
)

from book.models import Book
from rest_framework.permissions import AllowAny

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
    authentication_classes = []
    permission_classes = [AllowAny]
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

def htmx_book_search(request):
    """
    [GET] /order/api/book-search/?item_name=...
    'item_name'으로 책을 검색하여 'book_search_results.html' 템플릿을 렌더링합니다.
    (JSON이 아닌 HTML 조각을 반환합니다)
    """
    
    # 1. 'add_order.html'의 <button>이 보낸 'item_name' 검색어를 받습니다.
    query = request.GET.get('item_name', '')
    
    books_queryset = [] # 기본 빈 리스트
    
    if query:
        # 2. 쿼리로 책 제목 또는 원제를 검색합니다.
        #    N+1 문제 방지를 위해 저자(authors), 가격(price_histories)을 미리 join
        books_queryset = Book.objects.filter(
            Q(title_korean__icontains=query) | 
            Q(title_original__icontains=query)
        ).prefetch_related(
            'authors',          # 'authors' M2M 필드
            'price_histories'   # 'PriceHistory' 역참조
        ).order_by('title_korean')[:10] # 10개만 자릅니다.

    # 3. book_search_results.html 템플릿을 렌더링합니다.
    context = {
        'books': books_queryset
    }
    return render(request, 'order/book_search_results.html', context)

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
        
def htmx_lookup_address_modal(request):
    """
    [POST] /order/htmx-lookup-address/
    주문자명/연락처를 받아, 'address_modal.html' 템플릿을 
    렌더링하여 HTML 조각으로 반환합니다. (HTMX 타겟용)
    """
    if request.method == 'POST':
        # 1. 시리얼라이저를 사용하여 데이터 유효성 검사 및 주소 조회
        #    (Serializer가 'contact_number'를 기대하므로 request.POST를 그대로 전달)
        serializer = AddressLookupSerializer(data=request.POST)
        
        context = {
            'customer_name': request.POST.get('customer_name'),
            'recommended_address': None
        }

        if serializer.is_valid():
            # 2. 유효성 검사를 통과하면 조회된 주소를 context에 추가
            data = serializer.validated_data
            context['recommended_address'] = data.get('recommended_address')
        
        # 3. address_modal.html 템플릿을 렌더링하여 HTML 응답
        return render(request, 'order/address_modal.html', context)
    
    # POST가 아닌 접근은 허용하지 않음
    from django.http import HttpResponseNotAllowed
    return HttpResponseNotAllowed(['POST'])

def htmx_book_search(request):
    """
    [GET] /order/api/book-search/?item_name=...
    'item_name'으로 책을 검색하여 'book_search_results.html' 템플릿을 렌더링합니다.
    """
    
    # 1. 템플릿('add_order.html')에서 보낸 검색어를 받습니다.
    query = request.GET.get('item_name', '')
    
    books_queryset = [] # 기본 빈 리스트
    
    if query:
        # 2. 쿼리로 책 제목 또는 원제를 검색합니다.
        #    (N+1 문제 방지를 위해 저자(authors), 가격(price_histories)을 미리 join)
        books_queryset = Book.objects.filter(
            Q(title_korean__icontains=query) | 
            Q(title_original__icontains=query)
        ).prefetch_related(
            'authors', 'price_histories'
        ).order_by('title_korean')[:10] # 너무 많지 않게 10개만 자릅니다.

    # 3. book_search_results.html 템플릿을 렌더링합니다.
    #    (이 템플릿은 DRF 시리얼라이저를 더 이상 사용하지 않고, 
    #     템플릿 태그로 authors, price_histories를 직접 접근하게 됩니다.)
    context = {
        'books': books_queryset
    }
    return render(request, 'order/book_search_results.html', context)

def order_detail(request, pk):
    """
    주문 상세 조회 뷰
    """
    # 1. 주문(Order) 정보를 가져옵니다.
    #    (customer 정보는 select_related로 함께 가져와 DB 효율 향상)
    order = get_object_or_404(Order.objects.select_related('customer'), pk=pk)
    
    # 2. 이 주문에 속한 모든 주문 항목(OrderItem)을 가져옵니다.
    #    (book 정보는 select_related로 함께 가져옴)
    order_items = order.order_items.all().select_related('book')
    
    # 3. 주문의 '총 합계 금액' 계산
    #    (각 OrderItem의 total_price를 모두 더함)
    grand_total = order_items.aggregate(total=Sum('total_price'))['total'] or 0

    context = {
        'order': order,
        'order_items': order_items,
        'grand_total': grand_total
    }
    
    return render(request, 'order/order_detail.html', context)