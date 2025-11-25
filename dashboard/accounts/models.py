from django.contrib.auth.models import AbstractUser
from django.db import models

# CustomUser 모델 정의
# AbstractUser를 상속받아 username(ID 역할), password, email, is_staff(관리자 여부) 등의 필드를 기본으로 가집니다.
class CustomUser(AbstractUser):
    # =======================================================
    # 사용자 정의 필드
    # =======================================================
    name = models.CharField(max_length=150, verbose_name='이름')
    date_of_birth = models.DateField(null=True, blank=True, verbose_name='생년월일')
    contact_number = models.CharField(max_length=15, unique=True, verbose_name='연락처')
    
    # is_staff 필드 (관리자 권한 부여용)
    # is_staff=True이면 관리자(모든 접근 권한), False이면 일반 유저(정산 관리 페이지 접근)로 사용
    
    # =======================================================
    
    def __str__(self):
        # 사용자 이름 대신 ID를 반환
        return self.username

    class Meta:
        verbose_name = '사용자'
        verbose_name_plural = '사용자 목록'

    # 헬퍼 메서드: 사용자 권한 확인
    @property
    def is_manager(self):
        # is_staff는 Django의 기본 필드이며, 관리자 사이트 접근 권한을 제어합니다.
        # 여기서는 is_staff가 True이면 관리자 권한을 가짐을 의미합니다.
        return self.is_staff