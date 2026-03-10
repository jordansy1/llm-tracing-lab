# LLM Tracing Lab — Design Spec

**Date:** 2026-03-10
**Location:** `Code Projects/Testing/llm-tracing-lab/`
**Purpose:** Learning project to understand LLM tracing and evals through a security alert triage classifier.

## Overview

A security alert triage classifier that uses Claude (via raw Anthropic SDK) to categorize alerts by severity and type. Every LLM call is traced to LangSmith. Traced data feeds an eval pipeline that scores prompt versions against a hand-labeled golden set, enabling systematic prompt iteration.

**Approach:** LangSmith + Raw Anthropic SDK (no LangChain). Manual trace instrumentation teaches tracing mechanics; LangSmith evals handle the scoring/comparison workflow.

## Stack

- Python 3.11+
- Anthropic SDK (direct API calls)
- LangSmith SDK (`langsmith` package) for tracing + evals
- Pydantic for data models
- python-dotenv for env config
- Virtual environment at `.venv/`

## Directory Structure

```
llm-tracing-lab/
├── CLAUDE.md
├── requirements.txt
├── .env.example          # ANTHROPIC_API_KEY, LANGSMITH_API_KEY
├── .gitignore
├── src/
│   ├── classifier.py     # Core: takes an alert, returns classification via Claude
│   ├── tracing.py        # LangSmith tracing setup and decorators
│   ├── prompts.py        # System prompts (versioned — v1, v2, etc.)
│   └── models.py         # Pydantic models for alerts and classifications
├── data/
│   ├── sample_alerts.json    # 20-30 synthetic security alerts
│   └── golden_set.json       # Hand-labeled ground truth for evals
├── evals/
│   ├── run_eval.py       # Runs classifier against golden_set, scores results
│   └── scorers.py        # Scoring functions (exact match, partial credit)
├── scripts/
│   └── classify.py       # CLI entry point: classify single alert or batch
└── docs/
    └── superpowers/specs/
        └── 2026-03-10-llm-tracing-lab-design.md  # This file
```

## Components

### Models (`src/models.py`)

Pydantic models for structured data:

- **SecurityAlert**: `id`, `timestamp`, `source`, `raw_text`, `metadata` (dict)
- **Classification**: `severity` (critical/high/medium/low), `category` (phishing/brute_force/data_exfiltration/credential_abuse/insider_threat/malware), `confidence` (float 0-1), `reasoning` (str)
- **EvalResult**: `alert_id`, `expected` (Classification), `actual` (Classification), `severity_match` (bool), `category_match` (bool)

### Classifier (`src/classifier.py`)

Single function `classify_alert(alert, prompt_version)` that:
1. Loads the system prompt for the given version from `prompts.py`
2. Calls Claude via Anthropic SDK (model: claude-haiku-4-5 for cost-efficiency during learning)
3. Parses the structured JSON response into a Classification model
4. Returns the result

Decorated with `@traceable` so LangSmith captures the full input/output.

### Tracing (`src/tracing.py`)

Setup module that:
1. Initializes LangSmith client from env vars
2. Provides `wrap_anthropic()` to auto-trace raw Anthropic SDK calls (child spans: messages, tokens, latency)
3. Re-exports `@traceable` decorator for application-level spans

Two tracing layers:
- **Infrastructure**: `wrap_anthropic()` patches the Anthropic client to auto-log every API call
- **Application**: `@traceable` wraps business logic functions as parent spans

### Prompts (`src/prompts.py`)

System prompts as named string constants:
- `PROMPT_V1`: Baseline — simple classification instructions
- `PROMPT_V2`, `PROMPT_V3`, etc.: Iterations based on eval results

A `get_prompt(version)` function returns the prompt string and attaches the version as trace metadata.

### Sample Data (`data/sample_alerts.json`)

20-30 synthetic security alerts covering:
- All 6 categories (phishing, brute_force, data_exfiltration, credential_abuse, insider_threat, malware)
- All 4 severity levels
- Edge cases (ambiguous alerts that could be multiple categories)

### Golden Set (`data/golden_set.json`)

~15 alerts with hand-labeled expected classifications. This is the ground truth for evals — curated by the user as part of the learning process.

### Eval Runner (`evals/run_eval.py`)

Runs the classifier against the golden set for a given prompt version:
1. Loads golden_set.json
2. Classifies each alert using the specified prompt version
3. Scores results using scorers
4. Prints a summary table (accuracy per category, overall score)
5. Logs the experiment to LangSmith for dashboard comparison

### Scorers (`evals/scorers.py`)

Scoring functions:
- `severity_accuracy`: Exact match on severity level
- `category_accuracy`: Exact match on category
- `overall_score`: Weighted combination (e.g., 40% severity + 60% category)

### CLI (`scripts/classify.py`)

Entry point for interactive use:
- `python scripts/classify.py --alert "..."` — classify a single alert, print result
- `python scripts/classify.py --batch data/sample_alerts.json` — classify all, print summary
- All calls traced to LangSmith automatically

## Data Flow

```
CLI (classify.py or run_eval.py)
  │
  ▼
@traceable classify_alert()  ──── parent span → LangSmith
  │
  ▼
wrap_anthropic() Claude API   ──── child span → LangSmith (tokens, latency, model)
  │
  ▼
Pydantic Classification       ──── structured result back to caller + LangSmith
```

Each classification produces a two-level trace:
1. **Parent span** (`classify_alert`): alert input, Classification output, prompt version metadata
2. **Child span** (Anthropic API call): messages, model, tokens used, latency

## The Learning Loop

1. **Trace** — Run classifier on sample alerts; everything auto-traced to LangSmith
2. **Inspect** — View traces in LangSmith dashboard (inputs, outputs, latency, tokens, cost)
3. **Build eval dataset** — Curate golden_set.json with expected classifications
4. **Run evals** — Score prompt versions against golden set, log experiments to LangSmith
5. **Iterate** — Edit prompts.py (add v2), re-run evals, compare v1 vs v2 side-by-side in dashboard
6. **Repeat** — Continue improving until satisfied with accuracy

## Environment Setup

- Virtual environment: `.venv/` (created with `python -m venv .venv`)
- Dependencies in `requirements.txt`: `anthropic`, `langsmith`, `pydantic`, `python-dotenv`
- `.env.example` with: `ANTHROPIC_API_KEY`, `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT` (project name in LangSmith)
- `.gitignore`: `.venv/`, `.env`, `__pycache__/`

## Key Design Decisions

1. **Raw Anthropic SDK over LangChain** — Matches existing project stack, teaches tracing mechanics by requiring manual instrumentation
2. **Haiku for classifier** — Cost-efficient for a learning project with many iterations; upgrade to Sonnet if classification quality needs it
3. **Versioned prompts as constants** — Simple, diffable, no config complexity. Version string attached to traces for filtering
4. **Hand-labeled golden set** — Forces engagement with the data; no auto-generated ground truth
5. **Pydantic throughout** — Consistent with workshop_automation patterns; structured outputs make scoring straightforward
