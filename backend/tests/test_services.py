from unittest.mock import patch, MagicMock

from app.services.rag_service import build_context, process_query
from app.services.llm_service import ask_llm


# --- rag_service tests ---


def test_build_context_with_logs():
    result = build_context(logs="ERROR pod crash")
    assert result == "ERROR pod crash"


def test_build_context_empty_logs_falls_through():
    result = build_context(logs="")
    assert "No logs provided" in result


def test_build_context_none_logs_no_dir():
    result = build_context(logs=None)
    # With no real log directory, should fall through to the default message
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


# --- llm_service tests ---


@patch("app.services.llm_service.client")
def test_ask_llm_success(mock_client):
    mock_choice = MagicMock()
    mock_choice.message.content = "the answer"
    mock_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])

    result = ask_llm("test prompt")
    assert result == "the answer"


@patch("app.services.llm_service.client")
def test_ask_llm_connection_error(mock_client):
    from openai import APIConnectionError

    mock_client.chat.completions.create.side_effect = APIConnectionError(request=MagicMock())
    try:
        ask_llm("test")
        assert False, "Should have raised"
    except RuntimeError as exc:
        assert "Unable to reach" in str(exc)
