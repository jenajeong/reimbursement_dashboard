from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Sum

# 외부 모델 임포트 (실제 경로에 맞게 수정 필요)
# order.models에 Order와 OrderItem이, book.models에 Book이 있다고 가정합니다.
from order.models import Order, OrderItem 
from .models import SaleRecord 
import datetime

@receiver(post_save, sender=Order)
def create_sale_record_on_order_paid(sender, instance, created, **kwargs):
    """
    Order 객체가 저장될 때 (업데이트 포함), 결제가 완료된 주문이면 SaleRecord를 생성/업데이트합니다.
    - 주문의 각 OrderItem을 SaleRecord로 집계합니다.
    """
    if instance.payment_date is not None: 
        
        # 1. OrderItem들을 순회하며 SaleRecord를 생성/집계합니다.
        order_items = instance.order_items.all() # OrderItem 모델의 related_name이 'order_items'라고 가정
        
        for item in order_items:
            sale_date = instance.payment_date.date() # 결제일의 날짜만 사용
            
            # 2. 해당 책/해당 날짜의 SaleRecord를 찾거나 새로 생성합니다.
            # (SaleRecord에 unique_together = ('book', 'sale_date') 설정했기 때문에 find/create 사용)
            sale_record, is_new = SaleRecord.objects.get_or_create(
                book=item.book,
                sale_date=sale_date,
                defaults={
                    'quantity_sold': 0,
                    'total_revenue': 0.00
                }
            )
            
            # 3. SaleRecord를 OrderItem 값으로 업데이트/증분합니다.
            # Note: 겹치는 주문을 합산할 필요가 있다면 쿼리셋을 통한 합산 로직을 사용해야 합니다.
            # 지금은 각 OrderItem이 고유한 SaleRecord를 만들도록 단순하게 처리합니다.
            
            # 단순화된 로직: 해당 OrderItem의 수량/금액을 SaleRecord에 기록
            sale_record.quantity_sold += item.quantity # OrderItem의 quantity 필드 사용 가정
            sale_record.total_revenue += item.total_price # OrderItem의 total_price 필드 사용 가정
            sale_record.save() 

# Note: 위의 로직은 결제 완료된 주문이 나중에 수정될 때 중복 계산을 막는 방지책이 필요할 수 있습니다.
# 예를 들어, Order 모델에 'sale_record_created = BooleanField(default=False)'를 추가하고 체크해야 합니다.