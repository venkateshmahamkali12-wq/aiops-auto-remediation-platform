# Architecture

## Overview

```
Logs/Alert → AI Analysis → Confidence Score → Approval Gate → Auto-Remediation
                                 │                   │
                           ≥ 0.9 auto-approve    < 0.9 human approval required
```

## Workflow

1. **Analyze** — Submit logs + question → LLM returns structured diagnosis with confidence score (0.0–1.0)
2. **Approval Gate** — High-confidence results (≥ 0.9) are auto-approved; lower scores require human approval
3. **Execute** — Approved remediations execute actions (restart pod, scale up, rollback, etc.)

## Components

### API Layer
- `POST /api/analyze` — Analyze incident, create remediation plan with confidence score
- `GET /api/remediations` — List all remediations (filterable by status)
- `GET /api/remediations/{id}` — Get full remediation details
- `POST /api/remediations/{id}/approve` — Approve a pending remediation
- `POST /api/remediations/{id}/reject` — Reject a pending remediation
- `POST /api/remediations/{id}/execute` — Execute an approved remediation
- `POST /api/chat` — Legacy text-based chat (no remediation workflow)

### RAG Service (`app/services/rag_service.py`)
- Builds context from: request logs → log directory → general knowledge fallback
- Prompts the LLM to return structured JSON with:
  - Root cause, evidence, severity, confidence score
  - Recommended remediation actions with targets and parameters
  - Risk assessment

### LLM Service (`app/services/llm_service.py`)
- OpenAI gpt-4o-mini at temperature 0.2
- Error handling for connection, rate-limit, and API errors

### Remediation Store (`app/services/remediation_store.py`)
- In-memory store tracking remediation lifecycle:
  `pending_approval → approved → executing → completed`
                    `→ rejected`
                                             `→ failed`

### Remediation Executor (`app/services/remediation_executor.py`)
- Maps action types to kubectl commands (dry-run mode)
- Supported actions: restart_pod, scale_up, rollback, increase_memory, increase_cpu, drain_node, cordon_node

## Confidence Score

| Score     | Meaning                                        |
|-----------|-------------------------------------------------|
| 0.9–1.0   | Clear evidence, auto-approved                  |
| 0.7–0.89  | Strong indicators, needs human review           |
| 0.4–0.69  | Probable cause, verification recommended         |
| 0.1–0.39  | Speculative, limited evidence                    |

## Status Lifecycle

```
pending_approval ──approve──► approved ──execute──► executing ──► completed
       │                                                  │
       └──reject──► rejected                              └──► failed
```

## Configuration

| Variable              | Description                            | Default        |
|-----------------------|----------------------------------------|----------------|
| OPENAI_API_KEY        | OpenAI API key                         | (required)     |
| LOG_DIR               | Directory to read log files from       | /var/log/app   |
