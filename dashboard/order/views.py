from django.shortcuts import render, get_object_or_404
from .models import Order, OrderItem
from django.db.models import Q
import datetime
from django.db import models
from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Sum, Count
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
    [수정] OrderItem 기준이 아닌 Order 기준으로 조회
    """
    
    # 1. GET 파라미터 가져오기
    search_field = request.GET.get('search_field', 'all')
    search_query = request.GET.get('search_query', '')
    start_date_str = request.GET.get('start_date', '')
    end_date_str = request.GET.get('end_date', '')
    order_source = request.GET.get('order_source', 'all')
    
    # ▼▼▼ [이 부분 추가] ▼▼▼
    payment_status = request.GET.get('payment_status', 'all')
    # ▲▲▲ [여기까지 추가] ▲▲▲
    
    sort_by = request.GET.get('sort', 'order_date') 
    direction = request.GET.get('direction', 'desc')

    # 2. 기본 QuerySet 생성
    queryset = Order.objects.annotate(
        total_quantity=Sum('order_items__quantity'),
        total_types=Count('order_items__book', distinct=True)
    ).select_related('customer').prefetch_related(
        'order_items', 'order_items__book'
    )

    # [수정] 상품 없는 "빈 주문" 제외
    queryset = queryset.filter(total_types__gt=0)
    
    # 3. 검색 필터링
    if search_query:
        if search_field == 'book_title':
            queryset = queryset.filter(order_items__book__title_korean__icontains=search_query)
        elif search_field == 'customer_name':
            queryset = queryset.filter(customer__name__icontains=search_query)
        elif search_field == 'phone':
            queryset = queryset.filter(customer__contact_number__icontains=search_query)
        elif search_field == 'all':
            queryset = queryset.filter(
                Q(order_items__book__title_korean__icontains=search_query) |
                Q(customer__name__icontains=search_query) |
                Q(customer__contact_number__icontains=search_query)
            )

    # 4. 날짜 필터링
    if start_date_str:
        start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d')
        queryset = queryset.filter(order_date__gte=start_date)
        
    if end_date_str:
        end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d') + datetime.timedelta(days=1)
        queryset = queryset.filter(order_date__lt=end_date)

    # 5. 주문처 필터링
    if order_source and order_source != 'all':
        queryset = queryset.filter(order_source__iexact=order_source)

    # ▼▼▼ [이 부분 추가] ▼▼▼
    # 6. 결제 상태 필터링
    if payment_status == 'paid':
        queryset = queryset.filter(payment_date__isnull=False) # 결제일이 있는 건
    elif payment_status == 'unpaid':
        queryset = queryset.filter(payment_date__isnull=True)  # 결제일이 없는(null) 건
    # 'all' (default)는 아무것도 하지 않음
    # ▲▲▲ [여기까지 추가] ▲▲▲

    # 7. 정렬 로직 (기존 6번)
    next_direction = 'asc' if direction == 'desc' else 'desc'
    
    order_by_field = 'order_date' 
    if sort_by == 'order_date':
        order_by_field = 'order_date'
    elif sort_by == 'shipping_date':
        order_by_field = 'delivery_date'
    elif sort_by == 'customer':
        order_by_field = 'customer__name'
        
    if direction == 'desc':
        order_by_field = f'-{order_by_field}'
        
    if sort_by == 'shipping_date':
         f_object = models.F(order_by_field.replace('-', ''))
         if direction == 'desc':
             queryset = queryset.order_by(f_object.desc(nulls_last=True))
         else:
             queryset = queryset.order_by(f_object.asc(nulls_last=True))
    else:
         queryset = queryset.order_by(order_by_field)

    if search_query and (search_field == 'book_title' or search_field == 'all'):
        queryset = queryset.distinct()

    # 8. 컨텍스트 데이터 준비 (기존 7번)
    context = {
        'orders': queryset,
        'search_field': search_field,
        'search_query': search_query,
        'start_date': start_date_str,
        'end_date': end_date_str,
        'order_source': order_source,
        
        'payment_status': payment_status, 
        
        'current_sort': sort_by,
        'current_direction': direction,
        'next_direction': next_direction,
    }

    # 9. HTMX 요청 분기 처리 (기존 8번)
    if request.htmx:
        template_name = 'order/partials/order_table_body.html'
    else:
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

class OrderUpdateAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def patch(self, request, pk):
        try:
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return Response({"error": "주문을 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)
            
        # OrderSerializer의 update 메소드를 호출
        serializer = OrderSerializer(order, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
def order_edit(request, pk):
    """
    주문 수정 페이지 뷰
    order_detail과 거의 동일하지만, edit_order.html을 렌더링합니다.
    """
    order = get_object_or_404(Order.objects.select_related('customer'), pk=pk)
    
    # [수정] order_items 변수명을 order.order_items.all()로 템플릿에서 직접 사용
    # order_items = order.order_items.all().select_related('book')
    
    # [수정] 총 합계 금액은 템플릿에서 계산하거나 JS에서 계산
    # grand_total = order_items.aggregate(total=Sum('total_price'))['total'] or 0

    context = {
        'order': order,
        # 'order_items': order_items, # 템플릿에서 order.order_items.all 사용
        # 'grand_total': grand_total
    }
    
    return render(request, 'order/edit_order.html', context)