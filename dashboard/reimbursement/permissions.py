from rest_framework import permissions

class IsManagerOrComposer(permissions.BasePermission):
    """
    관리자(is_staff=True) 또는 일반 사용자(작곡가)만 접근을 허용합니다.
    관리자는 모든 것을 볼 수 있으며, 작곡가는 본인 관련 데이터만 볼 수 있도록 뷰에서 추가 필터링합니다.
    """
    def has_permission(self, request, view):
        # 인증된 사용자만 접근 가능
        return request.user and request.user.is_authenticated