# LLM Tracing Lab Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a security alert triage classifier with LangSmith tracing and evals to learn LLM observability and prompt iteration workflows.

**Architecture:** Raw Anthropic SDK calls wrapped with LangSmith's `wrap_anthropic()` for auto-tracing API calls, plus `@traceable` decorators for application-level spans. Eval pipeline uses LangSmith's `evaluate()` to score prompt versions against a hand-labeled golden set.

**Tech Stack:** Python 3.11+, anthropic, langsmith, pydantic, python-dotenv

---

## Chunk 1: Project Scaffold & Data Models

### Task 1: Project setup — venv, dependencies, config files

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `src/__init__.py`
- Create: `evals/__init__.py`
- Create: `scripts/__init__.py`
- Create: `data/` (directory)

- [ ] **Step 1: Create virtual environment**

```bash
cd "Code Projects/Testing/llm-tracing-lab"
python -m venv .venv
```

- [ ] **Step 2: Create requirements.txt**

```txt
anthropic>=0.39.0
langsmith>=0.2.0
pydantic>=2.0.0
python-dotenv>=1.0.0
pytest>=8.0.0
```

- [ ] **Step 3: Install dependencies**

```bash
source .venv/Scripts/activate
pip install -r requirements.txt
```

- [ ] **Step 4: Create .env.example**

```env
ANTHROPIC_API_KEY=your-anthropic-api-key
LANGSMITH_API_KEY=your-langsmith-api-key
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=llm-tracing-lab
```

- [ ] **Step 5: Create .gitignore**

```gitignore
.venv/
.env
__pycache__/
*.pyc
.DS_Store
```

- [ ] **Step 6: Create empty __init__.py files and data directory**

Create `src/__init__.py`, `evals/__init__.py`, `scripts/__init__.py` as empty files.
Create `data/` directory.

- [ ] **Step 7: Commit**

```bash
git add requirements.txt .env.example .gitignore src/__init__.py evals/__init__.py scripts/__init__.py data/
git commit -m "scaffold: project setup with venv, dependencies, and config"
```

---

### Task 2: Pydantic data models

**Files:**
- Create: `src/models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write failing tests for models**

Create `tests/__init__.py` and `tests/test_models.py`:

```python
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
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
source .venv/Scripts/activate
python -m pytest tests/test_models.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'src.models'`

- [ ] **Step 3: Implement models**

Create `src/models.py`:

```python
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Category(str, Enum):
    PHISHING = "phishing"
    BRUTE_FORCE = "brute_force"
    DATA_EXFILTRATION = "data_exfiltration"
    CREDENTIAL_ABUSE = "credential_abuse"
    INSIDER_THREAT = "insider_threat"
    MALWARE = "malware"


class SecurityAlert(BaseModel):
    id: str
    timestamp: str
    source: str
    raw_text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class Classification(BaseModel):
    severity: Severity
    category: Category
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str


class EvalResult(BaseModel):
    alert_id: str
    expected: Classification
    actual: Classification
    severity_match: bool
    category_match: bool
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
python -m pytest tests/test_models.py -v
```

Expected: All 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/models.py tests/__init__.py tests/test_models.py
git commit -m "feat: add Pydantic data models for alerts, classifications, and eval results"
```

---

## Chunk 2: Tracing Setup & Prompts

### Task 3: LangSmith tracing module

**Files:**
- Create: `src/tracing.py`
- Create: `tests/test_tracing.py`

- [ ] **Step 1: Write failing test for tracing setup**

Create `tests/test_tracing.py`:

```python
from unittest.mock import MagicMock, patch

from src.tracing import init_client


@patch("src.tracing.wrap_anthropic")
@patch("src.tracing.anthropic.Anthropic")
def test_init_client_returns_wrapped_anthropic(mock_anthropic_cls, mock_wrap):
    """init_client should create an Anthropic client and wrap it for tracing."""
    mock_raw_client = MagicMock()
    mock_anthropic_cls.return_value = mock_raw_client
    mock_wrapped = MagicMock()
    mock_wrap.return_value = mock_wrapped

    result = init_client()

    mock_anthropic_cls.assert_called_once()
    mock_wrap.assert_called_once_with(mock_raw_client)
    assert result is mock_wrapped
```

