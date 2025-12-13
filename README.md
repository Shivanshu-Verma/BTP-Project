# Receipts / Bills Digitalization App

An end-to-end system for uploading, digitizing, searching, and managing receipts and bills. The stack combines a Next.js web UI, Django REST backend, n8n automation/AI pipelines, PostgreSQL, a vector database, and S3-compatible object storage. Security is enforced with JWT, HTTPS, signed URLs, rate limiting, and centralized secrets management.

## Architecture (End-to-End)

```mermaid
flowchart LR
	%% Layout: left (actors/ui) -> center (API) -> right (AI/external); data stores below
	classDef ext fill:#f5f5f5,stroke:#444;
	classDef svc fill:#e8f0ff,stroke:#376fd9;
	classDef data fill:#fef6e4,stroke:#c77c02;
	classDef sec fill:#e9f7ef,stroke:#2f9e44;
	classDef monitor fill:#f2e8ff,stroke:#7b2cbf;

	subgraph Actors
		EU(("End User\nBrowser / Mobile Web")):::ext
		Admin(("System Admin /\nDevOps Engineer")):::ext
		OAuth(("OAuth Identity Provider\n(optional)")):::ext
		LLM(("External LLM Provider")):::ext
		OCR(("External OCR Provider")):::ext
		Notify(("Email/SMS Provider")):::ext
	end

	subgraph Frontend["Next.js Frontend (Web UI)"]
		FEAuth["Auth Pages\n- Login/Signup\n- Password reset / verify"]:::svc
		FEDash["Receipts Dashboard\nFilters, pagination, sorting"]:::svc
		FEUpload["Receipt Upload Page\nFile/camera/PDF, drag-drop, progress"]:::svc
		FEDetail["Receipt Detail Page\nImage/PDF via signed URL; OCR text; structured fields"]:::svc
		FEAi["AI Search & Q&A Page\nChat UI + filters"]:::svc
		FEProfile["User Profile & Settings"]:::svc
		FEClient["HTTP Client Layer\nJWT in secure storage/cookies\nAttaches tokens; handles errors"]:::svc
		FEToast["Error Handling & Toasts"]:::svc
	end

	subgraph Backend["Django Backend (REST API + Business Logic)"]
		APILayer["API Gateway / DRF View Layer\n/auth/*, /receipts/*, /ai/query, /webhooks/n8n, /healthz"]:::svc
		AuthSvc["Auth Service\nJWT access/refresh; password rules; rate limits"]:::svc
		Perm["Permission & Authorization\nPer-user scoping"]:::svc
		UserSvc["User Service\nProfiles, email verify, password reset"]:::svc
		ReceiptSvc["Receipt Service\nCreate receipt; store file URL; status=PENDING"]:::svc
		StorageSvc["Storage Service\nSigned URLs; download links"]:::svc
		SearchSvc["Search & Filter Service\nDB filters; FTS on ocr_text"]:::svc
		AiQuery["AI Query Service (RAG)\nEmbeddings; vector search; LLM answer"]:::svc
		N8NClient["n8n Trigger Client\nPOST webhook on upload"]:::svc
		N8NWebhook["Webhook Handler for n8n\nValidates signature; updates receipt"]:::svc
		ORM["ORM Layer (Django ORM)"]:::svc
	end

	subgraph DataStores
		subgraph PG["Relational Database (PostgreSQL)"]
			PGUsers["users"]:::data
			PGReceipts["receipts"]:::data
			PGSettings["user_settings"]:::data
			PGAudit["audit_logs"]:::data
			PGAux["api_keys / oauth_accounts (opt)"]:::data
		end
		subgraph VDB["Vector Database (RAG Index)"]
			VColl["Receipt Embeddings Collection\nuser_id, receipt_id, chunk_id, vector, metadata"]:::data
		end
		subgraph S3["Object Storage (S3-compatible)"]
			Bucket["Receipts Bucket\n/user_id/receipt_id/original.ext"]:::data
			SignedURL["Signed URL Mechanism"]:::data
		end
	end

	subgraph N8N["n8n Automation & AI Pipelines"]
		N8NUi["n8n Admin UI"]:::svc
		WWebhook["Webhook Trigger: New Receipt"]:::svc
		WMeta["GET Receipt Metadata (Django API)"]:::svc
		WDownload["Download Receipt File (signed URL)"]:::svc
		WScan["Virus/Malware Scan"]:::svc
		WOCR["OCR Processing"]:::svc
		WClean["Text Cleaning & PII masking"]:::svc
		WExtract["LLM Field Extraction"]:::svc
		WEmbed["Embedding Generation"]:::svc
		WWrite["Write Embeddings to Vector DB"]:::svc
		WPatch["Update Receipt in Django"]:::svc
		WNotify["Send Notification (optional)"]:::svc
		WSummary["Scheduled Summaries (cron)"]:::svc
	end

	subgraph Security["Security & Secrets"]
		Secrets["Secrets Manager / Env Config\n(DB creds, storage keys, OCR/LLM/n8n/Email API keys)"]:::sec
		JWTs["JWT Tokens (access + refresh)"]:::sec
		TLS["TLS / HTTPS termination"]:::sec
		WAF["Rate Limiter / WAF"]:::sec
	end

	subgraph Observability["Monitoring & Logging Stack"]
		Logs["Centralized Logs"]:::monitor
		Metrics["Metrics & Dashboards"]:::monitor
		Alerts["Alerting"]:::monitor
	end

	%% Actor connections
	EU -->|"HTTPS"| FEAuth
	EU -->|"HTTPS"| FEDash
	EU -->|"HTTPS"| FEUpload
	EU -->|"HTTPS"| FEDetail
	EU -->|"HTTPS"| FEAi
	EU -->|"HTTPS"| FEProfile
	EU -. "Login with Google (OAuth 2.0/OIDC)" .-> OAuth

	Admin -->|"HTTPS"| N8NUi
	Admin -->|"HTTPS"| APILayer
	Admin -->|"HTTPS"| Logs

	%% Frontend internal
	FEAuth --> FEClient
	FEDash --> FEClient
	FEUpload --> FEClient
	FEDetail --> FEClient
	FEAi --> FEClient
	FEProfile --> FEClient
	FEClient --> FEToast

	%% Frontend to Backend
	FEClient <--> |"HTTPS JSON REST\n/multipart uploads"| APILayer

	%% Backend internals
	APILayer --> AuthSvc
	APILayer --> Perm
	APILayer --> UserSvc
	APILayer --> ReceiptSvc
	APILayer --> StorageSvc
	APILayer --> SearchSvc
	APILayer --> AiQuery
	APILayer --> N8NWebhook
	ReceiptSvc --> N8NClient
	AuthSvc --> JWTs
	ORM --> PGUsers
	ORM --> PGReceipts
	ORM --> PGSettings
	ORM --> PGAudit
	ORM --> PGAux

	%% Backend to data stores
	APILayer -->|"SQL (TLS)"| PG
	AiQuery -->|"Similarity search (gRPC/HTTPS)"| VDB
	N8NWebhook -->|"SQL updates"| PGReceipts
	StorageSvc -->|"Generate signed URL"| SignedURL
	APILayer -->|"Upload/Download via signed URL"| Bucket

	%% Object storage direct/indirect
	FEUpload -->|"PUT via signed URL"| Bucket
	FEDetail -->|"GET via signed URL"| Bucket
	N8N -->|"GET for processing"| Bucket

	%% Django <-> n8n
	N8NClient -->|"HTTPS webhook trigger"| WWebhook
	WWebhook --> WMeta --> WDownload --> WScan --> WOCR --> WClean --> WExtract --> WEmbed --> WWrite --> WPatch --> WNotify
	WWrite -->|"Upsert embeddings"| VColl
	WEmbed -->|"Embeddings"| LLM
	WOCR -->|"OCR request"| OCR
	WExtract -->|"Field extraction"| LLM
	WPatch -->|"PATCH /receipts/{id}"| APILayer

	%% External calls from backend
	APILayer -->|"Password reset / notifications"| Notify
	APILayer -->|"RAG: context + question"| LLM
	APILayer -->|"OAuth token verify"| OAuth

	%% RAG query path
	FEAi -->|"POST /ai/query"| AiQuery
	AiQuery -->|"embedding(query)"| LLM
	AiQuery -->|"top_k search"| VColl
	VColl -->|"relevant chunks"| AiQuery
	AiQuery -->|"question + context"| LLM
	LLM -->|"answer"| AiQuery
	AiQuery -->|"answer + refs"| FEAi

	%% Observability
	APILayer --> Logs
	APILayer --> Metrics
	N8N --> Logs
	N8N --> Metrics
	VDB --> Logs
	PG --> Logs
	Alerts --> Admin

	%% Security & secrets
	Secrets -. "env / secret mount" .-> APILayer
	Secrets -. "env / secret mount" .-> N8N
	Secrets -. "env / secret mount" .-> PG
	Secrets -. "env / secret mount" .-> VDB
	TLS -. "HTTPS everywhere" .-> FEClient
	TLS -. "HTTPS" .-> APILayer
	TLS -. "HTTPS" .-> N8N
	WAF -. "Rate limit /auth, /ai/query" .-> APILayer

	%% Notes (rendering-safe)
	%% Bucket is private; access via signed URLs only
	%% Per-user isolation via user_id or namespace in vector DB
	%% Audit logs for login, uploads, AI queries, downloads
```

