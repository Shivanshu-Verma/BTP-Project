import uuid
import boto3
import json
import requests
import os
from django.conf import settings
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Receipt
from .serializers import ReceiptListSerializer, ReceiptDetailSerializer

# Create an S3 client factory
def s3_client():
    session = boto3.session.Session()
    kwargs = {
        "aws_access_key_id": settings.AWS_ACCESS_KEY_ID,
        "aws_secret_access_key": settings.AWS_SECRET_ACCESS_KEY,
        "region_name": settings.AWS_S3_REGION,
    }
    if settings.AWS_S3_ENDPOINT_URL:
        kwargs["endpoint_url"] = settings.AWS_S3_ENDPOINT_URL
    return session.client("s3", **kwargs)

class ReceiptUploadInitView(APIView):
    """
    POST /api/receipts/upload/
    body: { "filename": "receipt.jpg", "content_type": "image/jpeg" }
    returns: { "presigned_url": "...", "file_key": "...", "receipt_id": ... }
    """
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        user = request.user
        filename = request.data.get("filename")
        content_type = request.data.get("content_type", "application/octet-stream")
        if not filename:
            return Response({"detail": "filename is required"}, status=400)

        # Create DB record first with a file_key placeholder
        receipt = Receipt.objects.create(user=user, file_key="pending")
        # Build a deterministic file_key (user/receiptid/filename)
        file_key = f"{user.id}/{receipt.id}/{uuid.uuid4().hex}_{filename}"

        # Update the receipt with file_key
        receipt.file_key = file_key
        receipt.save(update_fields=["file_key"])

        # Generate presigned URL for PUT
        client = s3_client()
        bucket = settings.AWS_S3_BUCKET
        try:
            presigned_url = client.generate_presigned_url(
                "put_object",
                Params={"Bucket": bucket, "Key": file_key, "ContentType": content_type},
                ExpiresIn=60 * 15,  # 15 minutes
            )
        except Exception as e:
            receipt.delete()
            return Response({"detail": "Failed to generate presigned URL", "error": str(e)}, status=500)

        # Call n8n webhook to notify pipeline (it will fetch file after upload or you can send after upload)
        n8n_url = os.getenv("N8N_WEBHOOK_URL")
        if n8n_url:
            payload = {
                "receipt_id": receipt.id,
                "user_id": user.id,
                "file_key": file_key,
            }
            try:
                # fire-and-forget but small timeout
                requests.post(n8n_url, json=payload, timeout=2.0)
            except Exception:
                # ignore: n8n might be offline; pipeline can be triggered later too
                pass

        return Response({"presigned_url": presigned_url, "file_key": file_key, "receipt_id": receipt.id})

class ReceiptListView(generics.ListAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = ReceiptListSerializer

    def get_queryset(self):
        return Receipt.objects.filter(user=self.request.user).order_by("-created_at")

class ReceiptDetailView(generics.RetrieveAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = ReceiptDetailSerializer
    lookup_field = "id"

    def get_queryset(self):
        return Receipt.objects.filter(user=self.request.user)
