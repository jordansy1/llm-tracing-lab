import pytest
from src.models import SecurityAlert, Classification, EvalResult, Severity, Category


def test_security_alert_valid():
    alert = SecurityAlert(
        id="alert-001",
        timestamp="2026-03-10T14:30:00Z",
        source="google_workspace",
        raw_text="Multiple failed login attempts from IP 203.0.113.42 targeting admin@company.com",
        metadata={"ip": "203.0.113.42", "attempts": 15},
    )
    assert alert.id == "alert-001"
    assert alert.source == "google_workspace"


def test_classification_valid():
    c = Classification(
        severity=Severity.HIGH,
        category=Category.BRUTE_FORCE,
        confidence=0.92,
        reasoning="15 failed login attempts from single IP targeting admin account",
    )
    assert c.severity == Severity.HIGH
    assert c.category == Category.BRUTE_FORCE
    assert 0 <= c.confidence <= 1


def test_classification_confidence_bounds():
    with pytest.raises(ValueError):
        Classification(
            severity=Severity.LOW,
            category=Category.PHISHING,
            confidence=1.5,
            reasoning="test",
        )


def test_eval_result():
    expected = Classification(
        severity=Severity.HIGH,
        category=Category.BRUTE_FORCE,
        confidence=0.9,
        reasoning="expected",
    )
    actual = Classification(
        severity=Severity.HIGH,
        category=Category.CREDENTIAL_ABUSE,
        confidence=0.8,
        reasoning="actual",
    )
    result = EvalResult(
        alert_id="alert-001",
        expected=expected,
        actual=actual,
        severity_match=True,
        category_match=False,
    )
    assert result.severity_match is True
    assert result.category_match is False
