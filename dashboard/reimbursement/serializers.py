from rest_framework import serializers
from book.models import Author, Book, AuthorWork
from order.models import OrderItem

class BookSalesSerializer(serializers.ModelSerializer):
    """
    책별 판매 집계를 위한 시리얼라이저입니다.
    특정 기간 내의 판매량, 판매 금액, 전체 기간 누적 판매량을 계산합니다.
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

    def get_total_sales_current_period(self, obj):
        """필터링된 기간 내의 판매량"""
        start_date = self.context.get('start_date')
        end_date = self.context.get('end_date')

        if start_date and end_date:
            return OrderItem.objects.filter(
                book=obj,
                order__order_date__range=[start_date, end_date]
            ).aggregate(
                total=serializers.F('quantity')
            ).get('total', 0)
        return 0

    def get_total_revenue_current_period(self, obj):
        """필터링된 기간 내의 판매 금액"""
        start_date = self.context.get('start_date')
        end_date = self.context.get('end_date')

        if start_date and end_date:
            return OrderItem.objects.filter(
                book=obj,
                order__order_date__range=[start_date, end_date]
            ).aggregate(
                total=serializers.F('total_price')
            ).get('total', 0)
        return 0

    def get_total_sales_all_time(self, obj):
        """전체 기간 총 판매량"""
        return OrderItem.objects.filter(book=obj).aggregate(
            total=serializers.F('quantity')
        ).get('total', 0)

    def get_last_settlement_units(self, obj):
        """마지막 정산일 이후의 누적 판매량"""
        # 이 기능은 Settlement 모델과 연동되어야 합니다.
        # Settlement 모델에 책별 최종 정산일 필드가 필요합니다.
        # 예시 로직:
        # last_settlement_date = Settlement.objects.filter(
        #     author__in=obj.author.all()
        # ).order_by('-settled_date').first().settled_date
        # return OrderItem.objects.filter(
        #     book=obj,
        #     order__order_date__gt=last_settlement_date
        # ).aggregate(
        #     total=serializers.F('quantity')
        # ).get('total', 0)
        return 0


class AuthorSettlementSerializer(serializers.ModelSerializer):
    """
    저자별 정산 집계를 위한 시리얼라이저입니다.
    저자의 책별 판매량, 판매 금액, 누적 판매량 등을 계산합니다.
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
        저자가 쓴 책들과 해당 책의 판매량, 판매금액을 포함한 정보를 반환합니다.
        """
        start_date = self.context.get('start_date')
        end_date = self.context.get('end_date')
        
        books_data = []
        author_works = AuthorWork.objects.filter(author=obj)
        for work in author_works:
            book = work.book
            
            # 필터링된 기간 내 판매량 및 금액
            current_period_sales = OrderItem.objects.filter(
                book=book,
                order__order_date__range=[start_date, end_date]
            ).aggregate(
                sales=serializers.F('quantity'),
                revenue=serializers.F('total_price')
            )
            
            books_data.append({
                'book_id': book.id,
                'title_korean': book.title_korean,
                'number_of_songs': work.number_of_songs,
                'current_period_sales': current_period_sales.get('sales', 0),
                'current_period_revenue': current_period_sales.get('revenue', 0),
            })
        
        return books_data

    def get_total_sales_all_time(self, obj):
        """
        전체 기간 총 누적 판매 권수
        """
        total = 0
        for work in AuthorWork.objects.filter(author=obj):
            total += OrderItem.objects.filter(book=work.book).aggregate(
                total=serializers.F('quantity')
            ).get('total', 0)
        return total

    def get_units_since_last_settlement(self, obj):
        """
        마지막 정산일 이후 리셋된 누적 판매 권수
        """
        # 이 로직도 Settlement 모델과 연동되어야 합니다.
        # 예시 로직:
        # last_settlement_date = Settlement.objects.filter(
        #     author=obj
        # ).order_by('-settled_date').first().settled_date
        # total_units = 0
        # for work in AuthorWork.objects.filter(author=obj):
        #     total_units += OrderItem.objects.filter(
        #         book=work.book,
        #         order__order_date__gt=last_settlement_date
        #     ).aggregate(
        #         total=serializers.F('quantity')
        #     ).get('total', 0)
        # return total_units
        return 0