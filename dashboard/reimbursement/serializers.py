from rest_framework import serializers
from book.models import Author, Book, AuthorWork
from order.models import OrderItem # OrderItem 모델이 있다고 가정
from .models import Settlement # Settlement 모델 임포트
from django.db.models import Sum


class BookSalesSerializer(serializers.ModelSerializer):
    """
    책별 판매 집계를 위한 시리얼라이저입니다.
    특정 기간 내의 판매량, 판매 금액, 전체 기간 누적 판매량, 마지막 정산일 이후 판매량을 계산합니다.
    """
    total_sales_current_period = serializers.SerializerMethodField()
    total_revenue_current_period = serializers.SerializerMethodField()
    total_sales_all_time = serializers.SerializerMethodField()
    last_settlement_units = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = [
            'id', 'title_korean',
            'total_sales_current_period',
            'total_revenue_current_period',
            'total_sales_all_time',
            'last_settlement_units',
        ]
        
    def _filter_order_items(self, book_obj, start_date=None, end_date=None, after_date=None):
        """판매량 집계를 위한 쿼리셋 필터링을 수행합니다."""
        qs = OrderItem.objects.filter(book=book_obj)
        
        if start_date and end_date:
            # 특정 기간 필터링 (Views에서 넘어온 start_date, end_date)
            qs = qs.filter(order__order_date__range=[start_date, end_date])
        
        if after_date:
            # 특정 날짜 이후 필터링 (Settlement 날짜 이후)
            qs = qs.filter(order__order_date__gt=after_date)
            
        return qs.aggregate(
            total_quantity=Sum('quantity'),
            total_revenue=Sum('total_price')
        )

    def get_total_sales_current_period(self, obj):
        """필터링된 기간 내의 판매량 (current_period)"""
        start_date = self.context.get('start_date')
        end_date = self.context.get('end_date')
        
        result = self._filter_order_items(obj, start_date=start_date, end_date=end_date)
        return result.get('total_quantity', 0)

    def get_total_revenue_current_period(self, obj):
        """필터링된 기간 내의 판매 금액 (current_period)"""
        start_date = self.context.get('start_date')
        end_date = self.context.get('end_date')
        
        result = self._filter_order_items(obj, start_date=start_date, end_date=end_date)
        return result.get('total_revenue', 0)

    def get_total_sales_all_time(self, obj):
        """전체 기간 총 판매량"""
        result = self._filter_order_items(obj)
        return result.get('total_quantity', 0)

    def get_last_settlement_units(self, obj):
        """
        마지막 정산일 이후의 누적 판매량 (리셋된 누적 판매량)
        - 이 책에 참여한 모든 저자의 가장 최근 정산일을 기준으로 합니다.
        """
        # 이 책과 관련된 모든 저자들의 Settlement 기록 중 가장 최근 날짜를 찾습니다.
        last_settlement = Settlement.objects.filter(
            author__in=obj.authors.all() # Book 모델에 authors ManyToMany 필드가 있다고 가정
        ).order_by('-settled_date').first()
        
        if last_settlement:
            last_settlement_date = last_settlement.settled_date
            
            result = self._filter_order_items(obj, after_date=last_settlement_date)
            return result.get('total_quantity', 0)
            
        # 정산 기록이 없다면 전체 기간의 판매량과 동일합니다.
        return self.get_total_sales_all_time(obj)


class AuthorSettlementSerializer(serializers.ModelSerializer):
    """
    저자별 정산 집계를 위한 시리얼라이저입니다.
    저자의 책별 판매량, 누적 판매량, 리셋된 누적 판매량 등을 계산합니다.
    """
    authored_books = serializers.SerializerMethodField()
    total_sales_all_time = serializers.SerializerMethodField()
    units_since_last_settlement = serializers.SerializerMethodField()

    class Meta:
        model = Author
        fields = [
            'id', 'name', 'contact_number',
            'authored_books',
            'total_sales_all_time',
            'units_since_last_settlement',
        ]

    def get_authored_books(self, obj):
        """
        저자가 쓴 책들과 해당 책의 기간별 판매량, 판매금액을 포함한 정보를 반환합니다.
        """
        start_date = self.context.get('start_date')
        end_date = self.context.get('end_date')
        
        books_data = []
        author_works = AuthorWork.objects.filter(author=obj).select_related('book')
        
        for work in author_works:
            book = work.book
            
            # 필터링된 기간 내 판매량 및 금액
            current_period_aggregates = OrderItem.objects.filter(
                book=book,
                order__order_date__range=[start_date, end_date]
            ).aggregate(
                sales=Sum('quantity'),
                revenue=Sum('total_price')
            )
            
            books_data.append({
                'book_id': book.id,
                'title_korean': book.title_korean,
                'number_of_songs': work.number_of_songs,
                'current_period_sales': current_period_aggregates.get('sales', 0) or 0,
                'current_period_revenue': current_period_aggregates.get('revenue', 0) or 0,
            })
        
        return books_data

    def get_total_sales_all_time(self, obj):
        """
        저자의 전체 기간 총 누적 판매 권수
        """
        total = 0
        # 저자가 쓴 모든 책을 순회하며 전체 판매량을 합산합니다.
        for work in AuthorWork.objects.filter(author=obj):
            total += OrderItem.objects.filter(book=work.book).aggregate(
                total=Sum('quantity')
            ).get('total', 0) or 0
        return total

    def get_units_since_last_settlement(self, obj):
        """
        저자의 마지막 정산일 이후 리셋된 총 누적 판매 권수
        """
        # 해당 저자의 가장 최근 정산 기록을 찾습니다.
        last_settlement = Settlement.objects.filter(
            author=obj
        ).order_by('-settled_date').first()
        
        if not last_settlement:
            # 정산 기록이 없다면 전체 판매량과 동일합니다.
            return self.get_total_sales_all_time(obj)

        last_settlement_date = last_settlement.settled_date
        total_units = 0
        
        # 저자가 쓴 모든 책을 순회하며 정산일 이후의 판매량만 합산합니다.
        for work in AuthorWork.objects.filter(author=obj):
            total_units += OrderItem.objects.filter(
                book=work.book,
                # 정산일보다 엄격하게 '이후'의 판매량만 계산합니다.
                order__order_date__gt=last_settlement_date
            ).aggregate(
                total=Sum('quantity')
            ).get('total', 0) or 0
            
        return total_units
    