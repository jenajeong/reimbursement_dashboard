from django.shortcuts import render, redirect
from .forms import BookForm, ComposerWorkFormSet
from .models import Book, Category, Composer, ComposerWork # Author 모델 import
import datetime
from django.db.models import Q, F

def book_list_view(request):
    """
    책 목록 페이지의 메인 뷰.
    페이지 로드, 검색, 필터링을 처리하고 테이블 본문을 업데이트합니다.
    """
    books = Book.objects.select_related('category').prefetch_related('authors', 'price_histories').order_by('-pk')

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
        books = books.filter(category__category1=category1)
    if category2:
        books = books.filter(category__category2=category2)

    # --- 템플릿에 전달할 Context 데이터 ---
    context = {
        'books': books,
        'categories1': Category.objects.values_list('category1', flat=True).distinct().order_by('category1'),
        'search_query': search_query,
        'selected_category1': category1,
        'selected_category2': category2,
    }

    # HTMX 요청인 경우, 테이블 본문 부분만 렌더링하여 반환
    if request.htmx:
        return render(request, 'book/partials/book_table_body.html', context)

    # 일반적인 첫 페이지 로드인 경우, 전체 페이지 템플릿 렌더링
    return render(request, 'book/book_list.html', context)


def load_category2(request):
    """
    카테고리1 값에 따라 카테고리2 옵션을 반환하는 HTMX용 뷰
    """
    category1 = request.GET.get('category1')
    categories2 = []
    if category1:
        categories2 = Category.objects.filter(category1=category1).values_list('category2', flat=True).distinct().order_by('category2')
    
    return render(request, 'book/partials/category2_options.html', {
        'categories2': categories2
    })

def add_book_view(request):
    if request.method == 'POST':
        book_form = BookForm(request.POST)
        composer_formset = ComposerWorkFormSet(request.POST)

        if book_form.is_valid() and composer_formset.is_valid():
            book = book_form.save()

            # ==== 👇 저장 로직을 원래대로 복구 ====
            for form in composer_formset:
                if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                    composer_name = form.cleaned_data.get('composer_name')
                    date_of_birth = form.cleaned_data.get('date_of_birth')
                    
                    # get_or_create로 작곡가를 찾거나 새로 만듭니다.
                    composer, created = Composer.objects.get_or_create(name=composer_name)
                    
                    # 새로 생성된 작곡가이고 생년월일이 입력되었다면, 정보 업데이트
                    if created and date_of_birth:
                        composer.date_of_birth = date_of_birth
                        composer.save()

                    # formset의 인스턴스를 book과 연결하여 저장
                    composer_work = form.save(commit=False)
                    composer_work.book = book
                    composer_work.composer = composer
                    composer_work.save()
            
            return redirect('book_list')
    else:
        book_form = BookForm()
        composer_formset = ComposerWorkFormSet()

    context = {
        'book_form': book_form,
        'composer_formset': composer_formset,
    }
    return render(request, 'book/add_book.html', context)
