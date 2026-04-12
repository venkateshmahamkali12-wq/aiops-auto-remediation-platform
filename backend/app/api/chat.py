from fastapi import APIRouter
from pydantic import BaseModel
from app.services.rag_service import process_query

router = APIRouter()

class ChatRequest(BaseModel):
    question: str

@router.post("/chat")
def chat(req: ChatRequest):
    response = process_query(req.question)
    return {"response": response}
