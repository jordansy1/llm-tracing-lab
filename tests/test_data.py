import json
import pytest
from src.models import SecurityAlert, Severity, Category

DATA_DIR = "data"


def test_sample_alerts_valid():
    with open(f"{DATA_DIR}/sample_alerts.json") as f:
        alerts = json.load(f)

    assert len(alerts) >= 20, "Need at least 20 sample alerts"
    for raw in alerts:
        alert = SecurityAlert(**raw)  # Should not raise
        assert alert.raw_text, f"Alert {alert.id} has empty raw_text"


def test_golden_set_valid():
    with open(f"{DATA_DIR}/golden_set.json") as f:
        golden = json.load(f)

    assert len(golden) >= 15, "Need at least 15 golden set entries"
    for item in golden:
        SecurityAlert(**item["alert"])  # Should not raise
        expected = item["expected"]
        assert expected["severity"] in [s.value for s in Severity]
        assert expected["category"] in [c.value for c in Category]
        assert expected["reasoning"], "Expected reasoning must not be empty"


def test_golden_set_covers_all_categories():
    with open(f"{DATA_DIR}/golden_set.json") as f:
        golden = json.load(f)

    categories = {item["expected"]["category"] for item in golden}
    for cat in Category:
        assert cat.value in categories, f"Golden set missing category: {cat.value}"
