from rest_framework import permissions

class IsManager(permissions.BasePermission):
    """
    요청 사용자가 관리자(is_staff=True)인지 확인합니다.
    관리자 유저는 모든 페이지에 접근 권한을 갖습니다.
    """
    def has_permission(self, request, view):
        # CustomUser 모델의 is_manager 헬퍼 메서드를 사용하여 확인
        return request.user and request.user.is_authenticated and request.user.is_manager

class IsGeneralUser(permissions.BasePermission):
    """
    요청 사용자가 일반 유저(is_staff=False)인지 확인합니다.
    일반 유저는 정산 관리 페이지(SettlementOnlyAPIView)에 접근 권한을 갖습니다.
    """
    def has_permission(self, request, view):
        # is_authenticated인지 확인하고, is_manager가 False인지 확인합니다.
        return request.user and request.user.is_authenticated and not request.user.is_manager