- [ ] **Step 2: Run test — verify it fails**

```bash
python -m pytest tests/test_tracing.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'src.tracing'`

- [ ] **Step 3: Implement tracing module**

Create `src/tracing.py`:

```python
import anthropic
from langsmith import traceable
from langsmith.wrappers import wrap_anthropic


def init_client() -> anthropic.Anthropic:
    """Create an Anthropic client wrapped with LangSmith tracing.

    Requires ANTHROPIC_API_KEY, LANGSMITH_API_KEY, LANGSMITH_TRACING=true,
    and LANGSMITH_PROJECT env vars to be set (loaded via .env).
    """
    raw_client = anthropic.Anthropic()
    return wrap_anthropic(raw_client)


# Re-export traceable for use in other modules
__all__ = ["init_client", "traceable"]
```

- [ ] **Step 4: Run test — verify it passes**

```bash
python -m pytest tests/test_tracing.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/tracing.py tests/test_tracing.py
git commit -m "feat: add LangSmith tracing setup with wrap_anthropic"
```

---

### Task 4: Versioned system prompts

**Files:**
- Create: `src/prompts.py`
- Create: `tests/test_prompts.py`

- [ ] **Step 1: Write failing tests for prompts**

Create `tests/test_prompts.py`:

```python
import pytest

from src.prompts import get_prompt, PROMPT_V1


def test_prompt_v1_exists():
    assert isinstance(PROMPT_V1, str)
    assert "severity" in PROMPT_V1.lower()
    assert "category" in PROMPT_V1.lower()


def test_get_prompt_v1():
    prompt = get_prompt("v1")
    assert prompt == PROMPT_V1


def test_get_prompt_invalid_version():
    with pytest.raises(KeyError):
        get_prompt("v999")
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
python -m pytest tests/test_prompts.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implement prompts module**

Create `src/prompts.py`:

```python
PROMPT_V1 = """You are a security alert triage analyst. Given a security alert, classify it by:

1. **Severity**: critical, high, medium, or low
2. **Category**: one of: phishing, brute_force, data_exfiltration, credential_abuse, insider_threat, malware
3. **Confidence**: a float from 0.0 to 1.0 indicating how confident you are
4. **Reasoning**: one sentence explaining your classification

Respond with valid JSON only, no other text:
{
  "severity": "...",
  "category": "...",
  "confidence": 0.0,
  "reasoning": "..."
}"""

_PROMPTS = {
    "v1": PROMPT_V1,
}


def get_prompt(version: str) -> str:
    """Return the system prompt for the given version.

    Raises KeyError if the version does not exist.
    """
    return _PROMPTS[version]
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
python -m pytest tests/test_prompts.py -v
```

Expected: All 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/prompts.py tests/test_prompts.py
git commit -m "feat: add versioned system prompts with v1 baseline"
```

---

## Chunk 3: Classifier Core

### Task 5: Alert classifier with tracing

**Files:**
- Create: `src/classifier.py`
- Create: `tests/test_classifier.py`

- [ ] **Step 1: Write failing tests for classifier**

Create `tests/test_classifier.py`:

```python
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
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
python -m pytest tests/test_classifier.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'src.classifier'`

- [ ] **Step 3: Implement classifier**

Create `src/classifier.py`:

