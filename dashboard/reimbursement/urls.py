from django.urls import path
from .views import BookSalesListView, AuthorSettlementListView

urlpatterns = [
    # 책별 판매 집계 조회 API 엔드포인트
    path('reimbursement/books/', BookSalesListView.as_view(), name='book-sales'),
    
    # 저자별 정산 집계 조회 API 엔드포인트
    path('reimbursement/authors/', AuthorSettlementListView.as_view(), name='author-settlement'),
]
