from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('book.urls')),
    path('api/', include('order.urls')),  
      
    # DRF가 제공하는 로그인/로그아웃 뷰를 사용
    path('api-auth/', include('rest_framework.urls')),
]