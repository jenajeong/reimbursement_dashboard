from django.shortcuts import render
from django.db.models import Q
from rest_framework import generics
from datetime import datetime, time
from rest_framework.permissions import IsAdminUser
from .models import Order
from .serializers import OrderListSerializer, OrderSerializer, AddressLookupSerializer
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .models import Customer
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.http import HttpResponse
from book.models import Book

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



# 주문 추가 페이지 렌더링 및 폼 제출 처리를 위한 뷰
def order_add_view(request):
    """
    새로운 주문 추가 페이지 렌더링 (GET) 및 POST 요청 처리 (Serializer 사용)
    """
    
    # 필요한 import가 파일 상단에 있는지 확인: 
    # from .serializers import OrderSerializer
    # from django.shortcuts import render, redirect
    
    if request.method == 'POST':
        # HTML 폼 데이터를 OrderSerializer가 기대하는 JSON/API 형식으로 변환해야 합니다.
        # OrderSerializer는 'customer', 'order_items' (리스트), 'delivery_date' 등을 기대합니다.
        
        # 1. 폼 데이터 가공 및 구조화
        try:
            # 폼에서 받은 필드들을 구조화합니다.
            # NOTE: HTML 폼은 동적 OrderItem 리스트 처리가 까다로우므로, 
            # 현재 폼 구조(단일 상품 가정)에 맞게 하나의 OrderItem 리스트로 변환합니다.

            # Customer (CustomerSerializer는 OrderSerializer 내에서 사용됨)
            customer_data = {
                'name': request.POST.get('customer_name', '').strip(),
                'contact_number': request.POST.get('contact', '').strip(),
                # address 필드를 main_address와 detail_address를 합쳐서 전달
                'address': f"{request.POST.get('address', '').strip()} {request.POST.get('address_detail', '').strip()}".strip(),
            }
            
            # OrderItem (하나의 상품만 있다고 가정)
            order_items_data = [
                {
                    # 실제 Book ID를 알 수 없으므로, 현재는 임시로 1이라고 가정하거나
                    # 폼에 숨겨진 필드로 'book' ID가 있다고 가정해야 합니다. 
                    # 여기서는 폼에 book_id 필드(name='book')가 있다고 가정하고,
                    # 이전 로직에서 사용했던 임시 Book 객체 찾기 로직을 대체합니다.
                    'book': request.POST.get('book_id', None), # 폼에 book_id 숨김 필드가 있어야 함
                    'quantity': int(request.POST.get('quantity', 0)),
                    'discount_rate': float(request.POST.get('discount_rate', 0.0)),
                    'additional_item': request.POST.get('additional_item', ''),
                    # total_price는 OrderItemSerializer의 validate/create 로직에서 계산되는 것이 이상적이나,
                    # 현재 models.py와 serializers.py 구조상 폼에서 받은 값을 사용합니다.
                    'total_price': int(request.POST.get('supply_price', 0)),
                    # additional_price는 폼에 없으므로 0으로 가정
                    'additional_price': 0,
                }
            ]
            
            # Order
            raw_data = {
                # OrderSerializer는 OrderItemSerializer를 통해 이 데이터를 받지 않고
                # OrderSerializer.create()에서 OrderItem을 처리하므로, 
                # 여기서 customer 객체 대신 ID를 보내야 하지만, 현재 HTML 폼은 신규 고객/주문입니다.
                # 이를 해결하기 위해 OrderSerializer.create() 로직을 직접 수정하거나, 
                # 별도의 Serializer를 사용해야 합니다.
                
                # DRF의 일반적인 패턴을 따르기 위해, 일단 모든 데이터를 OrderSerializer에 전달하고
                # Serializer의 create 메서드가 Customer를 생성하거나 찾도록 Serializer를 수정합니다.
                
                'customer_info_data': customer_data, # Serializer 내에서 사용할 임시 필드
                'order_date': request.POST.get('order_date'), # order_date를 받지만 auto_now_add가 우선함
                'delivery_date': request.POST.get('shipping_date'),
                'order_source': request.POST.get('order_source'),
                'delivery_method': request.POST.get('shipping_method'),
                'requests': request.POST.get('request_memo'),
                'order_items': order_items_data,
            }
            
            # 2. Serializer 초기화 및 유효성 검사
            # OrderSerializer는 Customer ID(customer)를 기대하지만, 우리는 데이터를 보내야 합니다.
            # 이 문제를 해결하기 위해, Serializer의 `create` 메서드를 오버라이드하여
            # Customer를 찾거나 생성하는 로직을 통합해야 합니다. (이전 구현과 동일)
            
            serializer = OrderSerializer(data=raw_data)
            
            if serializer.is_valid():
                # Serializer의 create() 메서드가 호출되어 주문 및 주문 상품이 생성됨
                order_instance = serializer.save() 
                
                # 성공 시 목록 페이지로 리다이렉트 (HTMX 처리)
                response = redirect('order_list')
                response['HX-Redirect'] = response.url
                return response
            else:
                # 유효성 검사 실패 시, 에러 메시지를 템플릿에 렌더링
                error_messages = serializer.errors # 에러 딕셔너리
                # 에러 메시지를 사용자에게 보여줄 수 있도록 context에 담아 렌더링
                context = {
                    'error_message': '주문 생성 실패. 입력 정보를 확인해주세요.',
                    'errors': error_messages,
                    # 사용자가 입력했던 데이터도 다시 폼에 채워줄 수 있음 (생략)
                }
                # 400 Bad Request 상태 코드로 응답
                return render(request, 'order/add_order.html', context, status=400)

        except Exception as e:
            # 예상치 못한 오류 처리
            print(f"주문 생성 중 예외 발생: {e}")
            context = {
                'error_message': '서버 오류로 인해 주문 생성에 실패했습니다.',
            }
            return render(request, 'order/add_order.html', context, status=500)

    # GET 요청: 주문 추가 폼 페이지 렌더링
    return render(request, 'order/add_order.html')

def book_search_view(request):
    """
    HTMX 요청을 받아 책을 검색하고, 결과를 HTML 조각으로 반환
    """
    query = request.GET.get('item_name', '').strip()
    books = []
    if len(query) >= 1: # 1글자 이상일 때만 검색
        books = Book.objects.filter(
            Q(title_korean__icontains=query)
        )[:10] # 검색 결과는 최대 10개로 제한

    return render(request, 'order/partials/book_search_results.html', {'books': books})

def get_customer_address(request):
    """
    HTMX 요청으로 주문자명/연락처를 받아 기존 주소를 조회하고, 모달 HTML을 반환
    """
    customer_name = request.POST.get('customer_name')
    contact = request.POST.get('contact')

    if not customer_name or not contact:
        return HttpResponse("") # 빈 값 반환

    # AddressLookupSerializer를 사용하여 주소 조회
    serializer = AddressLookupSerializer(data={
        'customer_name': customer_name,
        'contact_number': contact
    })
    
    context = { 'customer_name': customer_name }
    if serializer.is_valid():
        context['recommended_address'] = serializer.validated_data.get('recommended_address')
        
    return render(request, 'order/address_modal.html', context)
