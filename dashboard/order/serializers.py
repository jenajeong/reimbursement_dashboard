from rest_framework import serializers
from book.models import Book
from .models import Customer, Order, OrderItem
from decimal import Decimal
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
        fields = ['book', 'book_title', 'quantity', 'discount_rate', 
                  'additional_quantity'] 
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
    order_items = OrderItemSerializer(many=True)
    customer_info_data = serializers.JSONField(write_only=True)
    customer = CustomerSerializer(read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'customer', 'order_date', 'delivery_date', 
            'payment_method', 'payment_date',
            'order_source', 'delivery_method', 'requests', 'order_items', 
            'customer_info_data'
        ]
        
    def create(self, validated_data):
        """
        Customer 및 Order 객체를 생성하고,
        서버에서 직접 OrderItem의 total_price를 계산하여 저장합니다.
        """
        order_items_data = validated_data.pop('order_items')
        customer_data = validated_data.pop('customer_info_data')
        
        customer_serializer = CustomerSerializer(data=customer_data)
        customer_serializer.is_valid(raise_exception=True)
        
        contact_number = customer_data.get('contact_number')
        customer, created = Customer.objects.update_or_create(
            contact_number=contact_number,
            defaults=customer_data
        )
        validated_data['customer'] = customer

        order = Order.objects.create(**validated_data)
        
        for item_data in order_items_data:
            book = item_data['book'] # 유효성 검사를 통과한 Book 인스턴스
            quantity = item_data['quantity']
            discount_rate = item_data.get('discount_rate', Decimal('0.0'))
            # Book 모델과 연결된 최신 가격 정보를 가져옵니다.
            latest_price_history = book.price_histories.order_by('-price_updated_at').first()
            if not latest_price_history:
                raise serializers.ValidationError({
                    'book': f"'{book.title_korean}' 상품의 가격 정보가 없습니다. 관리자에게 문의하세요."
                })
            
            book_price = Decimal(latest_price_history.price)

            discounted_book_price = book_price * (Decimal(1) - (discount_rate / Decimal(100)))
            total_price = round(discounted_book_price * quantity)
            item_data['total_price'] = total_price
            
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

# order/serializers.py (추가)

class AddressLookupSerializer(serializers.Serializer):
    """
    고객 이름과 연락처를 입력받아 기존 주소를 조회하는 Serializer
    """
    customer_name = serializers.CharField(max_length=100)
    contact_number = serializers.CharField(max_length=20)
    
    # 읽기 전용 필드로, 유효성 검사 후 조회된 주소를 반환
    recommended_address = serializers.ReadOnlyField() 
    
    def validate(self, data):
        """
        이름과 연락처로 기존 Customer를 조회하고 주소를 context에 추가
        """
        name = data.get('customer_name')
        contact = data.get('contact_number')

        try:
            # 이름과 연락처가 일치하는 최신 고객의 주소만 가져옴
            customer = Customer.objects.filter(
                name=name,
                contact_number=contact
            ).order_by('-id').first()

            if customer and customer.address:
                # 유효성 검사 후 데이터에 주소 추가
                data['recommended_address'] = customer.address
            else:
                data['recommended_address'] = None
                
        except Exception:
            # DB 조회 오류 시에도 에러를 발생시키지 않고 None 처리
            data['recommended_address'] = None

        return data

class BookSearchSerializer(serializers.ModelSerializer):
    """
    주문 추가 시 책을 검색하기 위한 시리얼라이저 (저자 정보 포함)
    """
    latest_price = serializers.SerializerMethodField()
    
    # [⬇️ 1. 'authors' 필드 추가]
    authors = serializers.SerializerMethodField()

    class Meta:
        model = Book
        # [⬇️ 2. fields 리스트에 'authors' 추가]
        fields = ['id', 'title_korean', 'title_original', 'latest_price', 'authors']

    def get_latest_price(self, book_instance):
        latest_price_obj = book_instance.price_histories.order_by('-price_updated_at').first()
        if latest_price_obj:
            return latest_price_obj.price
        return 0

    # [⬇️ 3. 'authors' 값을 가져오는 메소드 추가]
    def get_authors(self, book_instance):
        """
        M2M으로 연결된 저자들의 이름을 콤마(,)로 연결하여 반환합니다.
        """
        authors_queryset = book_instance.authors.all() # 'author'는 Book 모델의 M2M 필드명
        if not authors_queryset.exists():
            return "-" # 저자 정보가 없으면
        
        # 모든 저자 이름을 콤마로 연결
        return ", ".join([author.name for author in authors_queryset])
    

