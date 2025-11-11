from django.shortcuts import render, redirect, get_object_or_404 # 👈 [수정] get_object_or_404 추가
from .models import Book, Author, PriceHistory, ComposerWork, Composer 
import datetime
from django.db.models import Q, F, Case, When, Value, IntegerField
from django.http import JsonResponse
from django.db.models import Subquery, OuterRef
from django.utils import timezone # 👈 [신규] 임포트 (batch_price_update_api용)
from django.db import transaction # 👈 [신규] 임포트 (batch_price_update_api용)

def book_list_view(request):
    """
    책 목록 페이지의 메인 뷰.
    """
    
    # --- 최신 가격을 가져오기 위한 Subquery 정의 ---
    latest_price_sq = PriceHistory.objects.filter(
        book=OuterRef('pk'), 
        is_latest=True
    ).values('price')[:1] # is_latest=True인 가격 1개만 선택

    # --- Book 쿼리셋에 Subquery를 annotate로 추가 ---
    books = Book.objects.prefetch_related('authors').annotate(
        latest_price=Subquery(latest_price_sq) # 'latest_price'라는 가상 필드 생성
    ).order_by('-pk')

    # 1. GET 파라미터 가져오기
    search_query = request.GET.get('search_query', '')
    category1 = request.GET.get('category1', '')
    category2 = request.GET.get('category2', '')

    # 2. 텍스트 검색 (책 제목 또는 저자명)
    if search_query:
        books = books.filter(
            Q(title_korean__icontains=search_query) |
            Q(authors__name__icontains=search_query)
        ).distinct()

    # 3. 카테고리 필터링
    if category1:
        books = books.filter(category1=category1)
    if category2:
        books = books.filter(category2=category2)

    # --- 템플릿에 전달할 Context 데이터 ---
    context = {
        'books': books,
        'categories1': Book.objects.exclude(category1__isnull=True).exclude(category1__exact='')
                          .values_list('category1', flat=True).distinct().order_by('category1'),
        'search_query': search_query,
        'selected_category1': category1,
        'selected_category2': category2,
    }

    # HTMX 요청인 경우, 테이블 본문 부분만 렌더링
    if request.htmx:
        return render(request, 'book/partials/book_table_body.html', context)

    # 일반적인 첫 페이지 로드
    return render(request, 'book/book_list.html', context)

# --- [신규] 책 상세조회 뷰 ---
def book_detail_view(request, pk):
    """
    pk에 해당하는 책의 상세 정보를 조회하는 뷰
    """
    # prefetch_related를 사용하여 M2M 및 역방향 FK 데이터를 효율적으로 미리 가져옵니다.
    # 👇 이제 get_object_or_404 함수가 정의되었으므로 정상 작동합니다.
    book = get_object_or_404(
        Book.objects.prefetch_related(
            'authors', # 저자
            'price_histories', # 가격 이력 (모두)
            'composerwork_set__composer' # 작곡가 작업(ComposerWork) 및 연결된 작곡가(Composer)
        ), 
        pk=pk
    )
    
    context = {
        'book': book
    }
    return render(request, 'book/book_detail.html', context)


# --- [신규] 책 수정 페이지 뷰 ---
def book_edit_page_view(request, pk):
    """
    '책 수정' HTML 페이지만 렌더링하는 뷰
    기존 책 데이터를 템플릿에 전달하여 폼을 미리 채웁니다.
    """
    book = get_object_or_404(
        Book.objects.prefetch_related(
            'authors',
            'composerwork_set__composer'
        ), 
        pk=pk
    )
    
    # 현재 최신 가격 조회
    current_price_obj = book.price_histories.filter(is_latest=True).first()
    
    # 이 책에 연결된 작곡가 작업(ComposerWork) 목록 조회
    composer_works = book.composerwork_set.all().order_by('pk')
    
    context = {
        'book': book, # 책 기본 정보 (title, category 등)
        'current_price': current_price_obj.price if current_price_obj else 0,
        'book_authors': list(book.authors.all().values('name', 'name')), # Select2 pre-fill용 (id, text)
        'composer_works': composer_works,
    }
    # '책 추가' 템플릿과 다른, '수정' 전용 템플릿을 렌더링
    return render(request, 'book/book_edit_page.html', context)


