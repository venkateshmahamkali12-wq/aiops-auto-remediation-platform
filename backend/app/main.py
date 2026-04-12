from fastapi import FastAPI
from app.api.chat import router as chat_router

app = FastAPI(title="AI DevOps AIOps Platform")

app.include_router(chat_router, prefix="/api")

@app.get("/")
def health():
    return {"status": "ok"}
