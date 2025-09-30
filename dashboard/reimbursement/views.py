from django.shortcuts import render
from datetime import date
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from book.models import Book, Author
from .serializers import BookSalesSerializer, AuthorSettlementSerializer

# --- 1. 책별 집계 뷰 (관리자만 접근 가능하도록 유지) ---
class BookSalesListView(generics.ListAPIView):
    """
    책별 판매 집계 목록을 조회하는 뷰입니다.
    (관리자만 전체 목록 접근 가능하도록 IsAuthenticated 유지)
    """
    serializer_class = BookSalesSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """모든 책 목록을 반환합니다."""
        # TODO: 추후 관리자(is_staff=True)만 접근 가능하도록 Permission 클래스를 커스텀하는 것을 고려해야 합니다.
        return Book.objects.all()

    def get_serializer_context(self):
        """
        URL 쿼리 파라미터에서 기간 정보를 가져와 시리얼라이저에 전달합니다.
        """
        context = super().get_serializer_context()
        start_date_str = self.request.query_params.get('start_date')
        end_date_str = self.request.query_params.get('end_date')

        # 날짜 문자열을 date 객체로 변환
        start_date = date.fromisoformat(start_date_str) if start_date_str else None
        end_date = date.fromisoformat(end_date_str) if end_date_str else None

        context['start_date'] = start_date
        context['end_date'] = end_date
        return context


# --- 2. 저자별 정산 뷰 (인증된 작곡가만 자신의 데이터 접근 가능) ---
class AuthorSettlementListView(generics.ListAPIView):
    """
    저자별 정산 집계 목록을 조회하는 뷰입니다.
    - 관리자: 모든 저자 목록 조회 가능
    - 작곡가: 자신의 Author 정보만 목록으로 조회 가능 (QuerySet 필터링 적용)
    """
    serializer_class = AuthorSettlementSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # 1. 관리자인 경우 (is_staff=True)
        if user.is_staff:
            return Author.objects.all()

        # 2. 일반 작곡가인 경우 (is_staff=False)
        try:
            # 현재 로그인된 User와 1:1 연결된 Author 객체를 찾습니다.
            author_instance = Author.objects.get(user=user)
            # QuerySet을 반환해야 하므로, 해당 Author 객체만 필터링하여 반환합니다.
            return Author.objects.filter(pk=author_instance.pk)
            
        except Author.DoesNotExist:
            # User는 있지만 연결된 Author가 없는 경우 (잘못된 가입 경로 또는 누락)
            raise PermissionDenied("귀하의 사용자 계정과 연결된 작곡가 정보가 없습니다.")
        except Exception:
            # 기타 오류 처리
            raise PermissionDenied("데이터를 조회할 권한이 없습니다.")

    def get_serializer_context(self):
        """
        URL 쿼리 파라미터에서 기간 정보를 가져와 시리얼라이저에 전달합니다.
        """
        context = super().get_serializer_context()
        start_date_str = self.request.query_params.get('start_date')
        end_date_str = self.request.query_params.get('end_date')

        # 날짜 문자열을 date 객체로 변환
        start_date = date.fromisoformat(start_date_str) if start_date_str else None
        end_date = date.fromisoformat(end_date_str) if end_date_str else None

        context['start_date'] = start_date
        context['end_date'] = end_date
        return context
    