## Major Components and Responsibilities

- Next.js Frontend
	- Auth pages (login, signup, reset/verify), dashboard, upload, receipt detail, AI search/Q&A, profile/settings.
	- HTTP client layer handles HTTPS, JWT (httpOnly/secure cookie or secure storage), retries, and error toasts.
	- Optional OAuth login flow with external IdP.

- Django Backend (DRF)
	- API endpoints: /auth/register, /auth/login, /auth/refresh, /auth/logout, /auth/password-reset-request, /auth/password-reset-confirm, /auth/email-verify, /user/profile, /receipts/, /receipts/{id}, /receipts/{id}/download-url, /receipts/search, /ai/query, /webhooks/n8n/receipt-processed, /healthz, /readyz.
	- Auth: JWT access/refresh (e.g., DRF SimpleJWT), password policies, login rate limiting, CSRF/cookie handling for web flows.
	- Domain services: Receipt lifecycle, signed URL generation, search/filter, AI query orchestration (RAG), user notifications.
	- Integrations: triggers n8n on upload; receives n8n callback to update receipts; calls Email/SMS provider; calls LLM for RAG answers.

- n8n Automation & AI Pipelines
	- Workflow: webhook trigger → fetch metadata → download file (signed URL) → malware scan → OCR → clean text/PII masking → LLM field extraction → embeddings → upsert to vector DB → PATCH Django → notify user.
	- Secondary workflow: scheduled summaries via cron, optional LLM summary, send via Email/SMS provider.
	- Admin UI for workflow runs, retries, and logs.

