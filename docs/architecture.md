# Architecture

## Overview

The platform follows a pipeline architecture for incident analysis:

```
Monitoring → Ingestion → AI Analysis → Structured Response
```

## Components

### API Layer (`app/api/chat.py`)
- FastAPI endpoint accepting questions and optional log context
- Input validation via Pydantic models
- Error handling that maps service errors to appropriate HTTP status codes

### RAG Service (`app/services/rag_service.py`)
- Builds context for the LLM from three sources (in priority order):
  1. Logs provided directly in the API request
  2. Log files read from a configurable directory (`LOG_DIR` env var)
  3. Falls back to general knowledge mode when no logs are available
- Constructs a structured prompt requesting Root Cause, Evidence, Fix, and Risk

### LLM Service (`app/services/llm_service.py`)
- Wraps the OpenAI API (gpt-4o-mini, temperature 0.2)
- Handles connection errors, rate limits, and API errors with clear error messages

## Data Flow

```
1. Client sends POST /api/chat with {question, logs?}
2. chat.py validates input, calls rag_service.process_query()
3. rag_service builds context from logs (request → file system → fallback)
4. rag_service constructs structured prompt and calls llm_service.ask_llm()
5. llm_service sends prompt to OpenAI and returns the response
6. Response flows back through the chain to the client
```

## Configuration

| Variable       | Description                        | Default        |
|----------------|------------------------------------|----------------|
| OPENAI_API_KEY | OpenAI API key                     | (required)     |
| LOG_DIR        | Directory to read log files from   | /var/log/app   |
