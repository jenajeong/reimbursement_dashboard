from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import render, redirect

def home_view(request):
    return render(request, 'home.html')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('order/', include('order.urls')),
    path('book/', include('book.urls')),
    # path('api/', include('reimbursement.urls')),
    # path('api/', include('book.urls')),
    path('accounts/', include('accounts.urls')), 
    path('', home_view, name='home'),
    # DRF가 제공하는 로그인/로그아웃 뷰를 사용
    path('api-auth/', include('rest_framework.urls')),
    path('reimbursement/', include('reimbursement.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)