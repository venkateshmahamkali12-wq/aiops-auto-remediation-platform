import json
import os
import glob
import logging
from typing import Optional

from app.models import AnalysisResult
from app.services.llm_service import ask_llm

logger = logging.getLogger(__name__)

LOG_DIR = os.getenv("LOG_DIR", "/var/log/app")

ANALYSIS_PROMPT = """You are a senior DevOps AI assistant performing incident analysis.

Context (logs/metrics):
{context}

Question:
{question}

Respond ONLY with valid JSON matching this exact schema:
{{
  "root_cause": "concise root cause description",
  "evidence": ["evidence point 1", "evidence point 2"],
  "severity": "low|medium|high|critical",
  "confidence_score": 0.0 to 1.0,
  "recommended_actions": [
    {{
      "action_type": "restart_pod|scale_up|rollback|increase_memory|increase_cpu|drain_node|cordon_node|run_command",
      "target": "resource name (e.g. pod-xyz, deployment/web-app)",
      "command": null or "shell command if action_type is run_command",
      "parameters": {{}}
    }}
  ],
  "risk_assessment": "description of risks if remediation is applied"
}}

Rules for confidence_score:
- 1.0: logs clearly confirm the root cause with direct evidence
- 0.7-0.9: strong indicators but some ambiguity
- 0.4-0.6: probable cause based on patterns but needs verification
- 0.1-0.3: speculative, limited evidence available
- Base your score on how much evidence supports the diagnosis, NOT on severity"""


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


def parse_analysis(raw: str) -> AnalysisResult:
    """Parse LLM JSON response into a structured AnalysisResult."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

    data = json.loads(cleaned)
    return AnalysisResult(**data)


def process_query(question: str, logs: Optional[str] = None) -> str:
    """Legacy text-based query. Returns plain text response."""
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


def analyze(question: str, logs: Optional[str] = None) -> AnalysisResult:
    """Structured analysis returning AnalysisResult with confidence score."""
    context = build_context(logs)
    prompt = ANALYSIS_PROMPT.format(context=context, question=question)
    raw = ask_llm(prompt)

    try:
        return parse_analysis(raw)
    except (json.JSONDecodeError, KeyError, ValueError) as exc:
        logger.error("Failed to parse LLM response: %s\nRaw: %s", exc, raw)
        raise RuntimeError(f"LLM returned invalid analysis format: {exc}")
