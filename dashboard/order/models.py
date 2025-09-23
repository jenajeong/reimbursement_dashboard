from django.db import models
from book.models import Book

class Customer(models.Model):
    """주문자 정보 모델"""
    name = models.CharField(max_length=100, verbose_name="name")
    address = models.CharField(max_length=255, verbose_name="adress")
    contact_number = models.CharField(max_length=20, verbose_name="phone_num")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "customer"
        verbose_name_plural = "customer_list"


class Order(models.Model):
    """주문 목록 모델"""
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='orders', verbose_name="customer")
    order_date = models.DateTimeField(auto_now_add=True, verbose_name="order_date")
    delivery_date = models.DateTimeField(null=True, blank=True, verbose_name="delivery_date")
    order_source = models.CharField(max_length=50, verbose_name="order_source")
    delivery_method = models.CharField(max_length=50, verbose_name="delivery_method")
    requests = models.TextField(blank=True, verbose_name="requests")

    def __str__(self):
        return f"주문 번호: {self.id} ({self.customer.name})"

    class Meta:
        verbose_name = "order_ID"
        verbose_name_plural = "order_list"
        ordering = ['-order_date'] # 최신 주문이 위로 오도록 정렬


class OrderItem(models.Model):
    """주문 상품 목록 모델"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_items', verbose_name="order_ID")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='order_items', verbose_name="book_ID")
    quantity = models.PositiveIntegerField(verbose_name="quantity")
    discount_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, verbose_name="discount_rate")
    additional_item = models.CharField(max_length=100, blank=True, verbose_name="additional_item")
    additional_price = models.IntegerField(verbose_name='additional_price')
    total_price = models.IntegerField(verbose_name='supply_price')

    def __str__(self):
        return f"{self.book.title_korean} - {self.quantity}개"

    class Meta:
        verbose_name = "order_product"
        verbose_name_plural = "order_product_list"
        