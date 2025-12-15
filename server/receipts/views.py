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
from rest_framework.exceptions import PermissionDenied
from .helper import generate_signed_upload_url, generate_signed_download_url, generate_signed_view_url
from rest_framework.permissions import IsAuthenticated

class ReceiptUploadInitView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        user = request.user
        files = request.data.get("files")

        if not files or not isinstance(files, list):
            return Response({"detail": "files must be a list"}, status=400)

        results = []

        for file in files:
            filename = file.get("filename")
            content_type = file.get("content_type", "application/octet-stream")

            if not filename:
                continue

            # 1️⃣ Create receipt
            receipt = Receipt.objects.create(
                user=user,
                status="PENDING",
                file_key="pending",
            )

            # 2️⃣ Build object path
            object_name = f"{user.id}/{receipt.id}/{uuid.uuid4().hex}_{filename}"

            receipt.file_key = object_name
            receipt.save(update_fields=["file_key"])

            # 3️⃣ Signed PUT URL
            upload_url = generate_signed_upload_url(
                object_name=object_name,
                content_type=content_type,
            )

            results.append({
                "receipt_id": receipt.id,
                "object_name": object_name,
                "upload_url": upload_url,
                "status": receipt.status,
            })

        return Response({"uploads": results})

class ReceiptUploadCompleteView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        user = request.user
        receipt_ids = request.data.get("receipt_ids")

        if not receipt_ids or not isinstance(receipt_ids, list):
            return Response(
                {"detail": "receipt_ids must be a list"},
                status=400
            )

        n8n_url = settings.N8N_WEBHOOK_URL

        receipts = Receipt.objects.filter(
            id__in=receipt_ids,
            user=user,
            status="PENDING",
        )

        for receipt in receipts:
            # 1️⃣ Mark uploaded
            receipt.status = "UPLOADED"
            receipt.save(update_fields=["status"])

            # 2️⃣ Generate signed GET URL
            download_url = generate_signed_download_url(receipt.file_key)

            # 3️⃣ Notify n8n
            if n8n_url:
                try:
                    requests.post(
                        n8n_url,
                        json={
                            "receipt_id": receipt.id,
                            "user_id": user.id,
                            "download_url": download_url,
                        },
                        timeout=5.0,
                    )
                except Exception as e:
                    # IMPORTANT: do not silently fail in production
                    print("Failed to notify n8n:", e)

        return Response({"ok": True})

class ReceiptViewURL(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, receipt_id):
        try:
            receipt = Receipt.objects.get(id=receipt_id)
        except Receipt.DoesNotExist:
            raise NotFound("Receipt not found")

        # 🔐 Ownership check
        if receipt.user != request.user:
            raise PermissionDenied("You do not have access to this receipt")

        GCS_BUCKET_NAME = settings.GCS_BUCKET_NAME
        # print("GCS_BUCKET_NAME:", GCS_BUCKET_NAME)

        signed_url = generate_signed_view_url(
            bucket_name=GCS_BUCKET_NAME,
            blob_name=receipt.file_key,  # e.g. user_id/receipt_id/file.png
        )

        return Response({
            "receipt_id": receipt.id,
            "status": receipt.status,
            "view_url": signed_url,
            "expires_in_minutes": 60,
        })


class ReceiptListView(generics.ListAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = ReceiptListSerializer

    def get_queryset(self):
        return Receipt.objects.filter(user=self.request.user).order_by("-created_at")

class ReceiptUpdateView(generics.RetrieveUpdateAPIView):
    serializer_class = ReceiptDetailSerializer
    lookup_field = "id"

    def get_queryset(self):
        # User access (GET)
        if self.request.method == "GET":
            return Receipt.objects.filter(user=self.request.user)

        # n8n access (PATCH)
        return Receipt.objects.all()

    def get_permissions(self):
        if self.request.method == "GET":
            return [permissions.IsAuthenticated()]
        return []  # PATCH handled manually

    def patch(self, request, *args, **kwargs):
        # 🔐 n8n authentication
        secret = request.headers.get("X-N8N-SECRET")
        if secret != settings.N8N_SECRET:
            raise PermissionDenied("Invalid n8n secret")

        return super().patch(request, *args, **kwargs)
