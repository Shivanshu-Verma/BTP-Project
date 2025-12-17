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
import time
import traceback
# from qdrant_client import QdrantClient
# from sentence_transformers import SentenceTransformer
# from rest_framework.exceptions import ValidationError

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
    POST /api/ai/query/
    {
      "question": "How much did I pay to AARYAN?"
    }
    """

    permission_classes = [IsAuthenticated]

    TOP_K = 5

    def post(self, request):

        t0 = time.time()

        def dbg(msg, **kwargs):
            prefix = "[AIQueryView]"
            if kwargs:
                print(prefix, msg, "|", json.dumps(kwargs, default=str))
            else:
                print(prefix, msg)

        dbg("ENTER post()", user_id=getattr(request.user, "id", None))
        dbg("Incoming request.data keys", keys=list(getattr(request, "data", {}).keys()))

        # accept both "query" and "question" to reduce client mismatch issues
        question = request.data.get("query") or request.data.get("question")
        dbg("Parsed question", has_question=bool(question), length=(len(question) if question else 0))

        if not question:
            dbg("BAD REQUEST: missing question/query field")
            return Response(
                {"error": "question is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user_id = request.user.id
        dbg("Resolved user_id", user_id=user_id)

        # 1️⃣ Generate query embedding (Gemini)
        try:
            embed_url = (
                f"https://generativelanguage.googleapis.com/v1beta/"
                f"{settings.GEMINI_EMBED_MODEL}:embedContent"
                f"?key={settings.GEMINI_API_KEY}"
            )
            safe_embed_url = embed_url.split("?key=")[0] + "?key=<redacted>"
            dbg("STEP 1: embedding request prepared", url=safe_embed_url, model=str(settings.GEMINI_EMBED_MODEL))

            embed_payload = {"content": {"parts": [{"text": question}]}}
            dbg("STEP 1: embedding payload prepared", payload_size=len(json.dumps(embed_payload)))

            t1 = time.time()
            embed_resp = requests.post(embed_url, json=embed_payload, timeout=15)
            dbg(
                "STEP 1: embedding response received",
                status_code=embed_resp.status_code,
                elapsed_ms=int((time.time() - t1) * 1000),
            )

            if embed_resp.status_code >= 400:
                dbg(
                    "STEP 1: embedding error body",
                    body_preview=embed_resp.text[:1500],
                )

            embed_resp.raise_for_status()

            embed_json = embed_resp.json()
            dbg("STEP 1: embedding JSON parsed", top_keys=list(embed_json.keys()))

            query_vector = embed_json["embedding"]["values"]
            dbg("STEP 1: embedding vector extracted", vector_len=len(query_vector))
        except Exception as e:
            dbg("STEP 1 FAILED: embedding generation", error=str(e))
            dbg("TRACEBACK", tb=traceback.format_exc())
            return Response(
                {"error": "Embedding generation failed. Check server logs for details."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # 2️⃣ Qdrant semantic search (user-scoped)
        try:
            search_url = (
                f"{settings.QDRANT_URL}/collections/"
                f"{settings.QDRANT_COLLECTION}/points/search"
            )
            dbg("STEP 2: qdrant search prepared", url=search_url, collection=str(settings.QDRANT_COLLECTION))

            search_payload = {
                "vector": query_vector,
                "limit": self.TOP_K,
                "with_payload": True,
                "filter": {
                    "must": [
                        {"key": "user_id", "match": {"value": user_id}},
                    ]
                },
            }
            dbg("STEP 2: qdrant payload prepared", limit=self.TOP_K, payload_size=len(json.dumps(search_payload)))

            t2 = time.time()
            search_resp = requests.post(search_url, json=search_payload, timeout=10)
            dbg(
                "STEP 2: qdrant response received",
                status_code=search_resp.status_code,
                elapsed_ms=int((time.time() - t2) * 1000),
            )

            if search_resp.status_code >= 400:
                dbg("STEP 2: qdrant error body", body_preview=search_resp.text[:1500])

            search_resp.raise_for_status()

            search_json = search_resp.json()
            dbg("STEP 2: qdrant JSON parsed", top_keys=list(search_json.keys()))

            results = search_json.get("result", [])
            dbg("STEP 2: qdrant results extracted", result_count=len(results))
        except Exception as e:
            dbg("STEP 2 FAILED: qdrant search", error=str(e))
            dbg("TRACEBACK", tb=traceback.format_exc())
            return Response(
                {"error": "Vector search failed. Check server logs for details."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        if not results:
            dbg("NO RESULTS: returning fallback answer", total_elapsed_ms=int((time.time() - t0) * 1000))
            return Response(
                {
                    "answer": "I do not have enough information to answer that.",
                    "sources": [],
                }
            )

        # 3️⃣ Build grounded context
        try:
            dbg("STEP 3: building context from results")
            context_blocks = []
            source_receipts = set()

            for idx, r in enumerate(results):
                payload = r.get("payload", {}) or {}
                content = payload.get("content", "") or ""
                receipt_id = payload.get("receipt_id")

                dbg(
                    "STEP 3: result item",
                    idx=idx,
                    has_payload=bool(payload),
                    content_len=len(content),
                    receipt_id=receipt_id,
                )

                context_blocks.append(content)

                if receipt_id:
                    source_receipts.add(receipt_id)

            context = "\n\n---\n\n".join(context_blocks)
            dbg(
                "STEP 3: context built",
                blocks=len(context_blocks),
                context_len=len(context),
                sources_count=len(source_receipts),
            )
        except Exception as e:
            dbg("STEP 3 FAILED: context building", error=str(e))
            dbg("TRACEBACK", tb=traceback.format_exc())
            return Response(
                {"error": "Failed to build context. Check server logs for details."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # 4️⃣ Strict RAG prompt (anti-hallucination)
        prompt = f"""
