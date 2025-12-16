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
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from rest_framework.exceptions import ValidationError

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

class AIQueryView(APIView):
    """
    POST /ai/query
    {
      "query": "How much did I spend on Amazon last month?"
    }
    """

    permission_classes = [IsAuthenticated]

    # --- CONFIG ---
    COLLECTION_NAME = "receipts"
    TOP_K = 5

    QDRANT_URL = os.getenv("QDRANT_URL")
    QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

    # --- INIT SHARED OBJECTS ---
    embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

    qdrant = QdrantClient(
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY,
    )

    def post(self, request):
        question = request.data.get("query")

        if not question:
            raise ValidationError({"query": "This field is required."})

        # 1️⃣ Embed the query (FREE, local)
        query_vector = self.embedding_model.encode(question).tolist()

        # 2️⃣ Search Qdrant Cloud (user-scoped)
        hits = self.qdrant.search(
            collection_name=self.COLLECTION_NAME,
            query_vector=query_vector,
            limit=self.TOP_K,
            with_payload=True,
            query_filter={
                "must": [
                    {
                        "key": "user_id",
                        "match": {"value": request.user.id},
                    }
                ]
            },
        )

        if not hits:
            return Response({
                "answer": "I couldn't find any relevant receipts.",
                "sources": [],
            })

        # 3️⃣ Build context
        context_blocks = []
        source_receipts = set()

        for hit in hits:
            payload = hit.payload or {}

            context_blocks.append(
                f"""
Merchant: {payload.get("merchant_name")}
Amount: {payload.get("total_amount")}
Text: {payload.get("ocr_text")}
""".strip()
            )

            if payload.get("receipt_id"):
                source_receipts.add(payload["receipt_id"])

        context = "\n\n---\n\n".join(context_blocks)

        # 4️⃣ Prompt
        prompt = f"""
You are an assistant answering questions using receipt data.

Context:
{context}

Question:
{question}

Answer clearly and concisely. If unsure, say you don't know.
"""

        # 5️⃣ Call Gemini LLM
        llm_response = requests.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
            headers={
                "Content-Type": "application/json",
                "X-goog-api-key": self.GEMINI_API_KEY,
            },
            json={
                "contents": [
                    {"parts": [{"text": prompt}]}
                ]
            },
            timeout=30,
        )

        if not llm_response.ok:
            return Response(
                {"error": "LLM call failed"},
                status=500,
            )

        llm_data = llm_response.json()

        answer = (
            llm_data
            .get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "Unable to generate answer.")
        )

        # 6️⃣ Return response
        return Response({
            "answer": answer,
            "sources": list(source_receipts),
        })
