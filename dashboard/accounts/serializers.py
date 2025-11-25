from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from .models import CustomUser

class CustomUserSerializer(serializers.ModelSerializer):
    """
    회원가입을 위한 사용자 Serializer.
    비밀번호는 저장 시 해시 처리됩니다.
    """
    class Meta:
        model = CustomUser
        # 회원가입 시 받을 필드 목록
        fields = ('username', 'password', 'name', 'date_of_birth', 'contact_number')
        
        # password는 응답 시 제외하고, 필수 입력값으로 설정
        extra_kwargs = {
            'password': {'write_only': True, 'required': True}
        }

    def create(self, validated_data):
        # is_staff(관리자 권한)는 기본적으로 False로 설정하여 일반 유저로 생성
        validated_data['is_staff'] = False 
        
        # 비밀번호 해시 처리
        validated_data['password'] = make_password(validated_data.get('password'))
        
        return super().create(validated_data)