You are an AI assistant answering questions strictly using the provided context.

Context:
{context}

Question:
{question}

Rules:
- Use ONLY the context above.
- If the answer is not present, say:
  "I do not have enough information to answer that."
""".strip()
        dbg("STEP 4: prompt prepared", prompt_len=len(prompt))

        # 5️⃣ Generate final answer (Gemini text model)
        try:
            gen_url = (
                f"https://generativelanguage.googleapis.com/v1beta/"
                f"models/{settings.GEMINI_TEXT_MODEL}:generateContent"
                f"?key={settings.GEMINI_API_KEY}"
            )
            safe_gen_url = gen_url.split("?key=")[0] + "?key=<redacted>"
            dbg("STEP 5: generation request prepared", url=safe_gen_url, model=str(settings.GEMINI_TEXT_MODEL))

            gen_payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.2},
            }
            dbg("STEP 5: generation payload prepared", payload_size=len(json.dumps(gen_payload)))

            t3 = time.time()
            gen_resp = requests.post(gen_url, json=gen_payload, timeout=30)
            dbg(
                "STEP 5: generation response received",
                status_code=gen_resp.status_code,
                elapsed_ms=int((time.time() - t3) * 1000),
            )

            if gen_resp.status_code >= 400:
                dbg("STEP 5: generation error body", body_preview=gen_resp.text[:1500])

            gen_resp.raise_for_status()

            gen_json = gen_resp.json()
            dbg("STEP 5: generation JSON parsed", top_keys=list(gen_json.keys()))

            answer = (
                gen_json.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "Unable to generate answer.")
            )
            dbg("STEP 5: answer extracted", answer_len=len(answer))
        except Exception as e:
            dbg("STEP 5 FAILED: answer generation", error=str(e))
            dbg("TRACEBACK", tb=traceback.format_exc())
            return Response(
                {"error": "Answer generation failed. Check server logs for details."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        dbg("SUCCESS: returning response", total_elapsed_ms=int((time.time() - t0) * 1000))
        return Response(
            {
                "answer": answer,
                "sources": list(source_receipts),
            }
        )
