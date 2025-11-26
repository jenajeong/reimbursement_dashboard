# reimbursement/apps.py (수정)

from django.apps import AppConfig

class ReimbursementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'reimbursement'

    def ready(self):
        """
        앱이 로드될 때 signals를 등록합니다.
        """
        import reimbursement.signals