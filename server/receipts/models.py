from django.db import models
from django.conf import settings

class Receipt(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("PROCESSING", "Processing"),
        ("READY", "Ready"),
        ("FAILED", "Failed"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="receipts")
    file_key = models.CharField(max_length=1024)  # S3 key (user_id/receipt_id/filename)
    ocr_text = models.TextField(null=True, blank=True)
    merchant_name = models.CharField(max_length=255, null=True, blank=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=10, default="INR")
    purchase_date = models.DateTimeField(null=True, blank=True)
    raw_extracted_json = models.JSONField(null=True, blank=True)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="PENDING")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Receipt {self.id} ({self.user.email})"
