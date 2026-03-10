import json
from unittest.mock import MagicMock, patch

import pytest

from src.classifier import classify_alert
from src.models import SecurityAlert, Classification, Severity, Category


@pytest.fixture
def sample_alert():
    return SecurityAlert(
        id="alert-001",
        timestamp="2026-03-10T14:30:00Z",
        source="google_workspace",
        raw_text="Multiple failed login attempts from IP 203.0.113.42 targeting admin@company.com",
        metadata={"ip": "203.0.113.42"},
    )


@pytest.fixture
def mock_claude_response():
    """Mock Anthropic API response with valid classification JSON."""
    mock_response = MagicMock()
    mock_response.content = [
        MagicMock(text=json.dumps({
            "severity": "high",
            "category": "brute_force",
            "confidence": 0.92,
            "reasoning": "15 failed login attempts from single IP targeting admin account",
        }))
    ]
    return mock_response


def test_classify_alert_returns_classification(sample_alert, mock_claude_response):
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_claude_response

    result = classify_alert(sample_alert, client=mock_client, prompt_version="v1")

    assert isinstance(result, Classification)
    assert result.severity == Severity.HIGH
    assert result.category == Category.BRUTE_FORCE
    assert result.confidence == 0.92


def test_classify_alert_calls_claude_with_correct_prompt(sample_alert, mock_claude_response):
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_claude_response

    classify_alert(sample_alert, client=mock_client, prompt_version="v1")

    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == "claude-haiku-4-5-20251001"
    assert "severity" in call_kwargs["system"].lower()
    assert sample_alert.raw_text in call_kwargs["messages"][0]["content"]


def test_classify_alert_invalid_json_raises():
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="not valid json")]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    alert = SecurityAlert(
        id="alert-002", timestamp="2026-03-10T14:30:00Z",
        source="test", raw_text="test alert",
    )
    with pytest.raises(ValueError, match="Failed to parse"):
        classify_alert(alert, client=mock_client, prompt_version="v1")
