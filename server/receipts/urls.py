from django.urls import path
from .views import ReceiptUploadInitView, ReceiptListView, ReceiptDetailView

urlpatterns = [
    path("upload/", ReceiptUploadInitView.as_view(), name="receipt-upload-init"),
    path("", ReceiptListView.as_view(), name="receipt-list"),
    path("<int:id>/", ReceiptDetailView.as_view(), name="receipt-detail"),
]
