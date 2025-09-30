from django.urls import path
from .views import BookSalesListView, AuthorSettlementListView, SettlementListView, SettlementDetailView # 뷰 임포트 추가

urlpatterns = [
    # 1. 책별 판매 집계 조회 (관리자 전용)
    path('books/', BookSalesListView.as_view(), name='book-sales'),
    
    # 2. 저자별 정산 집계 조회 (본인/관리자)
    path('authors/', AuthorSettlementListView.as_view(), name='author-settlement'),

    # 3. 정산 기록 목록 조회 및 연도별 일괄 생성 (관리자 전용)
    path('settlements/', SettlementListView.as_view(), name='settlement-list-create'),
    
    # 4. 특정 정산 기록 상태 업데이트 (관리자 전용)
    path('settlements/<int:pk>/', SettlementDetailView.as_view(), name='settlement-detail-update'),
]