```python
import json

import anthropic
from langsmith import traceable

from src.models import SecurityAlert, Classification
from src.prompts import get_prompt

MODEL = "claude-haiku-4-5-20251001"


@traceable(name="classify_alert", metadata={"component": "classifier"})
def classify_alert(
    alert: SecurityAlert,
    client,
    prompt_version: str = "v1",
    langsmith_extra: dict | None = None,
) -> Classification:
    """Classify a security alert using Claude.

    Args:
        alert: The security alert to classify.
        client: An Anthropic client (ideally wrapped with wrap_anthropic).
        prompt_version: Which system prompt version to use.
        langsmith_extra: Additional LangSmith trace metadata (auto-populated by @traceable).

    Returns:
        A Classification with severity, category, confidence, and reasoning.

    Raises:
        ValueError: If Claude's response is not valid JSON or doesn't match the schema.
    """
    system_prompt = get_prompt(prompt_version)

    user_message = (
        f"Alert ID: {alert.id}\n"
        f"Timestamp: {alert.timestamp}\n"
        f"Source: {alert.source}\n"
        f"Alert: {alert.raw_text}"
    )
    if alert.metadata:
        user_message += f"\nMetadata: {json.dumps(alert.metadata)}"

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=256,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
    except anthropic.APIError as e:
        raise RuntimeError(f"Anthropic API call failed: {e}") from e

    raw_text = response.content[0].text
    try:
        data = json.loads(raw_text)
        return Classification(**data)
    except (json.JSONDecodeError, ValueError) as e:
        raise ValueError(f"Failed to parse classification from Claude response: {e}")
```

Note: When calling `classify_alert`, pass `langsmith_extra={"metadata": {"prompt_version": prompt_version}}` to tag traces with the prompt version. This is done at the call site (CLI and eval runner), not hardcoded in the function. Example:

```python
result = classify_alert(
    alert, client=client, prompt_version=version,
    langsmith_extra={"metadata": {"prompt_version": version}},
)
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
python -m pytest tests/test_classifier.py -v
```

Expected: All 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/classifier.py tests/test_classifier.py
git commit -m "feat: add alert classifier with LangSmith tracing"
```

---

## Chunk 4: Sample Data & CLI

### Task 6: Sample alerts and golden set

**Files:**
- Create: `data/sample_alerts.json`
- Create: `data/golden_set.json`

- [ ] **Step 1: Create sample alerts**

Create `data/sample_alerts.json` with 20 synthetic security alerts. Include a mix of all 6 categories and 4 severity levels. Each alert is a JSON object with `id`, `timestamp`, `source`, `raw_text`, and `metadata` fields.

Example structure (write all 20):

```json
[
  {
    "id": "alert-001",
    "timestamp": "2026-03-10T08:15:00Z",
    "source": "google_workspace",
    "raw_text": "User clicked link in email from spoofed-hr@company-benefits.xyz claiming to require immediate password reset. Link redirects to credential harvesting page mimicking company SSO portal.",
    "metadata": {"sender": "spoofed-hr@company-benefits.xyz", "user": "jsmith@company.com"}
  },
  {
    "id": "alert-002",
    "timestamp": "2026-03-10T09:22:00Z",
    "source": "firewall",
    "raw_text": "47 failed SSH login attempts from IP 198.51.100.23 targeting root account over 12-minute window. IP geolocated to known VPS hosting provider.",
    "metadata": {"ip": "198.51.100.23", "attempts": 47, "target_user": "root"}
  }
]
```

Cover all categories: phishing (3-4), brute_force (3-4), data_exfiltration (3-4), credential_abuse (3-4), insider_threat (3), malware (3). Include 2-3 ambiguous edge cases.

- [ ] **Step 2: Create golden set**

Create `data/golden_set.json` — a subset of 15 alerts with expected classifications.

Note: Do NOT include `confidence` in the expected output — confidence is the model's self-reported value and varies between runs. Only include `severity`, `category`, and `reasoning`.

```json
[
  {
    "alert": { "...same as sample_alerts format..." },
    "expected": {
      "severity": "high",
      "category": "phishing",
      "reasoning": "Spoofed sender with credential harvesting link targeting employee"
    }
  }
]
```

Select 15 alerts (at least 2 per category) and hand-label them with the correct severity, category, and reasoning.

- [ ] **Step 3: Write data validation test**

Create `tests/test_data.py`:

```python
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
```

- [ ] **Step 4: Run data validation tests — verify they pass**

```bash
python -m pytest tests/test_data.py -v
```

Expected: All 3 tests PASS (will fail if data files aren't created yet — run after Steps 1-2).

- [ ] **Step 5: Commit**

```bash
git add data/sample_alerts.json data/golden_set.json tests/test_data.py
git commit -m "feat: add synthetic security alerts, golden set, and data validation tests"
```

---

### Task 7: CLI entry point

**Files:**
- Create: `scripts/classify.py`
- Create: `tests/test_classify_cli.py`

- [ ] **Step 1: Write failing test for CLI**

Create `tests/test_classify_cli.py`:

```python
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
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
python -m pytest tests/test_classify_cli.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implement CLI**

