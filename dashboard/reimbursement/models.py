from django.db import models
from django.utils import timezone
from book.models import Author # Author 모델 임포트

class AnnualPerformance(models.Model):
    """
    (추가 정보용) 저자별 연간 실적 집계 모델 (필요 시 확장)
    """
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name='annual_performance')
    year = models.IntegerField(verbose_name='연도')
    total_sales_units = models.IntegerField(default=0, verbose_name='총 판매 권수')
    total_revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='총 매출')

    class Meta:
        verbose_name = '연간 실적'
        verbose_name_plural = '연간 실적 목록'
        unique_together = ('author', 'year')
        ordering = ['-year']

    def __str__(self):
        return f"{self.author.name} - {self.year}년 실적"


class Settlement(models.Model):
    """
    저자별 연말 정산 여부를 관리하는 모델.
    Author와 settlement_year의 조합은 고유해야 합니다.
    """
    # 1:1 연결이 아니라, 특정 저자에 대해 여러 해의 정산 기록을 남기기 때문에 ForeignKey 사용
    author = models.ForeignKey(
        Author, 
        on_delete=models.CASCADE, 
        related_name='settlements',
        verbose_name='저자'
    )
    
    # 정산 대상 연도 (예: 2024)
    settlement_year = models.IntegerField(
        default=timezone.now().year,
        verbose_name='정산 연도'
    )
    
    # 정산 완료 여부 (True: 정산 완료, False: 정산 미완료 또는 예정)
    is_settled = models.BooleanField(
        default=False,
        verbose_name='정산 완료 여부'
    )

    class Meta:
        verbose_name = '정산 기록'
        verbose_name_plural = '정산 기록 목록'
        # 특정 저자는 특정 연도에 대해 하나의 정산 기록만 가질 수 있도록 고유 제약 조건 설정
        unique_together = ('author', 'settlement_year')
        # 가장 최근 연도부터 보여주기
        ordering = ['-settlement_year', 'author__name']

    def __str__(self):
        return f"{self.author.name} - {self.settlement_year}년 정산: {'완료' if self.is_settled else '미완료'}"
    