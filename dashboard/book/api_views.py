from rest_framework import viewsets, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.utils import timezone
from django.db import transaction
from .models import Book, PriceHistory
from .serializers import BookSerializer, BookListSerializer
import datetime
import math # 반올림을 위해

class BookViewSet(viewsets.ModelViewSet):
    """
    Book 모델에 대한 CRUD API ViewSet
    """
    queryset = Book.objects.all().order_by('-id')
    permission_classes = [permissions.AllowAny]

    def get_serializer_class(self):
        """
        'list' 액션에서는 가벼운 Serializer를,
        'retrieve'나 'create', 'update' 등에서는 무거운 Serializer를 사용
        """
        if self.action == 'list':
            return BookListSerializer
        return BookSerializer

@api_view(['POST'])
@permission_classes([permissions.AllowAny]) 
def batch_price_update_api(request):
    """
    JSON 데이터를 받아 특정 ID의 책 가격을 일괄 변동시킵니다.
    """
    data = request.data
    # 카테고리 대신 book_ids를 받음
    book_ids_str = data.get('book_ids', '') 
    update_type = data.get('update_type') # 'amount' 또는 'percent'
    value = data.get('value')

    if not update_type or value is None:
        return Response({'error': 'update_type과 value가 필요합니다.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        value = int(value)
    except (ValueError, TypeError):
        return Response({'error': 'value는 숫자여야 합니다.'}, status=status.HTTP_400_BAD_REQUEST)

    # ID 문자열을 숫자 리스트로 변환
    book_ids = [int(id_val) for id_val in book_ids_str.split(',') if id_val.isdigit()]
    if not book_ids:
        return Response({'error': '유효한 book_ids가 필요합니다.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        with transaction.atomic(): # 데이터 일관성을 위해 트랜잭션 사용
            
            # 1. 대상 책 필터링 (카테고리 -> ID 리스트)
            books_to_update = Book.objects.filter(pk__in=book_ids)

            if not books_to_update.exists():
                return Response({'status': 'success', 'updated_count': 0, 'message': '해당 ID의 책이 없습니다.'}, status=status.HTTP_200_OK)

            # 2. 대상 책들의 현재 최신 가격 목록을 가져옴 (메모리에 로드)
            latest_prices = list(
                PriceHistory.objects.filter(book__in=books_to_update, is_latest=True)
            )
            latest_price_pks = [p.pk for p in latest_prices]

            # 3. 기존 가격들의 '최신' 플래그를 모두 False로 변경
            PriceHistory.objects.filter(pk__in=latest_price_pks).update(is_latest=False)

            # 4. 새 가격 이력 생성 준비
            new_histories = []
            now = timezone.now()

            for old_price in latest_prices:
                new_p = 0
                if update_type == 'amount':
                    new_p = old_price.price + value
                elif update_type == 'percent':
                    # 퍼센트 인상 (소수점 첫째 자리에서 반올림)
                    new_p = round(old_price.price * (1 + value / 100), 0) 
                
                # 가격이 0 미만이 되지 않도록
                new_p = max(0, new_p) 

                new_histories.append(
                    PriceHistory(
                        book=old_price.book, 
                        price=new_p, 
                        is_latest=True, 
                        price_updated_at=now
                    )
                )

            # 5. 새 가격 이력을 DB에 일괄 생성
            if new_histories:
                PriceHistory.objects.bulk_create(new_histories)

            return Response({
                'status': 'success', 
                'updated_count': len(new_histories)
            }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({'error': f'일괄 변동 중 오류 발생: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)