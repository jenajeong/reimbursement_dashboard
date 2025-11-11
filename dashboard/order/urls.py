from .views import order_list
from django.urls import path

urlpatterns = [

    path('', order_list, name='order_list'),
]

