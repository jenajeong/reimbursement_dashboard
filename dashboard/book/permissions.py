from rest_framework import permissions


class IsAuthorOrAdmin(permissions.BasePermission):
    """
    요청 사용자가 해당 저자 객체의 정보와 일치하거나 관리자인지 확인하는 커스텀 권한 클래스.
    """
    def has_object_permission(self, request, view, obj):
        # 관리자(is_staff)는 모든 권한을 가집니다.
        if request.user and request.user.is_staff:
            return True
        return False