Create `scripts/classify.py`:

```python
import argparse
import json
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

from src.classifier import classify_alert
from src.models import SecurityAlert, Classification
from src.tracing import init_client


def classify_single(raw_text: str, prompt_version: str = "v1") -> Classification:
    """Classify a single alert from raw text."""
    client = init_client()
    alert = SecurityAlert(
        id="cli-input",
        timestamp=datetime.now(timezone.utc).isoformat(),
        source="cli",
        raw_text=raw_text,
    )
    return classify_alert(
        alert, client=client, prompt_version=prompt_version,
        langsmith_extra={"metadata": {"prompt_version": prompt_version}},
    )


def classify_batch(file_path: str, prompt_version: str = "v1") -> list[Classification]:
    """Classify all alerts from a JSON file."""
    client = init_client()
    with open(file_path) as f:
        raw_alerts = json.load(f)

    results = []
    for raw in raw_alerts:
        alert = SecurityAlert(**raw)
        result = classify_alert(alert, client=client, prompt_version=prompt_version)
        results.append(result)
        print(f"[{alert.id}] {result.severity.value}/{result.category.value} "
              f"(confidence: {result.confidence:.2f}) — {result.reasoning}")

    return results


def main():
    parser = argparse.ArgumentParser(description="Classify security alerts with LLM tracing")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--alert", type=str, help="Single alert text to classify")
    group.add_argument("--batch", type=str, help="Path to JSON file with alerts")
    parser.add_argument("--prompt-version", type=str, default="v1", help="Prompt version to use")

    args = parser.parse_args()

    if args.alert:
        result = classify_single(args.alert, prompt_version=args.prompt_version)
        print(f"\nSeverity:   {result.severity.value}")
        print(f"Category:   {result.category.value}")
        print(f"Confidence: {result.confidence:.2f}")
        print(f"Reasoning:  {result.reasoning}")
    else:
        results = classify_batch(args.batch, prompt_version=args.prompt_version)
        print(f"\nClassified {len(results)} alerts.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
python -m pytest tests/test_classify_cli.py -v
```

Expected: All 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/classify.py tests/test_classify_cli.py
git commit -m "feat: add CLI for single and batch alert classification"
```

---

## Chunk 5: Eval Pipeline

### Task 8: Scoring functions

**Files:**
- Create: `evals/scorers.py`
- Create: `tests/test_scorers.py`

- [ ] **Step 1: Write failing tests for scorers**

Create `tests/test_scorers.py`:

```python
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
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
python -m pytest tests/test_scorers.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implement scorers**

Create `evals/scorers.py`:

```python
from src.models import Classification


def severity_accuracy(expected: Classification, actual: Classification) -> float:
    """1.0 if severity matches exactly, 0.0 otherwise."""
    return 1.0 if expected.severity == actual.severity else 0.0


def category_accuracy(expected: Classification, actual: Classification) -> float:
    """1.0 if category matches exactly, 0.0 otherwise."""
    return 1.0 if expected.category == actual.category else 0.0


def overall_score(
    expected: Classification,
    actual: Classification,
    severity_weight: float = 0.4,
    category_weight: float = 0.6,
) -> float:
    """Weighted combination of severity and category accuracy."""
    return (
        severity_weight * severity_accuracy(expected, actual)
        + category_weight * category_accuracy(expected, actual)
    )
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
python -m pytest tests/test_scorers.py -v
```

