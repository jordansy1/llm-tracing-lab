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
