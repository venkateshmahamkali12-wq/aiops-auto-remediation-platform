# AI-Powered AIOps Auto-Remediation Platform

An AI-powered incident analysis and auto-remediation platform. Submit logs, get a structured diagnosis with a confidence score, approve or auto-approve the fix, and execute remediation actions.

## Architecture

```
Logs → AI Analysis → Confidence Score → Approval Gate → Auto-Remediation
                          │                    │
                    ≥ 0.9 auto-approve    < 0.9 human review
```

See [docs/architecture.md](docs/architecture.md) for full details.

## Quick Start

```bash
cp .env.example .env    # Set OPENAI_API_KEY
docker-compose up --build
```

API available at `http://localhost:8000`.

## API Usage

### 1. Analyze an Incident

```bash
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Why is the pod crashing?",
    "logs": "2024-01-15 ERROR OOMKilled container web-app memory limit 512Mi"
  }'
```

Response includes `confidence_score`, `severity`, `root_cause`, `recommended_actions`, and whether it was `auto_approved`.

### 2. Approve (if not auto-approved)

```bash
curl -X POST http://localhost:8000/api/remediations/{id}/approve \
  -H "Content-Type: application/json" \
  -d '{"approved_by": "alice"}'
```

### 3. Execute Remediation

```bash
curl -X POST http://localhost:8000/api/remediations/{id}/execute
```

### Other Endpoints

- `GET /api/remediations` — List all remediations
- `GET /api/remediations/{id}` — Get remediation details
- `POST /api/remediations/{id}/reject` — Reject a remediation
- `POST /api/chat` — Legacy text-based analysis

## Development

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload    # Run server
pytest tests/ -v                 # Run tests (26 tests)
```

## Project Structure

```
backend/
├── app/
│   ├── main.py                      # FastAPI app + router setup
│   ├── models.py                    # Pydantic models (AnalysisResult, Remediation, etc.)
│   ├── api/
│   │   ├── chat.py                  # POST /api/chat (legacy)
│   │   └── remediation.py          # Analyze, approve, reject, execute endpoints
│   └── services/
│       ├── llm_service.py           # OpenAI integration
│       ├── rag_service.py           # Context building + structured analysis
│       ├── remediation_store.py     # In-memory remediation store
│       └── remediation_executor.py  # Action execution (kubectl dry-run)
├── tests/
│   ├── test_api.py                  # 12 API tests
│   └── test_services.py            # 14 service tests
├── Dockerfile
└── requirements.txt
```
