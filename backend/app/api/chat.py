import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.rag_service import process_query

logger = logging.getLogger(__name__)
router = APIRouter()


class ChatRequest(BaseModel):
    question: str
    logs: Optional[str] = None


@router.post("/chat")
def chat(req: ChatRequest):
    try:
        response = process_query(req.question, logs=req.logs)
        return {"response": response}
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception:
        logger.exception("Unexpected error in /chat")
        raise HTTPException(status_code=500, detail="Internal server error")
