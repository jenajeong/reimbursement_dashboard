from django.shortcuts import render
from datetime import date
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from book.models import Book, Author
from .serializers import BookSalesSerializer, AuthorSettlementSerializer


class BookSalesListView(generics.ListAPIView):
    """
    책별 판매 집계 목록을 조회하는 뷰입니다.
    - GET 요청: `start_date`와 `end_date` 쿼리 파라미터를 통해 기간별 필터링을 지원합니다.
    """
    serializer_class = BookSalesSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """모든 책 목록을 반환합니다."""
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


class AuthorSettlementListView(generics.ListAPIView):
    """
    저자별 정산 집계 목록을 조회하는 뷰입니다.
    - GET 요청: `start_date`와 `end_date` 쿼리 파라미터를 통해 기간별 필터링을 지원합니다.
    """
    serializer_class = AuthorSettlementSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """모든 저자 목록을 반환합니다."""
        return Author.objects.all()

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
    