def add_book_page_view(request):
    """
    [신규] '책 추가' HTML 페이지만 렌더링하는 뷰
    """
    context = {
    }
    return render(request, 'book/add_book_page.html', context)


# --- [신규] 가격 일괄 변동 페이지 (GET) 뷰 ---
def batch_price_update_view(request):
    """
    '가격 일괄 변동' HTML 페이지만 렌더링하는 뷰
    GET 파라미터로 받은 'ids'를 템플릿으로 전달합니다.
    """
    # 1. URL 쿼리 파라미터에서 'ids' 문자열(예: "1,3,5")을 가져옵니다.
    ids_str = request.GET.get('ids', '')
    
    # 2. 쉼표로 구분된 ID 문자열을 숫자 리스트로 변환합니다.
    book_ids = [int(id_val) for id_val in ids_str.split(',') if id_val.isdigit()]

    if not book_ids:
        books = Book.objects.none()
    else:
        # 3. 해당 ID의 책 목록을 조회 (템플릿에서 확인용으로 표시)
        books = Book.objects.filter(pk__in=book_ids)
    
    context = {
        'selected_books': books, # 선택된 책 목록 (확인용)
        'book_ids_str': ids_str    # API로 다시 보낼 ID 문자열
    }
    return render(request, 'book/batch_price_update.html', context)


# --- AJAX 뷰 (HTMX / Select2) ---
def ajax_load_category2(request):
    """
    카테고리1 값에 따라 카테고리2 옵션을 반환하는 HTMX용 뷰
    """
    category1_query = request.GET.get('category1', '')
    categories2 = []
    if category1_query:
            # 'category1' 필드가 사용자가 입력한 텍스트로 "시작"하는 책들을 찾음
            categories2 = Book.objects.filter(category1__istartswith=category1_query)\
                                    .values_list('category2', flat=True)\
                                    .distinct().order_by('category2')
    
    # book_list.html의 필터용 partial (전체 옵션 포함)
    # add_book_page.html의 폼용 partial (placeholder만 포함)
    # 요청 경로(referer) 등에 따라 다른 템플릿을 렌더링할 수 있으나,
    # 여기서는 book_list.html용 HTMX만 가정하고 category2_options.html을 사용
    # (add_book_page.html은 Select2 AJAX를 사용하므로 이 뷰를 호출하지 않음)
    return render(request, 'book/partials/category2_options.html', {
            'categories2': categories2,
            'selected_category2': request.GET.get('category2', '')
        })

def ajax_search_category1(request):
    """
    Category1 필드용 Select2 AJAX 검색 뷰
    """
    term = request.GET.get('term', '')
    
    categories = []
    if term:
        categories = Book.objects.filter(
            category1__icontains=term
        ).values_list('category1', flat=True).distinct().order_by('category1')[:10]
    
    results = [{"id": cat, "text": cat} for cat in categories]
    
    return JsonResponse({"results": results})


def ajax_search_category2(request):
    """
    Category2 필드용 Select2 AJAX 검색 뷰
    """
    term = request.GET.get('term', '')
    category1 = request.GET.get('category1', '') 
    
    qs = Book.objects.all()
    if term:
        qs = qs.filter(category2__icontains=term)
    
    if category1:
        qs = qs.annotate(
            is_primary=Case(
                When(category1=category1, then=Value(1)),
                default=Value(0),
                output_field=IntegerField()
            )
        ).order_by('-is_primary', 'category2')
    else:
        qs = qs.order_by('category2')
        
    distinct_categories = qs.values_list('category2', flat=True).distinct()[:10]
    
    results = [{"id": cat, "text": cat} for cat in distinct_categories]
    
    return JsonResponse({"results": results})

def ajax_search_books(request):
    """
    [현재 사용되지 않음] 책 제목 실시간 검색 (HTMX)
    (add_book_page.html이 Select2를 사용하도록 변경됨)
    """
    query = request.GET.get('title_korean', '') 
    books = []
    if query and len(query) > 1: 
        books = Book.objects.filter(
            Q(title_korean__icontains=query) | 
            Q(title_original__icontains=query)
        ).distinct()[:5]
    context = {'books': books}
    return render(request, 'book/partials/book_search_results.html', context)

