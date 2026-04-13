import os
import glob
from typing import Optional

from app.services.llm_service import ask_llm

LOG_DIR = os.getenv("LOG_DIR", "/var/log/app")


def load_logs_from_directory(directory: str, max_lines: int = 200) -> str:
    """Read recent log lines from files in the configured log directory."""
    lines = []
    log_files = sorted(glob.glob(os.path.join(directory, "*.log")), key=os.path.getmtime, reverse=True)
    for path in log_files[:5]:
        try:
            with open(path) as f:
                tail = f.readlines()[-50:]
                lines.extend(tail)
        except OSError:
            continue
    return "".join(lines[:max_lines]).strip()


def build_context(logs: Optional[str] = None) -> str:
    """Build context from provided logs or by reading the log directory."""
    if logs and logs.strip():
        return logs.strip()

    dir_logs = load_logs_from_directory(LOG_DIR)
    if dir_logs:
        return dir_logs

    return "(No logs provided. Answer based on general DevOps knowledge.)"


def process_query(question: str, logs: Optional[str] = None) -> str:
    context = build_context(logs)

    prompt = f"""You are a DevOps AI assistant.

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
