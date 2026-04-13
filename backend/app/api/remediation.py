import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models import Remediation, RemediationStatus
from app.services.rag_service import analyze
from app.services import remediation_store
from app.services.remediation_executor import execute_remediation

logger = logging.getLogger(__name__)
router = APIRouter()

AUTO_APPROVE_THRESHOLD = 0.9


class AnalyzeRequest(BaseModel):
    question: str
    logs: Optional[str] = None
    auto_approve_threshold: Optional[float] = None


class ApprovalRequest(BaseModel):
    approved_by: str


@router.post("/analyze")
def analyze_incident(req: AnalyzeRequest):
    """Analyze an incident and create a remediation plan (pending approval)."""
    try:
        result = analyze(req.question, logs=req.logs)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    remediation = Remediation(
        analysis=result,
        question=req.question,
        logs=req.logs,
    )

    threshold = req.auto_approve_threshold if req.auto_approve_threshold is not None else AUTO_APPROVE_THRESHOLD
    if result.confidence_score >= threshold:
        remediation.status = RemediationStatus.approved
        remediation.approved_by = "auto"
        logger.info(
            "Auto-approved remediation %s (confidence %.2f >= %.2f)",
            remediation.id, result.confidence_score, threshold,
        )

    remediation_store.save(remediation)

    return {
        "remediation_id": remediation.id,
        "status": remediation.status.value,
        "confidence_score": result.confidence_score,
        "severity": result.severity.value,
        "root_cause": result.root_cause,
        "recommended_actions": [a.model_dump() for a in result.recommended_actions],
        "risk_assessment": result.risk_assessment,
        "auto_approved": remediation.status == RemediationStatus.approved,
    }


@router.get("/remediations")
def list_remediations(status: Optional[str] = None):
    """List all remediations, optionally filtered by status."""
    filter_status = None
    if status:
        try:
            filter_status = RemediationStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    items = remediation_store.list_all(status=filter_status)
    return {
        "count": len(items),
        "remediations": [
            {
                "id": r.id,
                "status": r.status.value,
                "confidence_score": r.analysis.confidence_score,
                "severity": r.analysis.severity.value,
                "root_cause": r.analysis.root_cause,
                "created_at": r.created_at.isoformat(),
            }
            for r in items
        ],
    }


@router.get("/remediations/{remediation_id}")
def get_remediation(remediation_id: str):
    """Get full details of a remediation."""
    rem = remediation_store.get(remediation_id)
    if not rem:
        raise HTTPException(status_code=404, detail="Remediation not found")
    return rem.model_dump()


@router.post("/remediations/{remediation_id}/approve")
def approve_remediation(remediation_id: str, req: ApprovalRequest):
    """Approve a pending remediation."""
    rem = remediation_store.get(remediation_id)
    if not rem:
        raise HTTPException(status_code=404, detail="Remediation not found")
    if rem.status != RemediationStatus.pending_approval:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot approve: current status is '{rem.status.value}'",
        )

    remediation_store.update_status(
        remediation_id, RemediationStatus.approved, approved_by=req.approved_by
    )
    logger.info("Remediation %s approved by %s", remediation_id, req.approved_by)
    return {"id": remediation_id, "status": "approved", "approved_by": req.approved_by}


@router.post("/remediations/{remediation_id}/reject")
def reject_remediation(remediation_id: str, req: ApprovalRequest):
    """Reject a pending remediation."""
    rem = remediation_store.get(remediation_id)
    if not rem:
        raise HTTPException(status_code=404, detail="Remediation not found")
    if rem.status != RemediationStatus.pending_approval:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot reject: current status is '{rem.status.value}'",
        )

    remediation_store.update_status(
        remediation_id, RemediationStatus.rejected, approved_by=req.approved_by
    )
    logger.info("Remediation %s rejected by %s", remediation_id, req.approved_by)
    return {"id": remediation_id, "status": "rejected"}


@router.post("/remediations/{remediation_id}/execute")
def execute(remediation_id: str):
    """Execute an approved remediation."""
    rem = remediation_store.get(remediation_id)
    if not rem:
        raise HTTPException(status_code=404, detail="Remediation not found")
    if rem.status != RemediationStatus.approved:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot execute: status must be 'approved', got '{rem.status.value}'",
        )

    remediation_store.update_status(remediation_id, RemediationStatus.executing)
    try:
        result = execute_remediation(rem)
        remediation_store.update_status(
            remediation_id, RemediationStatus.completed, execution_result=result
        )
        logger.info("Remediation %s completed", remediation_id)
        return {"id": remediation_id, "status": "completed", "result": result}
    except Exception as exc:
        remediation_store.update_status(
            remediation_id, RemediationStatus.failed, execution_result=str(exc)
        )
        logger.exception("Remediation %s failed", remediation_id)
        raise HTTPException(status_code=500, detail=f"Execution failed: {exc}")
