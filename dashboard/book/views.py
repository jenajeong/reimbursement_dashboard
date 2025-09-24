from django.shortcuts import render
from rest_framework import viewsets
from rest_framework import generics
from .models import Book, Author
from .permissions import IsAuthorOrAdmin
from .serializers import BookListSerializer, BookDetailSerializer, AuthorDetailSerializer, AuthorSerializer, AuthorListSerializer
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend, FilterSet, DateFilter
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from datetime import date



class BookFilter(FilterSet):
    # 가격 변동일(price_updated_at)을 기준으로 날짜 범위를 필터링
    price_updated_at = DateFilter(field_name='price_histories__price_updated_at')

    class Meta:
        model = Book
        # 필터링 가능한 필드 목록
        fields = ['category', 'price_updated_at']


class BookListView(generics.ListAPIView):
    """
    책 목록을 조회(GET)하는 API 뷰입니다.
    로그인한 사용자만 접근할 수 있으며, 수정/생성/삭제는 불가능합니다.
    """
    queryset = Book.objects.all()
    
    # 필터링, 검색, 정렬 백엔드 추가
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    
    # 필터셋 클래스를 커스텀 필터인 BookFilter로 지정
    filterset_class = BookFilter
    
    # 검색을 허용할 필드 지정
    search_fields = ['title_korean', 'subtitle', 'author__name']
    
    # 정렬을 허용할 필드 지정
    ordering_fields = ['title_korean', 'current_price']
    
    # 기본 정렬 필드 지정 (이름 순서대로)
    ordering = ['title_korean']
    
    # GET 요청만 처리하므로 BookListSerializer를 직접 지정
    serializer_class = BookListSerializer
    
    # GET 요청만 있으므로 IsAuthenticated 권한만 적용
    permission_classes = [IsAuthenticated]




class BookDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    특정 책의 상세 정보를 조회(GET), 수정(PUT/PATCH), 삭제(DELETE)하는 API 뷰입니다.
    """
    queryset = Book.objects.all()
    serializer_class = BookDetailSerializer
    
    # 이 뷰는 GET 외의 요청도 처리하므로 복잡한 권한 로직을 유지합니다.
    # 안전한 요청(조회)은 로그인한 사용자만, 안전하지 않은 요청(수정/삭제)은 관리자만 허용
    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAuthenticated()]
        return [IsAdminUser()]

class AuthorListView(generics.ListAPIView):
    """
    모든 저자의 기본 정보 목록을 조회하는 뷰입니다.
    - GET 요청: 'id', 'name', 'date_of_birth', 'contact_number', 
      'total_books', 'total_songs' 값을 반환합니다.
    """
    queryset = Author.objects.all()
    serializer_class = AuthorListSerializer
    permission_classes = [IsAdminUser]

class AuthorCreateView(generics.CreateAPIView):
    """
    새로운 저자를 생성하는 뷰입니다.
    - POST 요청: AuthorSerializer를 사용하여 새로운 저자 데이터를 생성합니다.
    """
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer
    permission_classes = [IsAuthenticated]


class AuthorDetailView(generics.RetrieveUpdateAPIView):
    """
    특정 저자의 상세 정보 조회 및 수정을 위한 뷰입니다.
    - GET 요청: 기간별 책 정보 및 판매량 포함한 상세 정보를 조회합니다.
      예시 URL: /authors/1/?start_date=2024-01-01&end_date=2024-12-31
    - PUT/PATCH 요청: 저자 정보를 수정합니다.
    """
    queryset = Author.objects.all()
    permission_classes = [IsAuthenticated, IsAuthorOrAdmin]

    def get_serializer_class(self):
        """
        요청 HTTP 메서드에 따라 다른 시리얼라이저를 반환합니다.
        조회(GET) 시 AuthorDetailSerializer를 사용하고,
        수정(PUT/PATCH) 시 AuthorSerializer를 사용합니다.
        """
        if self.request.method in ['PUT', 'PATCH']:
            return AuthorSerializer
        return AuthorDetailSerializer

    def get_serializer_context(self):
        """
        URL 쿼리 파라미터에서 start_date와 end_date를 가져와 
        시리얼라이저의 context로 전달합니다.
        """
        context = super().get_serializer_context()
        start_date_str = self.request.query_params.get('start_date')
        end_date_str = self.request.query_params.get('end_date')

        try:
            if start_date_str:
                context['start_date'] = date.fromisoformat(start_date_str)
            if end_date_str:
                context['end_date'] = date.fromisoformat(end_date_str)
        except ValueError:
            # 날짜 형식이 올바르지 않으면 무시하고 다음으로 넘어갑니다.
            pass
        
        return context
    