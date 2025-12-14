from django.urls import path
from .views import ReceiptUploadInitView, ReceiptListView, ReceiptUpdateView

urlpatterns = [
    path("upload/", ReceiptUploadInitView.as_view(), name="receipt-upload-init"),
    path("", ReceiptListView.as_view(), name="receipt-list"),
    path("<int:id>/", ReceiptUpdateView.as_view(), name="receipt-detail"),
    path("analytics/", ReceiptListView.as_view(), name="receipt-analytics"),
]
