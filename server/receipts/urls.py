from django.urls import path
from .views import ReceiptUploadInitView, ReceiptListView, ReceiptUpdateView, ReceiptUploadCompleteView, ReceiptViewURL, AIQueryView

urlpatterns = [
    path("upload/", ReceiptUploadInitView.as_view(), name="receipt-upload-init"),
    path("complete/", ReceiptUploadCompleteView.as_view(), name="receipt-upload-complete"),
    path("", ReceiptListView.as_view(), name="receipt-list"),
    path("<int:id>/", ReceiptUpdateView.as_view(), name="receipt-detail"),
    path("analytics/", ReceiptListView.as_view(), name="receipt-analytics"),
    path("<int:receipt_id>/view-url/", ReceiptViewURL.as_view()),
    path("ai/query/", AIQueryView.as_view()),
]
