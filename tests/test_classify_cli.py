import json
from unittest.mock import MagicMock, patch

from scripts.classify import classify_single, classify_batch


@patch("scripts.classify.init_client")
@patch("scripts.classify.classify_alert")
def test_classify_single(mock_classify, mock_init):
    from src.models import Classification, Severity, Category

    mock_classify.return_value = Classification(
        severity=Severity.HIGH,
        category=Category.PHISHING,
        confidence=0.9,
        reasoning="test",
    )
    result = classify_single("Suspicious email from unknown sender", prompt_version="v1")
    assert result.severity == Severity.HIGH
    mock_classify.assert_called_once()


@patch("scripts.classify.init_client")
@patch("scripts.classify.classify_alert")
def test_classify_batch(mock_classify, mock_init, tmp_path):
    from src.models import Classification, Severity, Category

    mock_classify.return_value = Classification(
        severity=Severity.MEDIUM,
        category=Category.MALWARE,
        confidence=0.7,
        reasoning="test",
    )

    alerts_file = tmp_path / "alerts.json"
    alerts_file.write_text(json.dumps([
        {"id": "a1", "timestamp": "2026-01-01T00:00:00Z", "source": "test", "raw_text": "test alert 1"},
        {"id": "a2", "timestamp": "2026-01-01T00:00:00Z", "source": "test", "raw_text": "test alert 2"},
    ]))

    results = classify_batch(str(alerts_file), prompt_version="v1")
    assert len(results) == 2
    assert mock_classify.call_count == 2
