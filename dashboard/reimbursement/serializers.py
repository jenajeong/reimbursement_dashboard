# reimbursement/serializers.py (업데이트 완료)

from rest_framework import serializers
from django.db.models import Sum, F
from datetime import date
import decimal # DecimalField 처리를 위해 import

# 외부 모델 임포트 (실제 경로에 맞게 수정 필요)
from book.models import Book, ComposerWork, Composer 
from .models import SaleRecord, RoyaltySettlement 


class ReimbursementListSerializer(serializers.Serializer):
    """
    정산 목록 페이지에 필요한 최종 데이터를 표현하는 Serializer
    - views.py의 전체 누적 집계 필드(total_cumulative_sales/revenue)를 사용합니다.
    """
    # ----------------------------------------------------
    # View에서 어노테이션된 필드 (이름 변경됨)
    # ----------------------------------------------------
    book_id = serializers.IntegerField(source='id', read_only=True)
    book_name = serializers.CharField(source='title_korean', read_only=True)
    
    # 💡 View에서 전달받는 누적 필드 (이름 수정됨)
    total_cumulative_sales = serializers.IntegerField(read_only=True) 
    total_cumulative_revenue = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True) 

    # ----------------------------------------------------
    # 커스텀 계산 필드
    # ----------------------------------------------------
    composers_summary = serializers.SerializerMethodField()
    is_threshold_met_this_year = serializers.SerializerMethodField() # 누적 1000*n 달성 여부 체크
    
    # 시나리오 3을 반영한 정산 대상 판매량 (관리자/작곡가 공통)
    reimbursement_quantity = serializers.SerializerMethodField() 
    # 정산해야 할 금액 (관리자 전용)
    estimated_reimbursement_amount = serializers.SerializerMethodField() 
    
    # 권한별 필드
    composer_ratios = serializers.SerializerMethodField() # 관리자 전용
    my_settlement_paid = serializers.SerializerMethodField() # 작곡가 전용
    

    # --- 공통 로직 ---
    def get_composers_summary(self, obj):
        """ 작곡가 이름 요약: '첫 번째 작곡가 외 N명' """
        composers = obj.composers.all()
        if not composers:
            return "N/A"
        first_composer_name = composers.first().name
        count = composers.count()
        return f"{first_composer_name} 외 {count - 1}명" if count > 1 else first_composer_name

    def get_is_threshold_met_this_year(self, obj):
        """ 해당 연도에 1000*n 임계값을 달성했는지 여부 (RoyaltySettlement 기록 여부 확인) """
        current_year = date.today().year
        return RoyaltySettlement.objects.filter(
            book=obj,
            threshold_met_year=current_year
        ).exists()

    def get_reimbursement_quantity(self, obj):
        """
        시나리오 3을 반영하여, '직전 정산 시점 이후' 달성한 1000*n 단위의 추가 판매량을 계산합니다.
        """
        total_sales = obj.total_cumulative_sales or 0
        if total_sales < 1000:
            return 0 # 시나리오 1: 1000권 미달

        # 직전 정산 시점의 누적 판매량 (is_paid=True 기준)
        last_settled_sales_query = RoyaltySettlement.objects.filter(
            book=obj,
            is_paid=True
        ).order_by('-cumulative_sales_at_settlement').values('cumulative_sales_at_settlement')
        
        last_settled_sales = last_settled_sales_query.first().get('cumulative_sales_at_settlement', 0) if last_settled_sales_query.exists() else 0
        
        # 정산 대상 판매량 계산: (1000의 배수 중 최대치) - (직전 정산 판매량)
        target_sales_multiple = (total_sales // 1000) * 1000
        
        # 정산해야 할 실제 추가 판매량 (1000*n 단위로, 직전 정산 시점을 넘어선 부분만)
        reimb_qty = max(0, target_sales_multiple - last_settled_sales)

        return reimb_qty


    # --- 관리자 전용 로직 ---
    def get_composer_ratios(self, obj):
        """ 관리자 전용: 책의 모든 작곡가별 정산 비율을 조회합니다. """
        request = self.context.get('request')
        if not request or not request.user.is_staff:
            return None 

        ratios = ComposerWork.objects.filter(book=obj).select_related('composer')
        
        ratio_list = [
            {
                'name': cw.composer.name,
                'percentage': float(cw.royalty_percentage) 
            }
            for cw in ratios
        ]
        return ratio_list

    def get_estimated_reimbursement_amount(self, obj):
        """
        관리자 전용: get_reimbursement_quantity를 기반으로 정산 금액을 추정합니다.
        (전체 누적 매출액 * (정산 판매량 / 전체 판매량) * 전체 정산 비율)
        """
        request = self.context.get('request')
        if not request or not request.user.is_staff:
            return None

        reimb_qty = self.get_reimbursement_quantity(obj)
        total_sales = obj.total_cumulative_sales or 1 # 0으로 나누는 것을 방지
        total_revenue = obj.total_cumulative_revenue or decimal.Decimal(0.00)
        
        if reimb_qty == 0 or total_revenue == decimal.Decimal(0.00):
            return decimal.Decimal(0.00)
        
        # 작곡가들의 전체 정산 비율 합산
        total_ratio = ComposerWork.objects.filter(book=obj).aggregate(Sum('royalty_percentage'))['royalty_percentage__sum'] or decimal.Decimal(0.00)

        # 1. 정산 대상 비율 (전체 판매량 중 정산해야 할 판매량의 비율)
        sales_ratio_to_reimburse = decimal.Decimal(reimb_qty) / decimal.Decimal(total_sales)
        
        # 2. 정산해야 할 총 금액 (Revenue * 판매량 비율 * 정산 비율)
        estimated_total_reimbursement = total_revenue * sales_ratio_to_reimburse * (total_ratio / decimal.Decimal(100)) 
        
        return estimated_total_reimbursement.quantize(decimal.Decimal('0.01'))


    # --- 작곡가 전용 로직 ---
    def get_my_settlement_paid(self, obj):
        """ 작곡가 전용: 내가 정산 받았는지 여부를 확인합니다. """
        request = self.context.get('request')
        if not request or not request.user.is_authenticated or request.user.is_staff:
            return None 

        user = request.user
        try:
            current_composer = user.composer_profile 
        except AttributeError:
            return False 
        
        current_year = date.today().year

        # 해당 책, 해당 작곡가, 해당 연도의 정산 기록 중 'is_paid=True'인 레코드가 있는지 확인
        is_paid = RoyaltySettlement.objects.filter(
            book=obj,
            composer=current_composer, 
            threshold_met_year=current_year,
            is_paid=True
        ).exists()
        
        return is_paid

    # --- 최종 출력 포맷팅 ---
    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')

        # 필드 정리 및 포맷팅
        if request and request.user.is_staff:
            # 관리자: 작곡가 전용 필드를 제거
            data.pop('my_settlement_paid', None)
        else:
            # 작곡가: 관리자 전용 필드를 제거하고, 본인에게 필요한 필드만 남김
            data.pop('composer_ratios', None)
            data.pop('estimated_reimbursement_amount', None) # 작곡가에게는 금액을 보여주지 않음 (요청 사항)
        
        # 누적 판매량 필드 제거 (reimbursement_quantity만 남김)
        data.pop('total_cumulative_sales', None)
        data.pop('total_cumulative_revenue', None)
        
        # 금액 필드 콤마 포맷팅 (최종 사용자에게 보여줄 금액 필드만)
        if data.get('estimated_reimbursement_amount') is not None:
             data['estimated_reimbursement_amount'] = f"{data['estimated_reimbursement_amount']:,}"

        return data
    