# AI-Powered AIOps Auto-Remediation Platform

A DevOps incident analysis platform that uses LLM-powered reasoning to diagnose infrastructure issues from logs and metrics. Submit logs and a question, and get structured analysis with root cause, evidence, recommended fix, and risk assessment.

## Architecture

```
User / Alert ──► FastAPI ──► RAG Service ──► LLM Service ──► OpenAI
                  (API)      (context)       (gpt-4o-mini)
```

See [docs/architecture.md](docs/architecture.md) for details.

## Quick Start

```bash
# 1. Configure your API key
cp .env.example .env
# Edit .env and set OPENAI_API_KEY

# 2. Run with Docker
docker-compose up --build
```

The API is available at `http://localhost:8000`.

## API

### Health Check

```
GET /
```

Returns `{"status": "ok"}`.

### Chat / Analyze

```
POST /api/chat
Content-Type: application/json

{
  "question": "Why is the pod crashing?",
  "logs": "2024-01-15 ERROR OOMKilled container web-app memory limit 512Mi"
}
```

The `logs` field is optional. When provided, the LLM uses them as context for its analysis. Without logs, it answers based on general DevOps knowledge.

**Response:**

```json
{
  "response": "## Root Cause\n..."
}
```

## Development

```bash
cd backend
pip install -r requirements.txt

# Run locally
uvicorn app.main:app --reload

# Run tests
pytest tests/ -v
```

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI app, health check, logging config
│   ├── api/
│   │   └── chat.py          # POST /api/chat endpoint
│   └── services/
│       ├── llm_service.py   # OpenAI integration with error handling
│       └── rag_service.py   # Context building and prompt construction
├── tests/
│   ├── test_api.py          # API endpoint tests
│   └── test_services.py     # Service unit tests
├── Dockerfile
└── requirements.txt
```
