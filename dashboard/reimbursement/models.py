from django.db import models
from book.models import Author # Author 모델 임포트

class AnnualPerformance(models.Model):
    """
    저자별 연간 실적을 기록하는 모델입니다.
    이 모델의 데이터는 정산 기준(계약 건수)을 충족했는지 확인하는 데 사용됩니다.
    """
    author = models.ForeignKey(
        Author, 
        on_delete=models.CASCADE, 
        related_name='annual_performance', 
        verbose_name="저자"
    )
    year = models.PositiveIntegerField(
        verbose_name="연도"
    )
    total_units = models.PositiveIntegerField(
        default=0, 
        verbose_name="총 건수 (책에 포함된 곡 수)"
    )

    def __str__(self):
        return f"{self.year}년 {self.author.name} 총 실적: {self.total_units}건"

    class Meta:
        verbose_name = "연간 실적"
        verbose_name_plural = "연간 실적 목록"
        # 저자와 연도별로 유일한 레코드가 존재하도록 설정
        unique_together = ('author', 'year')


class Settlement(models.Model):
    """
    저자에게 지급된 정산 내역 및 정산 일자를 기록하는 모델입니다.
    이 모델의 'settled_date'는 판매량 리셋의 기준일이 됩니다.
    """
    author = models.ForeignKey(
        Author, 
        on_delete=models.CASCADE, 
        related_name='settlements', 
        verbose_name="저자"
    )
    settlement_year = models.PositiveIntegerField(
        verbose_name="정산 연도"
    )
    # 정산이 완료된 시점을 기록하며, 이 날짜 이후 판매량이 누적됩니다.
    settled_date = models.DateField(
        verbose_name="정산일"
    )
    # 실제 지급된 금액 (기록을 위해 추가)
    settlement_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name="정산 금액",
        null=True,
        blank=True
    )
    
    def __str__(self):
        return f"{self.settled_date} 정산 - {self.author.name}"

    class Meta:
        verbose_name = "정산 내역"
        verbose_name_plural = "정산 내역 목록"
        ordering = ['-settled_date', 'author__name']