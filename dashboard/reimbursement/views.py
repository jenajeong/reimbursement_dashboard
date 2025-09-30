from datetime import date
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from django.utils import timezone
from book.models import Book, Author
from .serializers import (
    BookSalesSerializer, 
    AuthorSettlementSerializer, 
    SettlementListSerializer,  # <--- 이 부분이 정확히 임포트되도록 수정했습니다.
    SettlementUpdateSerializer
)
from .permissions import IsAdminUser
from .models import Settlement # Settlement 모델 임포트


# --- 1. 책별 집계 뷰 (관리자 전용) ---
class BookSalesListView(generics.ListAPIView):
    """
    책별 판매 집계 목록을 조회하는 뷰입니다.
    - 관리자(is_staff=True)만 전체 목록 접근 가능합니다.
    """
    serializer_class = BookSalesSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

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

        start_date = date.fromisoformat(start_date_str) if start_date_str else None
        end_date = date.fromisoformat(end_date_str) if end_date_str else None

        context['start_date'] = start_date
        context['end_date'] = end_date
        return context


# --- 2. 저자별 정산 뷰 (본인 데이터만 접근 가능) ---
class AuthorSettlementListView(generics.ListAPIView):
    """
    저자별 정산 집계 목록을 조회하는 뷰입니다.
    - 관리자: 모든 저자 목록 조회 가능
    - 작곡가: 자신의 Author 정보만 목록으로 조회 가능
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
            author_instance = Author.objects.get(user=user)
            # QuerySet을 반환
            return Author.objects.filter(pk=author_instance.pk)
        except Author.DoesNotExist:
            raise PermissionDenied("귀하의 사용자 계정과 연결된 작곡가 정보가 없습니다.")
        except Exception:
            raise PermissionDenied("데이터를 조회할 권한이 없습니다.")

    def get_serializer_context(self):
        """
        URL 쿼리 파라미터에서 기간 정보를 가져와 시리얼라이저에 전달합니다.
        """
        context = super().get_serializer_context()
        start_date_str = self.request.query_params.get('start_date')
        end_date_str = self.request.query_params.get('end_date')

        start_date = date.fromisoformat(start_date_str) if start_date_str else None
        end_date = date.fromisoformat(end_date_str) if end_date_str else None

        context['start_date'] = start_date
        context['end_date'] = end_date
        return context


# --- 3. 정산 관리 뷰 (관리자 전용) ---

class SettlementListView(generics.ListCreateAPIView):
    """
    정산 기록 목록을 조회하고, 새로운 연도별 정산 기록을 생성하는 뷰입니다.
    - 관리자 전용 (IsAdminUser)
    - GET: 저자별 연도별 정산 목록 조회. `year` 쿼리 파라미터로 필터링 가능.
    - POST: 특정 연도에 대한 모든 저자의 정산 기록을 (미완료 상태로) 일괄 생성.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            # POST 요청 시, 연도 유효성 검사를 위해 SettlementUpdateSerializer를 사용
            return SettlementUpdateSerializer 
        return SettlementListSerializer

    def get_queryset(self):
        # 쿼리 파라미터에서 연도를 받아 필터링
        year_str = self.request.query_params.get('year')
        queryset = Settlement.objects.all()
        if year_str:
            try:
                year = int(year_str)
                queryset = queryset.filter(settlement_year=year)
            except ValueError:
                pass # 잘못된 연도 형식은 무시

        return queryset
    
    def create(self, request, *args, **kwargs):
        """
        POST 요청 시: 특정 연도에 대해 모든 Author의 정산 기록을 생성합니다.
        (is_settled=False로 초기화)
        """
        # 요청 본문에서 연도를 추출 (기본값은 현재 연도)
        settlement_year = request.data.get('settlement_year', timezone.now().year)

        try:
            settlement_year = int(settlement_year)
        except ValueError:
            return Response({'settlement_year': '유효한 연도(숫자)를 입력해야 합니다.'}, status=400)

        # 모든 Author를 조회
        authors = Author.objects.all()
        
        created_count = 0
        for author in authors:
            # 해당 Author와 연도의 기록이 없으면 생성. 기존 기록은 is_settled 상태를 유지함.
            _, created = Settlement.objects.get_or_create(
                author=author,
                settlement_year=settlement_year,
                defaults={'is_settled': False}
            )
            if created:
                created_count += 1
            
        # 생성된 레코드 수와 함께 성공 응답 반환
        message = f'Successfully created {created_count} new settlement records for year {settlement_year}. Existing records were updated.'
        return Response({'message': message}, status=201)


class SettlementDetailView(generics.RetrieveUpdateAPIView):
    """
    특정 정산 기록의 상세 정보를 조회하고, 정산 완료 여부(is_settled)를 업데이트합니다.
    - 관리자 전용 (IsAdminUser)
    """
    queryset = Settlement.objects.all()
    serializer_class = SettlementUpdateSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    lookup_field = 'pk' # /settlements/<pk>/ 경로 사용
