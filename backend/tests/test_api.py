from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@patch("app.api.chat.process_query", return_value="mocked analysis")
def test_chat_success(mock_pq):
    resp = client.post("/api/chat", json={"question": "Why is the pod crashing?"})
    assert resp.status_code == 200
    assert resp.json() == {"response": "mocked analysis"}
    mock_pq.assert_called_once_with("Why is the pod crashing?", logs=None)


@patch("app.api.chat.process_query", return_value="mocked analysis")
def test_chat_with_logs(mock_pq):
    payload = {
        "question": "What happened?",
        "logs": "ERROR OOMKilled container xyz",
    }
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
