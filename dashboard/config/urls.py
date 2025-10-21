from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('order/', include('order.urls')),
    path('book/', include('book.urls')),
    # path('api/', include('reimbursement.urls')),
    # path('api/', include('book.urls')),
      
    # DRF가 제공하는 로그인/로그아웃 뷰를 사용
    path('api-auth/', include('rest_framework.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)