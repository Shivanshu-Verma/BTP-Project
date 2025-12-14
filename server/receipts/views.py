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
from .helper import generate_signed_upload_url, generate_signed_download_url

class ReceiptUploadInitView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        user = request.user
        files = request.data.get("files")

        if not files or not isinstance(files, list):
            return Response(
                {"detail": "files must be a list"},
                status=400
            )

        n8n_url = settings.N8N_WEBHOOK_URL
        results = []

        for file in files:
            filename = file.get("filename")
            content_type = file.get("content_type", "application/octet-stream")

            if not filename:
                continue

            # 1️⃣ Create receipt (DB is source of truth)
            receipt = Receipt.objects.create(
                user=user,
                status="PENDING",
                file_key="pending",
            )

            # 2️⃣ Build GCS object path
            object_name = f"{user.id}/{receipt.id}/{uuid.uuid4().hex}_{filename}"

            receipt.file_key = object_name
            receipt.save(update_fields=["file_key"])

            # 3️⃣ Signed PUT URL (upload)
            upload_url = generate_signed_upload_url(
                object_name=object_name,
                content_type=content_type,
            )

            # 4️⃣ Signed GET URL (for n8n processing)
            download_url = generate_signed_download_url(object_name)

            # 5️⃣ Notify n8n (fire-and-forget)
            if n8n_url:
                try:
                    requests.post(
                        n8n_url,
                        json={
                            "receipt_id": receipt.id,
                            "user_id": user.id,
                            "download_url": download_url,
                        },
                        timeout=2.0,
                    )
                except Exception:
                    pass

            results.append({
                "receipt_id": receipt.id,
                "object_name": object_name,
                "upload_url": upload_url,
                "status": receipt.status,
            })

        return Response({"uploads": results})


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
