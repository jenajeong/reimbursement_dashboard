from django.shortcuts import render
from rest_framework import generics
from rest_framework.permissions import IsAdminUser
from .models import Order
from .serializers import OrderListSerializer, OrderSerializer

class OrderListView(generics.ListAPIView):
    """
    모든 주문 목록을 조회하는 뷰입니다.
    - GET 요청: OrderListSerializer를 사용하여 주문 정보를 반환합니다.
    """
    queryset = Order.objects.all()
    serializer_class = OrderListSerializer
    permission_classes = [IsAdminUser]


class OrderCreateView(generics.CreateAPIView):
    """
    새로운 주문을 생성하는 뷰입니다.
    - POST 요청: OrderSerializer를 사용하여 주문 데이터를 생성합니다.
    """
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAdminUser]


class OrderDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    특정 주문의 상세 정보 조회, 수정 및 삭제를 위한 뷰입니다.
    - GET 요청: OrderSerializer를 사용하여 상세 정보를 조회합니다.
    - PUT/PATCH 요청: 주문 정보를 수정합니다.
    - DELETE 요청: 주문을 삭제합니다.
    """
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAdminUser]
    