def ajax_search_authors(request):
    """
    [유지] 저자 실시간 검색 (Select2 AJAX)
    """
    query = request.GET.get('term', '') 
    authors = Author.objects.filter(name__icontains=query)
    
    results = [
        {
            "id": author.name, # [수정] JS가 ID 대신 이름을 사용하므로 text와 동일하게
            "text": author.name 
        }
        for author in authors
    ]
    
    return JsonResponse({"results": results})

def ajax_search_book_titles(request):
    """
    '책 제목 (한글)' 필드용 Select2 AJAX 검색 뷰
    """
    term = request.GET.get('term', '')
    
    titles = []
    if term:
        titles = Book.objects.filter(
            Q(title_korean__icontains=term) | Q(title_original__icontains=term)
        ).values_list('title_korean', flat=True).distinct().order_by('title_korean')[:10]
    
    results = [{"id": title, "text": title} for title in titles]
    
    return JsonResponse({"results": results})

def ajax_check_composer(request):
    """
    '작곡가명'을 받아 DB에 동명이인이 있는지 확인하고,
    일치하는 작곡가 목록(id, name, date_of_birth)을 JSON으로 반환합니다.
    """
    name = request.GET.get('name', '').strip()
    if not name:
        return JsonResponse([], safe=False) # 이름이 없으면 빈 리스트 반환

    # 이름이 정확히 일치하는(대소문자 무시) 작곡가 검색
    composers = Composer.objects.filter(name__iexact=name)
    
    results = [
        {
            "id": composer.id,
            "name": composer.name,
            "date_of_birth": composer.date_of_birth.strftime('%Y-%m-%d') if composer.date_of_birth else None
        }
        for composer in composers
    ]
    
    # 일치하는 목록 반환 (없으면 빈 리스트 [])
    return JsonResponse(results, safe=False)

def ajax_check_composer(request):
    """
    '작곡가명'과 '생년월일'을 받아 DB에 동명이인이 있는지 확인하고,
    일치하는 작곡가 목록(id, name, date_of_birth)을 JSON으로 반환합니다.
    """
    name = request.GET.get('name', '').strip()
    dob_str = request.GET.get('date_of_birth', '').strip()

    if not name or not dob_str or dob_str == '1900-01-01':
        return JsonResponse({'status': 'new', 'message': '이름 또는 생년월일이 유효하지 않습니다.'})

    try:
        # 1. 이름과 생년월일이 "정확히" 일치하는 경우 (동일인)
        exact_match = Composer.objects.get(name__iexact=name, date_of_birth=dob_str)
        return JsonResponse({
            'status': 'exact', # 정확히 일치
            'composer': {
                'id': exact_match.id,
                'name': exact_match.name,
                'date_of_birth': exact_match.date_of_birth.strftime('%Y-%m-%d')
            }
        })
    except Composer.DoesNotExist:
        # 2. 정확히 일치하는 사람은 없지만, "이름"만 같은 동명이인이 있는지 확인
        duplicate_names = Composer.objects.filter(name__iexact=name).exclude(date_of_birth=dob_str)
        
        if duplicate_names.exists():
            # 이름은 같지만 생년월일이 다른 동명이인 목록 반환
            results = [
                {
                    "id": composer.id,
                    "name": composer.name,
                    "date_of_birth": composer.date_of_birth.strftime('%Y-%m-%d') if composer.date_of_birth else '생일 미입력'
                }
                for composer in duplicate_names
            ]
            return JsonResponse({'status': 'duplicate_name', 'duplicates': results})
        else:
            # 3. 이름조차 일치하는 사람이 없는 신규 작곡가
            return JsonResponse({'status': 'new', 'message': '신규 작곡가입니다.'})
    except Composer.MultipleObjectsReturned:
        # (드문 경우) 이름과 생일이 모두 동일한 중복 데이터가 DB에 이미 있는 경우
        composer = Composer.objects.filter(name__iexact=name, date_of_birth=dob_str).first()
        return JsonResponse({
            'status': 'exact', 
            'composer': {
                'id': composer.id,
                'name': composer.name,
                'date_of_birth': composer.date_of_birth.strftime('%Y-%m-%d')
            }
        })