- Data Stores
	- PostgreSQL: users, receipts, user_settings, audit_logs, optional api_keys/oauth_accounts.
	- Vector DB (e.g., Qdrant/pgvector/Pinecone): per-user embeddings for receipts/chunks; used by RAG.
	- Object Storage (S3-compatible): private receipts bucket; signed URLs for upload/download.

- Security & Secrets
	- Secrets manager for all credentials/keys; env-injected.
	- HTTPS everywhere; TLS termination at reverse proxy/load balancer.
	- JWT handling, rate limiting/WAF on auth and AI endpoints.
	- Per-user isolation enforced in PostgreSQL (FK + auth) and vector DB (user_id filters/namespaces).
	- Receipt deletion triggers delete in storage + vector DB + DB row cleanup.

- Monitoring & Logging
	- Centralized logs (Django, n8n, DB, vector DB) with sensitive-data minimization.
	- Metrics: latency, error rates, receipts processed/day, AI query volume.
	- Alerts to admin for anomalies.

## Key Request Flows

### Receipt Upload & Processing
1) User uploads via Next.js → HTTPS to Django (/receipts/ POST multipart) or direct to S3 with signed URL.
2) Django stores metadata (status=PENDING_PROCESSING), triggers n8n webhook.
3) n8n downloads file (signed URL), scans for malware, runs OCR → clean text → LLM extraction → embeddings → vector DB upsert.
4) n8n PATCHes Django with OCR text, structured fields, raw JSON, status=READY; optional notification via Email/SMS provider.

### AI Search / RAG Q&A
1) User submits query from AI Search page → Django /ai/query.
2) Django generates query embedding (LLM provider) → vector DB similarity search (filtered by user_id, date/category, etc.).
3) Top chunks returned; Django calls LLM with question + context; returns answer + references to frontend.

### OAuth (Optional)
1) User selects "Login with Google" → Next.js ↔ OAuth IdP (OAuth 2.0/OIDC).
2) Next.js sends IdP token to Django Auth; Django verifies with IdP, links/creates user, issues JWT.

### Deletion
1) User deletes receipt → Django deletes DB row/marks deleted, calls object storage to delete file, calls vector DB to delete embeddings for receipt_id.

## API Surface (selected)
- Auth: /auth/register, /auth/login, /auth/refresh, /auth/logout, /auth/password-reset-request, /auth/password-reset-confirm, /auth/email-verify
- Users: /user/profile (GET/PATCH)
- Receipts: /receipts/ (GET list, POST upload/create), /receipts/{id} (GET/PATCH/DELETE), /receipts/{id}/download-url (GET signed URL), /receipts/search (GET/POST filters)
- AI: /ai/query (POST)
- Webhooks: /webhooks/n8n/receipt-processed (POST)
- Ops: /healthz, /readyz

