from django.shortcuts import render
from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from .serializers import CustomUserSerializer
from .permissions import IsManager, IsGeneralUser

# =======================================================
# 1. API 뷰 (JSON 응답)
# =======================================================

# 회원가입 API: CustomUser를 생성하고 일반 사용자 권한(is_staff=False)을 부여
class SignupAPIView(generics.CreateAPIView):
    serializer_class = CustomUserSerializer
    permission_classes = [AllowAny]
    authentication_classes = [] 

# 관리자만 접근 가능한 샘플 API
class ManagerOnlyAPIView(APIView):
    # 권한 설정: IsManager 퍼미션 사용
    permission_classes = [IsAuthenticated, IsManager] 

    def get(self, request):
        return Response({
            "message": "관리자 전용 페이지 접근 성공!",
            "user_id": request.user.username,
            "role": "Manager"
        })

# 일반 유저만 접근 가능한 샘플 API (정산 관리 페이지)
class SettlementOnlyAPIView(APIView):
    # 권한 설정: IsGeneralUser 퍼미션 사용
    permission_classes = [IsAuthenticated, IsGeneralUser] 

    def get(self, request):
        return Response({
            "message": "정산 관리 페이지 접근 성공! (일반 유저 전용)",
            "user_id": request.user.username,
            "role": "General User"
        })

# =======================================================
# 2. HTMX 폼 로드 뷰 (HTML Fragment 응답)
# =======================================================

# 로그인 폼만 보여주는 뷰
def login_form_only(request):
    return render(request, 'accounts/login_form.html')

# 회원가입 폼만 보여주는 뷰
def signup_form_only(request):
    return render(request, 'accounts/signup_form.html')

# 로그인 성공 후 상태를 보여주는 뷰
def is_logged_in(request):
    return render(request, 'accounts/is_logged_in.html')