Expected: All 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add evals/scorers.py tests/test_scorers.py
git commit -m "feat: add scoring functions for severity, category, and overall accuracy"
```

---

### Task 9: Eval runner with LangSmith experiments

**Files:**
- Create: `evals/run_eval.py`
- Create: `tests/test_run_eval.py`

This is the most important task for learning LangSmith evals. The `run_eval.py` script:
1. Uploads the golden set as a **LangSmith Dataset** (once, idempotent)
2. Uses `langsmith.evaluate()` to run the classifier as the **target function** against that dataset
3. Passes custom **evaluator functions** (our scorers) that produce scores per example
4. Results appear as an **Experiment** in the LangSmith dashboard for side-by-side comparison

- [ ] **Step 1: Write failing tests for eval runner**

Create `tests/test_run_eval.py`:

```python
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
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
python -m pytest tests/test_run_eval.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'evals.run_eval'`

- [ ] **Step 3: Implement eval runner**

Create `evals/run_eval.py`:

```python
import argparse
import json

from dotenv import load_dotenv

load_dotenv()

from langsmith import Client, evaluate

from src.classifier import classify_alert
from src.models import SecurityAlert, Classification
from src.tracing import init_client


def load_golden_set(path: str) -> list[dict]:
    """Load golden set and format as LangSmith dataset examples.

    Each example has:
      - inputs: the alert fields (fed to the target function)
      - outputs: the expected classification (used by evaluators)
    """
    with open(path) as f:
        data = json.load(f)

    examples = []
    for item in data:
        examples.append({
            "inputs": item["alert"],
            "outputs": {
                "severity": item["expected"]["severity"],
                "category": item["expected"]["category"],
                "reasoning": item["expected"]["reasoning"],
            },
        })
    return examples


def upload_dataset(examples: list[dict], dataset_name: str) -> str:
    """Upload examples to a LangSmith dataset (idempotent).

    Returns the dataset name.
    """
    client = Client()

    # Create or get existing dataset
    dataset = client.create_dataset(
        dataset_name=dataset_name,
        description="Security alert triage golden set",
    )

    # Upload examples
    client.create_examples(
        inputs=[e["inputs"] for e in examples],
        outputs=[e["outputs"] for e in examples],
        dataset_id=dataset.id,
    )
    return dataset_name


def make_target(prompt_version: str = "v1"):
    """Create a target function for langsmith.evaluate().

    The target takes a dict of inputs (alert fields) and returns
    a dict of outputs (classification fields).
    """
    client = init_client()

    def target(inputs: dict) -> dict:
        alert = SecurityAlert(**inputs)
        result = classify_alert(
            alert, client=client, prompt_version=prompt_version,
            langsmith_extra={"metadata": {"prompt_version": prompt_version}},
        )
        return {
            "severity": result.severity.value,
            "category": result.category.value,
            "confidence": result.confidence,
            "reasoning": result.reasoning,
        }

    return target


def make_severity_evaluator():
    """Evaluator: does the predicted severity match the expected?"""
    def severity_match(run, example) -> dict:
        predicted = run.outputs.get("severity", "")
        expected = example.outputs.get("severity", "")
        return {"key": "severity_match", "score": 1.0 if predicted == expected else 0.0}
    return severity_match


def make_category_evaluator():
    """Evaluator: does the predicted category match the expected?"""
    def category_match(run, example) -> dict:
        predicted = run.outputs.get("category", "")
        expected = example.outputs.get("category", "")
        return {"key": "category_match", "score": 1.0 if predicted == expected else 0.0}
    return category_match


