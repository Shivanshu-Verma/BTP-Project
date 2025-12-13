from rest_framework import serializers
from .models import Receipt

class ReceiptListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Receipt
        fields = ("id", "merchant_name", "total_amount", "purchase_date", "status", "created_at")

class ReceiptDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Receipt
        fields = "__all__"
        read_only_fields = ("user", "created_at", "updated_at")
