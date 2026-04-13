import json
from unittest.mock import patch, MagicMock

from app.services.rag_service import build_context, process_query, analyze, parse_analysis
from app.services.llm_service import ask_llm
from app.services.remediation_executor import execute_action, execute_remediation
from app.models import AnalysisResult, Remediation, RemediationAction, Severity


# --- rag_service tests ---


def test_build_context_with_logs():
    result = build_context(logs="ERROR pod crash")
    assert result == "ERROR pod crash"


def test_build_context_empty_logs_falls_through():
    result = build_context(logs="")
    assert "No logs provided" in result


def test_build_context_none_logs_no_dir():
    result = build_context(logs=None)
    assert "No logs provided" in result


@patch("app.services.rag_service.ask_llm", return_value="root cause: OOM")
def test_process_query_with_logs(mock_llm):
    result = process_query("Why crash?", logs="OOMKilled in pod-abc")
    assert result == "root cause: OOM"
    prompt = mock_llm.call_args[0][0]
    assert "OOMKilled in pod-abc" in prompt
    assert "Why crash?" in prompt


@patch("app.services.rag_service.ask_llm", return_value="analysis")
def test_process_query_without_logs(mock_llm):
    result = process_query("General question")
    assert result == "analysis"


MOCK_ANALYSIS_JSON = json.dumps({
    "root_cause": "Container exceeded memory limit",
    "evidence": ["OOMKilled in pod logs", "Memory usage at 512Mi limit"],
    "severity": "high",
    "confidence_score": 0.85,
    "recommended_actions": [
        {
            "action_type": "increase_memory",
            "target": "deployment/web-app",
            "command": None,
            "parameters": {"memory": "1Gi"},
        }
    ],
    "risk_assessment": "Increasing memory may affect cluster resource allocation",
})


def test_parse_analysis_valid_json():
    result = parse_analysis(MOCK_ANALYSIS_JSON)
    assert isinstance(result, AnalysisResult)
    assert result.confidence_score == 0.85
    assert result.severity == Severity.high
    assert len(result.recommended_actions) == 1
    assert result.recommended_actions[0].action_type == "increase_memory"


def test_parse_analysis_with_markdown_fences():
    wrapped = f"```json\n{MOCK_ANALYSIS_JSON}\n```"
    result = parse_analysis(wrapped)
    assert result.confidence_score == 0.85


def test_parse_analysis_invalid_json():
    try:
        parse_analysis("not json at all")
        assert False, "Should have raised"
    except (json.JSONDecodeError, ValueError):
        pass


@patch("app.services.rag_service.ask_llm", return_value=MOCK_ANALYSIS_JSON)
def test_analyze_returns_structured_result(mock_llm):
    result = analyze("Why is the pod crashing?", logs="OOMKilled")
    assert isinstance(result, AnalysisResult)
    assert result.confidence_score == 0.85
    assert result.root_cause == "Container exceeded memory limit"
    prompt = mock_llm.call_args[0][0]
    assert "OOMKilled" in prompt


# --- llm_service tests ---


@patch("app.services.llm_service._get_client")
def test_ask_llm_success(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_choice = MagicMock()
    mock_choice.message.content = "the answer"
    mock_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])

    result = ask_llm("test prompt")
    assert result == "the answer"


@patch("app.services.llm_service._get_client")
def test_ask_llm_connection_error(mock_get_client):
    from openai import APIConnectionError

    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_client.chat.completions.create.side_effect = APIConnectionError(request=MagicMock())
    try:
        ask_llm("test")
        assert False, "Should have raised"
    except RuntimeError as exc:
        assert "Unable to reach" in str(exc)


# --- remediation executor tests ---


def test_execute_action_restart():
    action = RemediationAction(action_type="restart_pod", target="web-pod-abc")
    result = execute_action(action)
    assert "web-pod-abc" in result
    assert "restart" in result.lower() or "delete" in result.lower()


def test_execute_action_unknown():
    action = RemediationAction(action_type="unknown_action", target="something")
    result = execute_action(action)
    assert "Unknown" in result


def test_execute_remediation_multiple_actions():
    analysis = AnalysisResult(
        root_cause="OOM",
        evidence=["log1"],
        severity="high",
        confidence_score=0.9,
        recommended_actions=[
            RemediationAction(action_type="restart_pod", target="pod-1"),
            RemediationAction(action_type="scale_up", target="deployment/web", parameters={"replicas": 5}),
        ],
        risk_assessment="minimal",
    )
    rem = Remediation(analysis=analysis, question="test")
    result = execute_remediation(rem)
    assert "Action 1" in result
    assert "Action 2" in result
    assert "pod-1" in result
    assert "replicas=5" in result
