# Receipt Intelligence Platform

Modern receipt ingestion pipeline with:

- Next.js frontend (uploads, dashboard, AI search)
- Django REST backend (auth, receipts API, n8n webhook)
- OCR microservice (FastAPI + Tesseract)
- LLM microservice (FastAPI + Ollama Llama 3.2)
- Automation via n8n, storage in Postgres, vectors in Qdrant

## Repository Layout

- client/ — Next.js app UI
- server/ — Django REST API + n8n webhook
- OCR/ — FastAPI OCR service (Tesseract + pdf2image)
- llama-server/ — FastAPI over local Ollama model

## Prerequisites

- Docker + Docker Compose
- Node.js 18+ (if running frontend locally)
- Python 3.11 (if running backend/OCR locally)
- GPU + NVIDIA drivers for Llama (optional, only for llama-server)

## Quickstart (Docker Compose)

From server/:

1. `cp .env.example .env` and fill secrets (DB, n8n webhook, GCS/Qdrant if used)
2. `docker compose up --build`
3. Open services:
   - Backend API: http://localhost:8000
   - OCR: http://localhost:8001/ocr
   - n8n: http://localhost:5678 (admin/admin by default)
   - Qdrant: http://localhost:6333 (if enabled)

Create Qdrant collection (once):

```bash
curl -X PUT http://localhost:6333/collections/receipts \
  -H "Content-Type: application/json" \
  -d '{"vectors": {"size": 768, "distance": "Cosine"}}'
```

Adjust `size` to your embedding dimension.

## Service Configuration

### Backend (server)

- Env: see server/.env.example for all keys (Django, Postgres, GCS, Qdrant, n8n webhook).
- Docker: builds from server/Dockerfile, applies migrations, runs `runserver` on 8000.
- Depends on: Postgres (db), optional Qdrant.

### OCR (OCR)

- FastAPI `/ocr` multipart file upload, optional `lang`.
- Docker installs tesseract-ocr, poppler-utils, libheif; serves on 8000 (published 8001 in Compose).

### n8n

- Image: n8nio/n8n, port 5678, basic auth admin/admin (change in env).
- Workflows mounted from server/workflows/ (includes receipt pipeline calling OCR and AI).

### Qdrant (optional but included in compose)

- Image: qdrant/qdrant, ports 6333/6334, volume qdrant_data.

### Llama (optional, separate run)

- Build/run from llama-server/ if you need local LLM:
  ```bash
  cd llama-server
  docker build -t llama-http .
  docker run --gpus all -p 8002:8000 --name llama-http --rm llama-http
  ```
- Endpoint: POST http://localhost:8002/ with `{ "prompt": "..." }`.
  Requires GPU and pulls llama3.2 at startup.

## Frontend (client)

- Next.js 16, Tailwind 4, React 19.
- API base currently set to `http://localhost:8000` in client/lib/api.ts. Update for deployments or add `NEXT_PUBLIC_API_BASE` handling if needed.
- Dev: `cd client && npm install && npm run dev` (http://localhost:3000).

## Local Development (without full Compose)

- Backend: `cd server && python -m venv .venv && .venv/Scripts/activate && pip install -r requirements.txt && python manage.py migrate && python manage.py runserver 0.0.0.0:8000`
- OCR: install tesseract-ocr + poppler-utils, then `cd OCR && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && uvicorn main:app --host 0.0.0.0 --port 8000`
- Frontend: `cd client && npm install && npm run dev`

## Key Endpoints

- Backend receipts workflow: see server/receipts/views.py (upload init/complete, view URL, update).
- OCR: POST /ocr (form-data `data` file, optional `lang`), returns `{filename, text}`.
- Llama (optional): POST / with `{prompt}` returning `{response}`.

## Production Notes

- Replace runserver with gunicorn/uvicorn behind a reverse proxy (Nginx/ingress) with TLS.
- Harden n8n credentials, rotate webhook secrets, and restrict ingress.
- Persist volumes: postgres_data, n8n_data, qdrant_data; consider mounting Ollama model cache when using llama-server.
- Set proper CORS/CSRF, secure cookies, and rate limits on auth/AI endpoints.

## Troubleshooting

- Compose YAML parsing: ensure Windows quoting is respected; `docker compose config` should succeed.
- OCR errors: verify tesseract/poppler are installed in the image; test via http://localhost:8001/docs.
- Llama container exits: ensure GPU is available and `docker run --gpus all ...` is used; first start pulls model (can take time).
