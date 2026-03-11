# LLM Tracing Lab

A learning project that builds a security alert triage classifier with end-to-end LLM observability. Every Claude API call is traced to LangSmith, and an evaluation pipeline scores prompt versions against a hand-labeled golden set.

**Core question this project explores:** How do you systematically improve an LLM classifier using tracing, automated evals, and qualitative human annotation — rather than guessing?

---

## What It Does

The system takes raw security alerts (failed logins, suspicious network traffic, malware detections, etc.) and uses Claude to classify each one by:

- **Severity** — `low`, `medium`, `high`, or `critical`
- **Category** — e.g., `brute_force`, `malware`, `phishing`, `data_exfiltration`
- **Confidence** — 0.0–1.0 float
- **Reasoning** — a brief natural language explanation

Every classification is automatically traced to LangSmith, creating a full audit trail of inputs, outputs, token usage, and latency.

---

## Stack

- **Python 3.11+**
- **Anthropic SDK** (Claude Haiku) — the classifier model
- **LangSmith** — tracing, datasets, experiments, annotation queues
- **Pydantic** — data validation for alerts and classifications
- **pytest** — unit and integration tests

---

## Setup

```bash
# 1. Create and activate virtual environment
python -m venv .venv
source .venv/Scripts/activate   # Windows git bash
# or: .venv\Scripts\activate    # Windows cmd/PowerShell

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Fill in: ANTHROPIC_API_KEY, LANGSMITH_API_KEY, LANGSMITH_PROJECT
```

### Required environment variables

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Your Anthropic API key |
| `LANGSMITH_API_KEY` | Your LangSmith API key |
| `LANGSMITH_TRACING` | Set to `true` to enable tracing |
| `LANGSMITH_PROJECT` | Project name in LangSmith dashboard (e.g. `llm-tracing-lab`) |

---

## Usage

### Classify a single alert
```bash
PYTHONPATH=. python scripts/classify.py --alert "Failed SSH login from 192.168.1.100 — 47 attempts in 60 seconds"
```

### Classify a batch from JSON
```bash
PYTHONPATH=. python scripts/classify.py --batch data/sample_alerts.json
```

### Run evals against the golden set
```bash
PYTHONPATH=. python evals/run_eval.py --prompt-version v1
PYTHONPATH=. python evals/run_eval.py --prompt-version v2
```
Results appear as named Experiments under **Datasets & Testing** in LangSmith.

### Send runs to annotation queue for manual review
```bash
PYTHONPATH=. python scripts/send_to_review.py --queue "triage-v2-review" --limit 30
```

### Pull and summarize annotation feedback
```bash
# Print summary of reviewer scores and notes
PYTHONPATH=. python scripts/summarize_feedback.py

# Use Claude to synthesize failure themes and suggest prompt fixes
PYTHONPATH=. python scripts/summarize_feedback.py --synthesize
```

### Run tests
```bash
python -m pytest tests/ -v
```

---

## Project Structure

```
llm-tracing-lab/
├── src/
│   ├── tracing.py       # init_client() — wraps Anthropic client for auto-tracing
│   ├── classifier.py    # classify_alert() — @traceable LLM classification function
│   ├── prompts.py       # Versioned system prompts (_PROMPTS dict: v1, v2, ...)
│   └── models.py        # Pydantic models: SecurityAlert, Classification
├── evals/
│   ├── run_eval.py      # Eval runner using langsmith.evaluate()
│   └── scorers.py       # Scoring functions: severity_accuracy, category_accuracy
├── scripts/
│   ├── classify.py          # CLI for single and batch classification
│   ├── send_to_review.py    # Sends runs to LangSmith annotation queue
│   └── summarize_feedback.py # Pulls annotations, synthesizes themes with Claude
├── data/
│   ├── golden_set.json      # 15 hand-labeled examples (ground truth for evals)
│   └── sample_alerts.json   # Example alerts for testing
└── tests/                   # pytest test suite
```

---

## How Tracing Works

Two layers work together to give full visibility into every classification:

**1. `wrap_anthropic()` — infrastructure layer**

Wraps the Anthropic client to automatically capture every API call: model, tokens used, latency, full request/response. No changes needed to API call code.

```python
# src/tracing.py
raw_client = anthropic.Anthropic()
return wrap_anthropic(raw_client)  # every .messages.create() call is now traced
```

**2. `@traceable` decorator — business logic layer**

Wraps `classify_alert()` as a parent span that captures function inputs and outputs. When the wrapped client makes an API call inside a `@traceable` function, LangSmith auto-nests them as parent/child spans.

```python
# src/classifier.py
@traceable(name="classify_alert", metadata={"component": "classifier"})
def classify_alert(alert, client, prompt_version="v1"):
    ...
```

