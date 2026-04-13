import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Severity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class RemediationStatus(str, Enum):
    pending_approval = "pending_approval"
    approved = "approved"
    rejected = "rejected"
    executing = "executing"
    completed = "completed"
    failed = "failed"


class RemediationAction(BaseModel):
    action_type: str = Field(description="e.g. restart_pod, scale_up, rollback, run_command")
    target: str = Field(description="e.g. pod name, deployment name")
    command: Optional[str] = Field(default=None, description="Shell command to execute")
    parameters: dict = Field(default_factory=dict)


class AnalysisResult(BaseModel):
    root_cause: str
    evidence: list[str]
    severity: Severity
    confidence_score: float = Field(ge=0.0, le=1.0, description="0.0 to 1.0")
    recommended_actions: list[RemediationAction]
    risk_assessment: str


class Remediation(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: RemediationStatus = RemediationStatus.pending_approval
    analysis: AnalysisResult
    question: str
    logs: Optional[str] = None
    approved_by: Optional[str] = None
    execution_result: Optional[str] = None
