## Receipt Processing Pipeline

### Tech Stack
- Django REST Framework
- n8n (workflow orchestration)
- Google Gemini (OCR + embeddings)
- Qdrant (vector search)
- Docker Compose

### How to Run

1. Clone the repo
2. Copy env file:
   cp .env.example .env
3. Fill API keys
4. Run:
   docker compose up --build
5. Open:
   - Backend: http://localhost:8000
   - n8n: http://localhost:5678 (admin/admin)

### Workflow
- Receipt upload triggers n8n pipeline
- OCR → AI extraction → embeddings → Qdrant
- Django updated at each stage
