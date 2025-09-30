from rest_framework import permissions

class IsAdminUser(permissions.BasePermission):
    """
    Django User 모델의 is_staff 필드를 확인하여 관리자만 접근을 허용합니다.
    """
    message = '이 작업은 관리자(Admin) 계정만 수행할 수 있습니다.'

    def has_permission(self, request, view):
        # 인증된 사용자(request.user.is_authenticated)인지 이미 IsAuthenticated에서 검사하므로,
        # 여기서는 is_staff만 확인합니다.
        return request.user and request.user.is_staff