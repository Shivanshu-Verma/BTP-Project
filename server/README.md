# Backend (Django + n8n webhook)

Exposes REST APIs for auth/receipts and a webhook endpoint consumed by n8n. Uses Postgres for data, optional Qdrant for vectors, and triggers OCR/LLM via workflows.

## Setup

```bash
cd server
cp .env.example .env   # fill values
python -m venv .venv && .venv/Scripts/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

## Environment

See [.env.example](.env.example). Key entries:

- `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`
- `GCS_BUCKET_NAME`, `GOOGLE_APPLICATION_CREDENTIALS`
- `QDRANT_URL`, `QDRANT_API_KEY`
- `API_KEY` (app-level)
- `N8N_WEBHOOK_URL`, `N8N_WEBHOOK_SECRET`

## Docker Compose

From server/:

```bash
docker compose up --build
```

Services: Postgres (5432), backend (8000), OCR (8001), n8n (5678), Qdrant (6333/6334). Backend waits for DB health; n8n uses workflows from server/workflows/.

## Qdrant Collection (once)

```bash
curl -X PUT http://localhost:6333/collections/receipts \
  -H "Content-Type: application/json" \
  -d '{"vectors": {"size": 3072, "distance": "Cosine"}}'
```

Adjust `size` to your embedding dimension.

## Key Endpoints (Django)

- Receipt upload init/complete, signed view URL, update (n8n callback) in receipts/views.py.
- Auth endpoints (SimpleJWT) and user profile endpoints (see authapp).
- Ops: add /healthz if deploying behind probes.

## n8n Workflow

- Webhook URL configured via `N8N_WEBHOOK_URL` in backend env.
- Pipeline steps (in server/workflows/receipt_pipeline.json): download via signed URL → OCR (http://host.docker.internal:8001/ocr) → LLM extraction → embeddings → Qdrant upsert → PATCH backend.

## Production Notes

- Run Django with gunicorn/uvicorn behind Nginx/ingress with TLS.
- Harden n8n credentials and limit ingress; rotate webhook secret.
- Persist Postgres volume; back up regularly.
- Apply CORS/CSRF settings for your frontend origin.
