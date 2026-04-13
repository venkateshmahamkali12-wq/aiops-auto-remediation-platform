import json
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.models import AnalysisResult, RemediationAction, Severity
from app.services import remediation_store

client = TestClient(app)


def setup_function():
    remediation_store.clear()


# --- Health ---


def test_health():
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# --- Chat (legacy) ---


@patch("app.api.chat.process_query", return_value="mocked analysis")
def test_chat_success(mock_pq):
    resp = client.post("/api/chat", json={"question": "Why is the pod crashing?"})
    assert resp.status_code == 200
    assert resp.json() == {"response": "mocked analysis"}
    mock_pq.assert_called_once_with("Why is the pod crashing?", logs=None)


@patch("app.api.chat.process_query", return_value="mocked analysis")
def test_chat_with_logs(mock_pq):
    payload = {"question": "What happened?", "logs": "ERROR OOMKilled container xyz"}
    resp = client.post("/api/chat", json=payload)
    assert resp.status_code == 200
    mock_pq.assert_called_once_with("What happened?", logs="ERROR OOMKilled container xyz")


def test_chat_missing_question():
    resp = client.post("/api/chat", json={})
    assert resp.status_code == 422


@patch("app.api.chat.process_query", side_effect=RuntimeError("LLM down"))
def test_chat_llm_error(mock_pq):
    resp = client.post("/api/chat", json={"question": "test"})
    assert resp.status_code == 502
    assert "LLM down" in resp.json()["detail"]


# --- Analyze + Remediation workflow ---


MOCK_ANALYSIS = AnalysisResult(
    root_cause="OOMKilled",
    evidence=["memory limit exceeded"],
    severity=Severity.high,
    confidence_score=0.75,
    recommended_actions=[
        RemediationAction(action_type="increase_memory", target="deployment/web-app", parameters={"memory": "1Gi"})
    ],
    risk_assessment="May affect cluster resources",
)


MOCK_HIGH_CONFIDENCE = AnalysisResult(
    root_cause="OOMKilled",
    evidence=["memory limit exceeded"],
    severity=Severity.high,
    confidence_score=0.95,
    recommended_actions=[
        RemediationAction(action_type="restart_pod", target="pod-xyz")
    ],
    risk_assessment="Minimal risk",
)


@patch("app.api.remediation.analyze", return_value=MOCK_ANALYSIS)
def test_analyze_creates_pending_remediation(mock_analyze):
    resp = client.post("/api/analyze", json={"question": "pod crash", "logs": "OOMKilled"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["confidence_score"] == 0.75
    assert data["status"] == "pending_approval"
    assert data["auto_approved"] is False
    assert data["root_cause"] == "OOMKilled"
    assert len(data["recommended_actions"]) == 1


@patch("app.api.remediation.analyze", return_value=MOCK_HIGH_CONFIDENCE)
def test_analyze_auto_approves_high_confidence(mock_analyze):
    resp = client.post("/api/analyze", json={"question": "pod crash"})
    data = resp.json()
    assert data["confidence_score"] == 0.95
    assert data["status"] == "approved"
    assert data["auto_approved"] is True


@patch("app.api.remediation.analyze", return_value=MOCK_ANALYSIS)
def test_approve_and_execute_workflow(mock_analyze):
    # Step 1: Analyze
    resp = client.post("/api/analyze", json={"question": "pod crash"})
    rem_id = resp.json()["remediation_id"]
    assert resp.json()["status"] == "pending_approval"

    # Step 2: Approve
    resp = client.post(f"/api/remediations/{rem_id}/approve", json={"approved_by": "alice"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"

    # Step 3: Execute
    resp = client.post(f"/api/remediations/{rem_id}/execute")
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"
    assert "increase_memory" in resp.json()["result"]


@patch("app.api.remediation.analyze", return_value=MOCK_ANALYSIS)
def test_reject_remediation(mock_analyze):
    resp = client.post("/api/analyze", json={"question": "pod crash"})
    rem_id = resp.json()["remediation_id"]

    resp = client.post(f"/api/remediations/{rem_id}/reject", json={"approved_by": "bob"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"

    # Cannot execute a rejected remediation
    resp = client.post(f"/api/remediations/{rem_id}/execute")
    assert resp.status_code == 409


@patch("app.api.remediation.analyze", return_value=MOCK_ANALYSIS)
def test_cannot_execute_pending(mock_analyze):
    resp = client.post("/api/analyze", json={"question": "test"})
    rem_id = resp.json()["remediation_id"]

    resp = client.post(f"/api/remediations/{rem_id}/execute")
    assert resp.status_code == 409


@patch("app.api.remediation.analyze", return_value=MOCK_ANALYSIS)
def test_list_remediations(mock_analyze):
    client.post("/api/analyze", json={"question": "q1"})
    client.post("/api/analyze", json={"question": "q2"})

    resp = client.get("/api/remediations")
    assert resp.status_code == 200
    assert resp.json()["count"] == 2

    resp = client.get("/api/remediations?status=pending_approval")
    assert resp.json()["count"] == 2

    resp = client.get("/api/remediations?status=approved")
    assert resp.json()["count"] == 0


def test_get_remediation_not_found():
    resp = client.get("/api/remediations/nonexistent")
    assert resp.status_code == 404