def run_evaluation(
    golden_set_path: str,
    prompt_version: str = "v1",
    dataset_name: str = "security-alert-triage",
) -> None:
    """Run the classifier against the golden set using LangSmith evaluate().

    This creates a LangSmith Experiment that you can view in the dashboard,
    compare side-by-side with other prompt versions, and drill into per-example.
    """
    # Load and upload golden set
    examples = load_golden_set(golden_set_path)
    upload_dataset(examples, dataset_name)

    # Run evaluation — this creates an Experiment in LangSmith
    experiment_name = f"triage-{prompt_version}"
    results = evaluate(
        make_target(prompt_version),
        data=dataset_name,
        evaluators=[make_severity_evaluator(), make_category_evaluator()],
        experiment_prefix=experiment_name,
        metadata={"prompt_version": prompt_version},
    )

    print(f"\nExperiment '{experiment_name}' logged to LangSmith.")
    print("Open your LangSmith dashboard to view results and compare prompt versions.")


def main():
    parser = argparse.ArgumentParser(description="Run eval against golden set via LangSmith")
    parser.add_argument(
        "--golden-set", type=str, default="data/golden_set.json",
        help="Path to golden set JSON",
    )
    parser.add_argument(
        "--prompt-version", type=str, default="v1",
        help="Prompt version to evaluate",
    )
    parser.add_argument(
        "--dataset-name", type=str, default="security-alert-triage",
        help="LangSmith dataset name",
    )
    args = parser.parse_args()

    run_evaluation(args.golden_set, prompt_version=args.prompt_version, dataset_name=args.dataset_name)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
python -m pytest tests/test_run_eval.py -v
```

Expected: All 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add evals/run_eval.py tests/test_run_eval.py
git commit -m "feat: add eval runner using LangSmith evaluate() for experiment tracking"
```

---

## Chunk 6: CLAUDE.md & Smoke Test

### Task 10: Project CLAUDE.md

**Files:**
- Create: `CLAUDE.md`

- [ ] **Step 1: Create CLAUDE.md**

```markdown
# LLM Tracing Lab

Learning project: security alert triage classifier with LangSmith tracing and evals.

## Stack
Python 3.11+, Anthropic SDK, LangSmith, Pydantic

## Setup
```bash
python -m venv .venv
source .venv/Scripts/activate   # Windows git bash
pip install -r requirements.txt
cp .env.example .env            # Fill in API keys
```

## Commands
- Classify single alert: `python scripts/classify.py --alert "alert text here"`
- Classify batch: `python scripts/classify.py --batch data/sample_alerts.json`
- Run evals: `python evals/run_eval.py --prompt-version v1`
- Run tests: `python -m pytest tests/ -v`

## Key Concepts
- `src/tracing.py`: `init_client()` returns a wrapped Anthropic client (auto-traces API calls)
- `@traceable` decorator on `classify_alert()` creates parent spans in LangSmith
- `src/prompts.py`: versioned prompts — add new versions and compare via evals
- `data/golden_set.json`: hand-labeled ground truth for scoring
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add project CLAUDE.md with setup and command reference"
```

---

### Task 11: End-to-end smoke test

- [ ] **Step 1: Run full test suite**

```bash
source .venv/Scripts/activate
python -m pytest tests/ -v
```

Expected: All tests pass.

- [ ] **Step 2: Smoke test with real API (manual)**

Set up `.env` with real API keys, then:

```bash
python scripts/classify.py --alert "Multiple failed login attempts from IP 203.0.113.42 targeting admin@company.com over 5 minutes"
```

Expected: Prints a classification. Check LangSmith dashboard — you should see a trace with parent span `classify_alert` and a child span for the Anthropic API call.

- [ ] **Step 3: Run batch classification**

```bash
python scripts/classify.py --batch data/sample_alerts.json --prompt-version v1
```

Expected: Classifies all 20 alerts. LangSmith dashboard shows 20 traces.

- [ ] **Step 4: Run eval**

```bash
python evals/run_eval.py --prompt-version v1
```

Expected: Prints per-alert pass/fail and aggregate scores. LangSmith shows traces for the eval run.

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "chore: finalize project scaffold and verify end-to-end workflow"
```
