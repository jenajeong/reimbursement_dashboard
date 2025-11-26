from django.urls import path
from .views import ReimbursementListView,ReimbursementHTMXListView, reimbursement_detail_dummy_view, settlement_toggle_dummy_view, ReimbursementBaseView

urlpatterns = [
    path('', ReimbursementBaseView, name='reimbursement_base'),
    path('json/list/', ReimbursementListView.as_view(), name='reimbursement-json-list'),
    path('list/', ReimbursementHTMXListView, name='reimbursement_list'),
    path('<int:book_id>/detail/', reimbursement_detail_dummy_view, name='reimbursement_detail'),
    path('<int:book_id>/settle/', settlement_toggle_dummy_view, name='settlement_toggle'),
]