import logging

from fastapi import FastAPI

from app.api.chat import router as chat_router
from app.api.remediation import router as remediation_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(title="AI DevOps AIOps Platform")

app.include_router(chat_router, prefix="/api")
app.include_router(remediation_router, prefix="/api")


@app.get("/")
def health():
    return {"status": "ok"}