## Security Notes
- HTTPS/TLS on every hop; reverse proxy or ingress handles termination.
- JWT access/refresh; httpOnly/secure cookies or secure storage; short-lived access tokens with refresh rotation.
- Rate limiting/WAF on /auth/* and /ai/query; login throttling to deter brute-force.
- Signed URLs for object storage; bucket is private; short expirations.
- Principle of least privilege for service IAM/credentials; secrets never committed.
- Audit logs for auth events, uploads, AI queries, downloads.

## Monitoring & Observability
- Centralized logging (structured), redaction for PII; separate channels for audit.
- Metrics: request latency, error rates, workflow durations, queue/backlog, AI token usage, storage errors.
- Alerts: high error/latency, failed OCR/LLM rates, login failure spikes, storage/DB errors.

## Local Development

### Prerequisites
- Node.js 18+ and npm/pnpm/yarn
- Python 3.11+
- PostgreSQL (or use Docker) and object storage emulator (e.g., MinIO) for local
- n8n (docker or local binary)

### Backend (Django)
1) `cd server`
2) Create venv: `python -m venv .venv && .venv/Scripts/activate`
3) Install deps: `pip install -r requirements.txt`
4) Create `.env` with settings (example):
	 - `DJANGO_SECRET_KEY=...`
	 - `DATABASE_URL=postgresql://user:pass@localhost:5432/btp`
	 - `ALLOWED_HOSTS=localhost,127.0.0.1`
	 - `CORS_ALLOWED_ORIGINS=https://localhost:3000`
	 - `STORAGE_ENDPOINT=http://localhost:9000`
	 - `STORAGE_ACCESS_KEY=...`, `STORAGE_SECRET_KEY=...`, `STORAGE_BUCKET=receipts`
	 - `LLM_API_KEY=...`, `OCR_API_KEY=...`
	 - `EMAIL_API_KEY=...`
	 - `N8N_WEBHOOK_SECRET=...`
5) Run migrations: `python manage.py migrate`
6) Start dev server: `python manage.py runserver 0.0.0.0:8000`

### Frontend (Next.js)
1) `cd client`
2) Install deps: `npm install`
3) Create `.env.local` (example):
	 - `NEXT_PUBLIC_API_BASE=https://localhost:8000`
	 - `NEXT_PUBLIC_STORAGE_BUCKET_BASE=https://localhost:9000`
4) Dev server: `npm run dev` (defaults to http://localhost:3000)

### n8n
- Run via Docker: `docker run -p 5678:5678 -v ~/.n8n:/home/node/.n8n n8nio/n8n`
- Configure webhook URLs to point at Django endpoints; set shared secret.

### Vector DB
- Choose one (Qdrant, pgvector, Pinecone). For local, Qdrant docker: `docker run -p 6333:6333 qdrant/qdrant`.

### Object Storage
- MinIO local: `docker run -p 9000:9000 -p 9001:9001 -e MINIO_ROOT_USER=admin -e MINIO_ROOT_PASSWORD=admin123 minio/minio server /data --console-address :9001`

### Useful Commands
- Backend tests: `cd server && python manage.py test`
- Lint backend (if configured): `ruff server`
- Frontend lint: `cd client && npm run lint`

## Deployment Considerations
- Reverse proxy/ingress with TLS termination; separate services for Django and n8n.
- Use managed PostgreSQL; enable TLS and automated backups.
- Use managed object storage (S3/compatible) with lifecycle policies.
- Secrets manager (e.g., AWS Secrets Manager, Vault); do not store secrets in env files in production images.
- Centralized logging/metrics (e.g., OpenTelemetry → ELK/Loki/Prometheus/Grafana).
- Autoscaling: frontend (static/site), backend API, n8n workers; queueing if needed for heavy OCR/LLM.
- Strict egress controls when calling LLM/OCR providers; mask PII when possible.

## Testing Checklist
- Auth flows: register/login/logout, refresh, password reset, email verify, OAuth.
- Upload flows: success, oversized file, unsupported type, malware-positive.
- n8n workflow: webhook auth, OCR failure, LLM failure, embedding failure retries.
- RAG: per-user isolation, filters, empty results, long queries.
- Signed URLs: expiration, wrong user access, download denial when status not READY.
- Rate limits/WAF: brute-force protection on /auth/* and /ai/query.
- Deletion: removes storage object, vector embeddings, and DB row.

---

This README documents the full architecture, flows, and runbook for the Receipts/Bills Digitalization App. Adapt environment variables and provider choices to your deployment target.
