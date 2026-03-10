import pytest

from src.models import Classification, Severity, Category
from evals.scorers import severity_accuracy, category_accuracy, overall_score


def _make_classification(severity, category):
    return Classification(
        severity=severity, category=category,
        confidence=0.9, reasoning="test",
    )


def test_severity_accuracy_match():
    expected = _make_classification(Severity.HIGH, Category.PHISHING)
    actual = _make_classification(Severity.HIGH, Category.MALWARE)
    assert severity_accuracy(expected, actual) == 1.0


def test_severity_accuracy_mismatch():
    expected = _make_classification(Severity.HIGH, Category.PHISHING)
    actual = _make_classification(Severity.LOW, Category.PHISHING)
    assert severity_accuracy(expected, actual) == 0.0


def test_category_accuracy_match():
    expected = _make_classification(Severity.LOW, Category.PHISHING)
    actual = _make_classification(Severity.HIGH, Category.PHISHING)
    assert category_accuracy(expected, actual) == 1.0


def test_category_accuracy_mismatch():
    expected = _make_classification(Severity.LOW, Category.PHISHING)
    actual = _make_classification(Severity.LOW, Category.MALWARE)
    assert category_accuracy(expected, actual) == 0.0


def test_overall_score():
    expected = _make_classification(Severity.HIGH, Category.PHISHING)
    actual = _make_classification(Severity.HIGH, Category.MALWARE)
    # severity matches (1.0), category doesn't (0.0)
    # default weights: 0.4 severity + 0.6 category = 0.4
    score = overall_score(expected, actual)
    assert score == pytest.approx(0.4)
