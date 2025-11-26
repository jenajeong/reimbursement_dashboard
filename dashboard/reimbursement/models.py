from django.db import models
import datetime 
from book.models import Book, Composer 

class SaleRecord(models.Model):
    """
    책별 판매 기록 (기간별 판매량 및 누적 계산의 기초 자료)
    """
    book = models.ForeignKey(
        Book, 
        on_delete=models.CASCADE, 
        related_name='sale_records',
        verbose_name='책'
    )
    sale_date = models.DateField(
        verbose_name='판매 날짜'
    )
    quantity_sold = models.PositiveIntegerField(
        default=0,
        verbose_name='판매 수량'
    )
    total_revenue = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00,
        verbose_name='판매 금액'
    )
    recorded_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='기록 생성일'
    )

    class Meta:
        verbose_name = '판매 기록'
        verbose_name_plural = '판매 기록 목록'
        # 특정 책의 특정 날짜 판매 기록이 중복되지 않도록 합니다.
        unique_together = ('book', 'sale_date') 
        # 판매 날짜를 기준으로 최신순 정렬
        ordering = ['-sale_date']
    
    def __str__(self):
        return f"{self.book.title_korean} - {self.sale_date}: {self.quantity_sold}권"


class RoyaltySettlement(models.Model):
    """
    1000권*n 누적 판매 달성에 따른 작곡가별 정산 내역 및 지급 여부 기록
    - 정산 비율은 ComposerWork 모델을 통해 참조하여 사용합니다.
    """
    book = models.ForeignKey(
        Book, 
        on_delete=models.CASCADE, 
        related_name='settlements',
        verbose_name='정산 대상 책'
    )
    composer = models.ForeignKey(
        Composer, 
        on_delete=models.CASCADE, 
        related_name='settlements',
        verbose_name='정산 대상 작곡가'
    )
    # 누적 판매량 계산 시, 특정 연도에 달성한 임계값을 기록합니다.
    threshold_met_year = models.IntegerField(
        default=datetime.date.today().year,
        verbose_name='임계값 달성 연도'
    )
    threshold_multiple = models.PositiveIntegerField(
        verbose_name='달성 1000권 배수 (n)'
    )
    
    is_paid = models.BooleanField(
        default=False,
        verbose_name='정산 지급 완료 여부'
    )
    settlement_date = models.DateField(
        null=True, 
        blank=True,
        verbose_name='실제 정산 지급일'
    )
    
    # 이 정산이 발생한 시점의 누적 판매량을 기록하여 기록의 투명성을 높입니다.
    cumulative_sales_at_settlement = models.PositiveIntegerField(
        default=0,
        verbose_name='정산 시점의 누적 판매량'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        verbose_name = '저작권 정산 내역'
        verbose_name_plural = '저작권 정산 내역 목록'
        # 한 책의 한 작곡가에 대해, 같은 연도에 같은 배수로 중복 정산 기록을 방지합니다.
        unique_together = ('book', 'composer', 'threshold_met_year', 'threshold_multiple')
        # 최신 정산 내역이 먼저 보이도록 합니다.
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.book.title_korean}] {self.threshold_met_year}년 {self.threshold_multiple}000권 정산 - {self.composer.name}"
    