from django.shortcuts import render
from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.settings import api_settings
from rest_framework.authtoken.models import Token 
from .serializers import RegisterSerializer, EmailAuthTokenSerializer

class RegisterView(generics.CreateAPIView):
    """
    회원가입을 위한 API 뷰입니다.
    - POST 요청을 받아 RegisterSerializer를 통해 사용자 계정을 생성합니다.
    - Author 모델에 등록된 작곡가만 가입 가능하도록 유효성 검사를 수행합니다.
    - 접근 권한: AllowAny (누구나 가입 가능)
    """
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny] # 인증되지 않은 사용자도 접근 가능해야 합니다.

    def create(self, request, *args, **kwargs):
        # 시리얼라이저를 사용하여 데이터 유효성 검증 및 사용자 생성 (User와 Author 연결 포함)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # 응답 데이터 구성
        response_data = {
            "message": "회원가입이 성공적으로 완료되었습니다.",
            "username": user.username,
            "email": user.email,
            "user_type": "관리자" if user.is_staff else "작곡가"
        }
        
        headers = self.get_success_headers(serializer.data)
        return Response(response_data, status=status.HTTP_201_CREATED, headers=headers)


class EmailLoginView(ObtainAuthToken):
    """
    이메일과 비밀번호를 사용하여 인증 토큰을 발급받는 커스텀 뷰입니다.
    EmailAuthTokenSerializer를 사용하여 이메일 기반 인증을 처리합니다.
    (로그인 성공 시 토큰과 함께 User ID 및 사용자 유형도 반환합니다.)
    """
    serializer_class = EmailAuthTokenSerializer
    renderer_classes = api_settings.DEFAULT_RENDERER_CLASSES
    
    # 토큰 응답 커스터마이징
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        # 토큰을 생성하거나 기존 토큰을 가져옵니다.
        token, created = Token.objects.get_or_create(user=user)
        
        # 사용자 유형을 판단합니다.
        user_type = "ADMIN" if user.is_staff else "AUTHOR"
        
        return Response({
            'token': token.key,
            'user_id': user.pk,
            'email': user.email,
            'username': user.username,
            'user_type': user_type
        })
