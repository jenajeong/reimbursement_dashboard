from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import SignupAPIView, ManagerOnlyAPIView, SettlementOnlyAPIView, signup_form_only, login_form_only, is_logged_in

urlpatterns = [
    # =======================================================
    # 인증 API 엔드포인트
    # =======================================================
    path('api/signup/', SignupAPIView.as_view(), name='api_signup'),
    path('api/login/', TokenObtainPairView.as_view(), name='api_token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='api_token_refresh'),

    # =======================================================
    # 권한 체크 샘플 API 엔드포인트
    # =======================================================
    # 관리자 전용 (is_staff=True)
    path('api/manager-only/', ManagerOnlyAPIView.as_view(), name='api_manager_only'), 
    # 일반 유저 전용 (is_staff=False) (정산 관리 페이지)
    path('api/settlement-only/', SettlementOnlyAPIView.as_view(), name='api_settlement_only'), 

    # =======================================================
    # HTMX용 HTML 폼 엔드포인트
    # =======================================================
    path('forms/signup/', signup_form_only, name='signup_form_only'),
    path('forms/login/', login_form_only, name='login_form_only'),
    path('forms/status/', is_logged_in, name='is_logged_in'), 
]