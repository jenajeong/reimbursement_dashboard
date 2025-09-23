from rest_framework import serializers
from .models import Customer, Order, OrderItem
import re

class CustomerSerializer(serializers.ModelSerializer):
    """
    주문자 모델을 위한 시리얼라이저
    이름 및 전화번호 유효성 검사 로직 추가
    """
    class Meta:
        model = Customer
        fields = '__all__'

    def validate_name(self, value):
        # 공백이 포함되어 있는지 확인
        if ' ' in value:
            raise serializers.ValidationError("이름에 공백을 사용할 수 없습니다.")

        # 한글, 영문, 숫자만 허용하는 정규 표현식
        if not re.match(r'^[가-힣a-zA-Z]+$', value):
            raise serializers.ValidationError("이름에는 한글, 영문만 사용할 수 있습니다.")
        
        return value

    def validate_contact_number(self, value):
        # '-'를 제외한 숫자의 길이가 11자리를 초과하면 오류
        number_only = value.replace('-', '')
        if len(number_only) > 11:
            raise serializers.ValidationError("전화번호는 11자리를 초과할 수 없습니다.")
        
        # '숫자-숫자-숫자' 형식이 아니면 오류
        # 정규식 패턴: 첫 그룹(2~3자리), 둘째 그룹(3~4자리), 셋째 그룹(4자리)
        pattern = re.compile(r'^\d{2,3}-\d{3,4}-\d{4}$')
        if not pattern.match(value):
            raise serializers.ValidationError("전화번호 형식이 올바르지 않습니다. (예: 010-1234-5678)")
        
        return value



class OrderItemSerializer(serializers.ModelSerializer):
    """
    주문 상품 목록 모델을 위한 시리얼라이저 (중첩 시리얼라이저)
    """
    book_title = serializers.ReadOnlyField(source='book.title_korean')
    
    class Meta:
        model = OrderItem
        fields = ['book', 'book_title', 'quantity', 'discount_rate', 'additional_item', 'total_price']
        extra_kwargs = {
            'book': {'write_only': True}
        }

    def validate_discount_rate(self, value):
        """
        할인율은 100%를 초과할 수 없습니다.
        """
        if value > 100:
            raise serializers.ValidationError("할인율은 100%를 초과할 수 없습니다.")
        return value


class OrderSerializer(serializers.ModelSerializer):
    customer_info = CustomerSerializer(read_only=True)
    order_items = OrderItemSerializer(many=True)

    class Meta:
        model = Order
        fields = [
            'id', 'customer', 'customer_info', 'order_date', 'delivery_date', 
            'order_source', 'delivery_method', 'requests', 'order_items'
        ]
        read_only_fields = []

    def validate(self, data):
        """
        주문일자가 배송일자보다 빠르거나 같아야 합니다.
        """
        order_date = data.get('order_date')
        delivery_date = data.get('delivery_date')

        # 배송일자가 존재할 경우에만 검사
        if delivery_date and order_date and order_date > delivery_date:
            raise serializers.ValidationError(
                {'delivery_date': '배송일은 주문일보다 늦은 날짜여야 합니다.'}
            )

        return data

    def create(self, validated_data):
        """
        유효성 검사가 완료된 데이터로 객체를 생성합니다.
        """
        order_items_data = validated_data.pop('order_items')
        order = Order.objects.create(**validated_data)
        
        for item_data in order_items_data:
            OrderItem.objects.create(order=order, **item_data)
        
        return order

class TotalPriceSerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(source='book.title_korean')

    class Meta:
        model = OrderItem
        fields = ['book_title', 'quantity']

    def get_amount(self, obj):
        # 수량 * (공급가 * (1 - 할인율))
        final_price = obj.supply_price * (1 - obj.discount_rate / 100)
        return int(obj.quantity * final_price)


class OrderListSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name')
    customer_contact_number = serializers.CharField(source='customer.contact_number')
    order_items = TotalPriceSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'order_date', 'delivery_date', 'customer_name', 'customer_contact_number', 'order_items']   
