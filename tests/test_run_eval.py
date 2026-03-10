import json
from unittest.mock import MagicMock, patch

from evals.run_eval import load_golden_set, make_target, make_severity_evaluator, make_category_evaluator


def test_load_golden_set(tmp_path):
    golden = [
        {
            "alert": {
                "id": "a1", "timestamp": "2026-01-01T00:00:00Z",
                "source": "test", "raw_text": "test alert",
            },
            "expected": {
                "severity": "high", "category": "phishing",
                "reasoning": "test",
            },
        }
    ]
    f = tmp_path / "golden.json"
    f.write_text(json.dumps(golden))

    examples = load_golden_set(str(f))
    assert len(examples) == 1
    assert examples[0]["inputs"]["raw_text"] == "test alert"
    assert examples[0]["outputs"]["severity"] == "high"


@patch("evals.run_eval.init_client")
@patch("evals.run_eval.classify_alert")
def test_make_target(mock_classify, mock_init):
    from src.models import Classification, Severity, Category

    mock_classify.return_value = Classification(
        severity=Severity.HIGH, category=Category.PHISHING,
        confidence=0.9, reasoning="test",
    )

    target = make_target(prompt_version="v1")
    result = target({
        "id": "a1", "timestamp": "2026-01-01T00:00:00Z",
        "source": "test", "raw_text": "test alert",
    })

    assert result["severity"] == "high"
    assert result["category"] == "phishing"
    mock_classify.assert_called_once()


def test_severity_evaluator_match():
    evaluator = make_severity_evaluator()
    result = evaluator(
        run=MagicMock(outputs={"severity": "high", "category": "phishing"}),
        example=MagicMock(outputs={"severity": "high", "category": "phishing"}),
    )
    assert result["score"] == 1.0


def test_severity_evaluator_mismatch():
    evaluator = make_severity_evaluator()
    result = evaluator(
        run=MagicMock(outputs={"severity": "low", "category": "phishing"}),
        example=MagicMock(outputs={"severity": "high", "category": "phishing"}),
    )
    assert result["score"] == 0.0


def test_category_evaluator_match():
    evaluator = make_category_evaluator()
    result = evaluator(
        run=MagicMock(outputs={"severity": "low", "category": "phishing"}),
        example=MagicMock(outputs={"severity": "high", "category": "phishing"}),
    )
    assert result["score"] == 1.0
