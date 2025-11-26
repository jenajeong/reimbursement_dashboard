from django.shortcuts import render
from django.db import models
from django.db.models import Sum
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .permissions import IsManagerOrComposer
from .serializers import ReimbursementListSerializer 
from rest_framework.authentication import SessionAuthentication, TokenAuthentication, BasicAuthentication
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.db.models import Sum, Q
from datetime import date

# 외부 모델 임포트 (실제 경로에 맞게 수정 필요)
from book.models import Book

# ===============================================
# 정산 목록 API View
# ===============================================


def ReimbursementBaseView(request):
    """
    정산 목록 페이지의 기본 레이아웃 (reimbursement_list.html)을 렌더링합니다.
    (최초 페이지 접근 시 사용)
    """
    if not request.user.is_authenticated:
        # 인증되지 않았다면 로그인 페이지 등으로 리다이렉트
        # 실제 로그인 URL 패턴으로 변경 필요
        return HttpResponseRedirect(reverse('login')) 
    
    context = {
        # 템플릿에서 사용할 기본 변수들 (available_years, all_composers 등)
        'request': request, 
        # ... (필터링에 필요한 context 변수 추가)
    }
    
    # 전체 페이지 템플릿을 렌더링합니다.
    return render(request, 'reimbursement/reimbursement_list.html', context)

class ReimbursementListView(generics.ListAPIView):
    """
    관리자 및 작곡가를 위한 정산 목록 조회 API
    권한에 따라 데이터 필터링 및 필드 구성이 달라집니다.
    """
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    serializer_class = ReimbursementListSerializer
    permission_classes = [IsAuthenticated, IsManagerOrComposer]

    def get_queryset(self):
        # 💡 수정 1: 모든 책을 쿼리셋의 시작점으로 사용합니다.
        queryset = Book.objects.all()
        user = self.request.user
        
        # --- 1. 작곡가 필터링 (Composer View) ---
        if not user.is_staff: 
            try:
                current_composer = user.composer_profile 
            except AttributeError:
                return Book.objects.none()
            
            # 일반 작곡가는 본인이 참여한 책만 필터링 (이 필터는 유지)
            queryset = queryset.filter(composers=current_composer) 

        # --- 2. 기본 데이터 (전체 누적) 어노테이션 ---
        # 판매 기록이 없는 책은 NULL 값을 가지게 됩니다.
        queryset = queryset.annotate(
            total_cumulative_sales=Sum('sale_records__quantity_sold'),
            total_cumulative_revenue=Sum('sale_records__total_revenue'),
        ).distinct()

        return queryset

    def list(self, request, *args, **kwargs):
        # get_queryset에서 기본 집계된 쿼리셋을 가져옵니다.
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True, context={'request': request})
        
        # Serializer 결과에 필요한 추가 데이터를 붙여 응답합니다.
        return Response(serializer.data)

def ReimbursementHTMXListView(request):
    """
    HTMX 요청을 처리하고 HTML 조각(fragment)을 반환하는 뷰
    - 책 제목/작곡가 검색, 연도, 정산 상태 필터링을 지원합니다.
    """
    # 1. 권한 확인 
    if not request.user.is_authenticated:
        return render(request, '401.html', status=401)
    
    queryset = Book.objects.all()
    user = request.user

    # --- 2. 쿼리 파라미터 가져오기 ---
    search_query = request.GET.get('search_query', '').strip()
    search_field = request.GET.get('search_field', 'book_title')
    selected_year = request.GET.get('year', 'all')
    selected_status = request.GET.get('status', 'all')


    # --- 3. 작곡가 필터링 (Composer View) ---
    # 일반 작곡가일 경우, 자신이 참여한 책만 필터링합니다.
    if not user.is_staff:
        try:
             current_composer = user.composer_profile 
             queryset = queryset.filter(composers=current_composer)
        except AttributeError:
             queryset = Book.objects.none()

    # --- 4. 검색 필터링 로직 (책 제목 / 작곡가) ---
    if search_query:
        query = Q()
        if search_field == 'book_title':
            # 책 제목 검색 (한국어 또는 원본 제목)
            query = Q(title_korean__icontains=search_query) | Q(title_original__icontains=search_query)
        
        elif search_field == 'composer_name':
            # 작곡가 이름 검색
            query = Q(composers__name__icontains=search_query)
        
        queryset = queryset.filter(query).distinct()
    
    
    # --- 5. 연도 필터링 (RoyaltySettlement 기록의 연도 기준) ---
    if selected_year != 'all' and selected_year.isdigit():
        # settlements는 Book 모델과 RoyaltySettlement 모델 간의 related_name을 가정합니다.
        queryset = queryset.filter(settlements__threshold_met_year=selected_year).distinct()

    # --- 6. 정산 상태 필터링 (RoyaltySettlement 기록의 is_paid 상태 기준) ---
    if selected_status != 'all':
        # 'paid'면 True, 'pending'이면 False를 기준으로 필터링합니다.
        is_paid_status = True if selected_status == 'paid' else False
        
        # is_paid 필터링 적용 (settlements는 RoyaltySettlement 모델의 related_name)
        queryset = queryset.filter(settlements__is_paid=is_paid_status).distinct()
    
    
    # --- 7. 데이터 집계 및 어노테이션 ---
    # Serializer가 사용하는 필드를 annotate로 추가합니다.
    queryset = queryset.annotate(
        total_cumulative_sales=Sum('sale_records__quantity_sold'),
        total_cumulative_revenue=Sum('sale_records__total_revenue'),
    ).distinct()
    
    # 8. Serializer를 사용하여 데이터를 HTML context로 변환
    serializer = ReimbursementListSerializer(queryset, many=True, context={'request': request})
    reimbursement_items = serializer.data
    
    # 9. Context 생성
    context = {
        'reimbursement_items': reimbursement_items,
        'request': request,
        
        # 필터링 후에도 상태가 유지되도록 context에 전달
        'search_query': search_query, 
        'search_field': search_field,
        'selected_year': selected_year,
        'selected_status': selected_status,
        
        # 템플릿의 <select> 옵션 구성을 위해 사용 가능한 연도 목록 전달 (예: 현재 연도부터 5년 전까지)
        'available_years': list(range(date.today().year, date.today().year - 5, -1)),
    }
    
    # 10. HTML Fragment를 렌더링하여 반환
    return render(request, 'reimbursement/partials/reimbursement_table_body.html', context)

def reimbursement_detail_dummy_view(request, book_id):
    """
    reimbursement_detail URL 패턴 해결을 위한 임시 뷰.
    추후 상세 페이지 구현 시 이 함수를 대체해야 합니다.
    """
    return HttpResponse(f"<h1>정산 상세 페이지 (Book ID: {book_id}) - 구현 예정</h1>")

def settlement_toggle_dummy_view(request, book_id):
    """
    settlement_toggle URL 패턴 해결을 위한 임시 뷰.
    """
    # HTMX가 POST 요청을 보내므로, CSRF 방지 목적으로 Dummy Response를 보냅니다.
    return HttpResponse(f"<td>정산 완료 처리됨 (Book ID: {book_id})</td>")