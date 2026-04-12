from app.services.llm_service import ask_llm

def process_query(question: str) -> str:
    context = "Sample log: Pod crashed due to OOMKilled"

    prompt = f"""
You are a DevOps AI assistant.

Context:
{context}

Question:
{question}

Answer with:
- Root Cause
- Evidence
- Fix
- Risk
"""

    return ask_llm(prompt)
