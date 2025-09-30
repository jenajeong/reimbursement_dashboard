from rest_framework import serializers
from book.models import Author, Book, AuthorWork
from order.models import OrderItem 
from .models import Settlement, AnnualPerformance # Settlement, AnnualPerformance 모델 임포트
from django.db.models import Sum
from datetime import date


# --- 1. 책별 판매 집계 시리얼라이저 (BookSalesListView 사용) ---

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
            # Order 모델에 order_date가 있다고 가정합니다.
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
        return result.get('total_quantity', 0) or 0

    def get_total_revenue_current_period(self, obj):
        """필터링된 기간 내의 판매 금액 (current_period)"""
        start_date = self.context.get('start_date')
        end_date = self.context.get('end_date')
        
        result = self._filter_order_items(obj, start_date=start_date, end_date=end_date)
        return result.get('total_revenue', 0) or 0

    def get_total_sales_all_time(self, obj):
        """전체 기간 총 판매량"""
        result = self._filter_order_items(obj)
        return result.get('total_quantity', 0) or 0

    def get_last_settlement_units(self, obj):
        """
        마지막 정산일 이후의 누적 판매량 (리셋된 누적 판매량)
        - 이 책에 참여한 모든 저자의 가장 최근 정산일을 기준으로 합니다.
        """
        # Settlement 모델에 settled_date 필드가 있고, Book 모델에 authors ManyToMany 필드가 있다고 가정
        last_settlement = Settlement.objects.filter(
            author__in=obj.authors.all() 
        ).order_by('-settled_date').first()
        
        if last_settlement and last_settlement.settled_date:
            last_settlement_date = last_settlement.settled_date
            
            result = self._filter_order_items(obj, after_date=last_settlement_date)
            return result.get('total_quantity', 0) or 0
            
        # 정산 기록이 없다면 전체 기간의 판매량과 동일합니다.
        return self.get_total_sales_all_time(obj)


# --- 2. 저자별 정산 집계 시리얼라이저 (AuthorSettlementListView 사용) ---

class AuthorSettlementSerializer(serializers.ModelSerializer):
    """
    저자별 정산 집계를 위한 시리얼라이저입니다.
    저자의 책별 판매량, 누적 판매량, 리셋된 누적 판매량 등을 계산합니다.
    """
    authored_books = serializers.SerializerMethodField()
    total_sales_all_time = serializers.SerializerMethodField()
    units_since_last_settlement = serializers.SerializerMethodField()
    annual_performances = serializers.SerializerMethodField() # 연간 실적 필드 추가

    class Meta:
        model = Author
        fields = [
            'id', 'name', 'contact_number',
            'authored_books',
            'total_sales_all_time',
            'units_since_last_settlement',
            'annual_performances',
        ]

    def get_authored_books(self, obj):
        """
        저자가 쓴 책들과 해당 책의 기간별 판매량, 판매금액을 포함한 정보를 반환합니다.
        """
        start_date = self.context.get('start_date')
        end_date = self.context.get('end_date')
        
        # start_date와 end_date가 유효한지 확인합니다.
        if not (start_date and end_date):
             return [] # 기간이 없으면 빈 목록 반환

        books_data = []
        author_works = AuthorWork.objects.filter(author=obj).select_related('book')
        
        for work in author_works:
            book = work.book
            
            # 필터링된 기간 내 판매량 및 금액을 단일 쿼리로 집계합니다.
            try:
                current_period_aggregates = OrderItem.objects.filter(
                    book=book,
                    order__order_date__range=[start_date, end_date]
                ).aggregate(
                    sales=Sum('quantity'),
                    revenue=Sum('total_price')
                )
            except Exception as e:
                # 쿼리 실패 시 로깅 또는 기본값 처리
                print(f"Error aggregating sales for book {book.id}: {e}")
                current_period_aggregates = {'sales': 0, 'revenue': 0}
            
            books_data.append({
                'book_id': book.id,
                'title_korean': book.title_korean,
                'number_of_songs': work.number_of_songs,
                'current_period_sales': current_period_aggregates.get('sales') or 0,
                'current_period_revenue': current_period_aggregates.get('revenue') or 0,
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
            author=obj,
            is_settled=True # 완료된 정산만 확인
        ).order_by('-settled_date').first()
        
        if not last_settlement or not last_settlement.settled_date:
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

    def get_annual_performances(self, obj):
        """
        연간 실적 데이터를 반환합니다.
        """
        # 연결된 AnnualPerformance 인스턴스를 필터링하여 가져옵니다.
        # 연도별 정렬하여 최신 연도가 먼저 오도록 합니다.
        performances = obj.annualperformance_set.all().order_by('-settlement_year')
        
        # 필요한 필드만 직렬화하여 반환합니다. (AnnualPerformance 모델 구조에 따라 달라질 수 있음)
        return [
            {
                'year': p.settlement_year,
                'total_units': p.total_units,
                'total_revenue': p.total_revenue,
                'is_settled': p.is_settled
            }
            for p in performances
        ]


# --- 3. 정산 기록 시리얼라이저 (SettlementListView 사용) ---

class SettlementListSerializer(serializers.ModelSerializer):
    """
    정산 기록 목록을 조회하기 위한 시리얼라이저입니다.
    Author 이름과 연도, 정산 상태를 보여줍니다.
    """
    author_name = serializers.CharField(source='author.name', read_only=True)

    class Meta:
        model = Settlement
        fields = ['id', 'author', 'author_name', 'settlement_year', 'is_settled', 'settled_date', 'created_at']
        read_only_fields = ['settled_date', 'created_at']
        

# --- 4. 정산 업데이트/생성 시리얼라이저 (SettlementDetailView 및 POST 사용) ---

class SettlementUpdateSerializer(serializers.ModelSerializer):
    """
    정산 기록의 is_settled 상태를 업데이트하거나, SettlementListView에서 연도 유효성 검사에 사용됩니다.
    """
    class Meta:
        model = Settlement
        fields = ['id', 'author', 'settlement_year', 'is_settled', 'settled_date']
        read_only_fields = ['author', 'settlement_year', 'settled_date'] # GET 요청 시 필드

    def update(self, instance, validated_data):
        """
        is_settled 상태를 True로 변경 시, settled_date를 현재 시각으로 자동 업데이트합니다.
        """
        if 'is_settled' in validated_data and validated_data['is_settled'] and not instance.is_settled:
            # False -> True로 변경될 때만 settled_date 업데이트
            instance.settled_date = date.today() # 정산은 연도/날짜 단위로 처리

        # 기타 필드 업데이트
        instance.is_settled = validated_data.get('is_settled', instance.is_settled)
        instance.save()
        return instance

    def validate_settlement_year(self, value):
        """
        POST 요청 시, 연도 값이 숫자인지 유효성 검사 (SettlementListView에서 사용)
        """
        try:
            int(value)
        except ValueError:
            raise serializers.ValidationError("연도는 유효한 숫자 형식이어야 합니다.")
        
        if value > date.today().year:
            raise serializers.ValidationError("미래 연도에 대한 정산 기록을 생성할 수 없습니다.")
            
        return value