The result in LangSmith: a parent span showing the full classification (what went in, what came out) with a nested child span showing the raw API call.

---

## Eval Pipeline

The eval pipeline scores prompt versions against `data/golden_set.json` — 15 hand-labeled alerts with expected severity and category.

```
golden_set.json → LangSmith Dataset → langsmith.evaluate() → Experiment (scores)
```

**Evaluators:**
- `severity_match` — 1.0 if predicted severity equals expected, else 0.0
- `category_match` — 1.0 if predicted category equals expected, else 0.0

Running the same eval against different prompt versions creates named Experiments you can compare side by side in the LangSmith dashboard.

**Results from this project:**

| Metric | v1 | v2 | Change |
|---|---|---|---|
| category_match | 0.93 | 0.93 | — |
| severity_match | 0.67 | 0.87 | **+0.20** |

v2 added explicit severity criteria definitions. The 20-point severity improvement confirmed that Claude was over-predicting `critical` because v1 gave no guidance on distinguishing severity levels.

---

## Qualitative Annotation in LangSmith

Beyond automated scores, we used LangSmith's **Annotation Queues** for manual qualitative review — examining *why* the model got things wrong, not just *whether* it did.

### How Annotation Queues Work

An annotation queue is a review interface in LangSmith where you can score individual runs against a custom rubric. We defined three feedback types:

| Feedback key | Type | Purpose |
|---|---|---|
| `severity_correct` | Categorical (0/1) | Was the severity label right? |
| `category_correct` | Categorical (0/1) | Was the category label right? |
| `reasoning_quality` | Continuous (1–5) | Was the reasoning coherent and specific? |
| `notes` | Freeform text | Free-text observations about failure patterns |

### The Review Workflow

1. Run the classifier on a batch of alerts — traces are sent to LangSmith automatically
2. Push runs to a named queue: `python scripts/send_to_review.py --queue "triage-v2-review"`
3. Open LangSmith → **Annotation Queues** → work through the queue, scoring each run
4. Pull feedback: `python scripts/summarize_feedback.py`
5. Use `--synthesize` to have Claude read all reviewer notes and identify top failure themes

### What Qualitative Review Catches That Metrics Miss

Automated evals give you a score. Manual annotation tells you the *pattern* behind the score. Examples from this project:

- **Severity over-prediction:** The model was calling alerts `critical` when they were `high`. The automated `severity_match` score flagged this as wrong, but reviewer notes made it clear the model lacked explicit criteria for the distinction — leading directly to the v2 prompt fix.
- **Confident-but-wrong reasoning:** Some misclassified runs had well-structured, plausible-sounding reasoning that happened to be wrong. These wouldn't stand out without reading them — the `reasoning_quality` score surfaced them for review.
- **Ambiguous alert text:** Several alerts were genuinely borderline (e.g., a single failed login vs. a brute force attempt). Reviewer notes flagged these as "edge cases" rather than model failures — useful signal for improving the golden set, not the prompt.

### Closing the Loop

The `--synthesize` flag in `summarize_feedback.py` sends all reviewer notes to Claude and asks it to identify the top failure themes and suggest specific prompt modifications. This turns qualitative human observations into actionable prompt engineering tasks.

---

## The Prompt Iteration Loop

```
classify alerts
      ↓
traces → LangSmith
      ↓
run eval → experiment scores
      ↓
send runs → annotation queue → manual review
      ↓
summarize_feedback.py --synthesize → failure themes
      ↓
write new prompt version in src/prompts.py
      ↓
re-run eval → compare experiments
      ↓
repeat
```

---

## Key Concepts

- **Prompt versioning** — prompts live in a `_PROMPTS` dict in `src/prompts.py`. Adding a new version is one dict entry; comparing it to v1 is one eval run.
- **Prompt engineering vs. data enrichment** — if the model had the information but used it wrong, fix the prompt. If the model lacked information (e.g., whether an IP is known-malicious), fix the pipeline by enriching the input before the LLM call.
- **LangSmith hierarchy** — Projects hold raw traces; Datasets hold labeled examples; Experiments are eval runs scored against a dataset. Experiments are found under Datasets & Testing, not Projects.

For a deeper walkthrough of concepts learned building this project, see [`learning_review.md`](learning_review.md).

---

## Next Steps

- [ ] Investigate the 2 remaining severity mismatches in v2 via annotation queue
- [ ] Add data enrichment (domain reputation lookup, IP geolocation) before the LLM call
- [ ] Try an LLM-as-judge evaluator for reasoning quality
- [ ] Explore pairwise annotation queues (compare two model outputs side by side)
- [ ] Add a v3 prompt incorporating engagement metrics for phishing alerts
