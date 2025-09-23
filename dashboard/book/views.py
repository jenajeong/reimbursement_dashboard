from django.shortcuts import render
from rest_framework import generics
from .models import Book
from .serializers import BookListSerializer, BookDetailSerializer
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend, FilterSet, DateFilter
from rest_framework.permissions import IsAuthenticated, IsAdminUser



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
