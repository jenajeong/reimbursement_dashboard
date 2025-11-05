from django import forms
from django.forms import inlineformset_factory
from .models import Customer, Order, OrderItem

class CustomerForm(forms.ModelForm):
    """
    주문자 정보(신규 또는 기존)를 다루는 폼
    """
    class Meta:
        model = Customer
        fields = ['name', 'address', 'contact_number']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_number': forms.TextInput(attrs={'class': 'form-control'}),
        }

class OrderForm(forms.ModelForm):
    """
    주문 기본 정보(배송, 출처, 결제 등)를 다루는 폼
    """
    class Meta:
        model = Order
        # customer, order_date, delivery_date, payment_date는 폼에서 제외
        fields = ['order_source', 'delivery_method', 'payment_method', 'requests'] # 'payment_method' 추가
        widgets = {
            'order_source': forms.TextInput(attrs={'class': 'form-control'}),
            'delivery_method': forms.TextInput(attrs={'class': 'form-control'}),
            'payment_method': forms.Select(attrs={'class': 'form-control'}), # Select 위젯으로 변경
            'requests': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class OrderItemForm(forms.ModelForm):
    """
    개별 주문 항목(책)을 다루는 폼 (FormSet의 기반이 됨)
    """
    class Meta:
        model = OrderItem
        # order는 FormSet이 자동으로 처리
        fields = ['book', 'quantity', 'discount_rate', 'additional_item', 'additional_price', 'total_price']
        widgets = {
            'book': forms.Select(attrs={'class': 'form-control book-select'}), # 나중에 Select2 같은 라이브러리 적용 고려
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'discount_rate': forms.NumberInput(attrs={'class': 'form-control'}),
            'additional_item': forms.TextInput(attrs={'class': 'form-control'}),
            'additional_price': forms.NumberInput(attrs={'class': 'form-control'}),
            'total_price': forms.NumberInput(attrs={'class': 'form-control'}),
        }

# Order(부모)와 OrderItem(자식)을 연결하는 인라인 폼셋 정의
OrderItemFormSet = inlineformset_factory(
    Order,                  # 부모 모델
    OrderItem,              # 자식 모델
    form=OrderItemForm,     # 위에서 정의한 OrderItemForm을 사용
    extra=1,                # 기본으로 보여줄 빈 폼의 개수 (1개부터 시작)
    can_delete=True,        # 폼 삭제 기능 활성화
    min_num=1,              # 최소 1개의 폼은 있어야 함
    validate_min=True,
)