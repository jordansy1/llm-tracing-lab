# LLM Tracing Lab — Learning Review

## Session: 2026-03-10

### What This Project Is
A security alert triage classifier that uses Claude (via the raw Anthropic SDK) to categorize alerts by severity and category. Every LLM call is traced to LangSmith, and an eval pipeline scores prompt versions against a hand-labeled golden set.

---

### Concepts Learned

#### 1. Two Layers of Tracing
- **`wrap_anthropic()`** — wraps the Anthropic client to auto-trace every API call (tokens, latency, model, full request/response). This is the infrastructure layer; no code changes needed to your API calls.
- **`@traceable` decorator** — wraps your business logic functions as parent spans. Captures function inputs, outputs, and timing.
- When a wrapped client call happens inside a `@traceable` function, LangSmith auto-nests them as parent/child spans via Python context variables.

#### 2. Configuration via Environment Variables
- `LANGSMITH_API_KEY` — authenticates with LangSmith
- `LANGSMITH_TRACING=true` — master on/off switch for all tracing
- `LANGSMITH_PROJECT` — groups traces into a named project in the dashboard
- These are read automatically by the `langsmith` SDK; `load_dotenv()` must run before imports that touch LangSmith.

#### 3. LangSmith Dashboard Structure
- **Projects** hold raw traces (every API call and function span)
- **Datasets** hold input/output example pairs (like our golden set)
- **Experiments** are eval runs against a dataset, scored by evaluators — found under Datasets & Testing, not under Projects

#### 4. Eval Pipeline (`langsmith.evaluate()`)
- **Dataset**: Upload golden set examples (inputs + expected outputs) to LangSmith
- **Target function**: Takes inputs, runs the classifier, returns outputs
- **Evaluators**: Scoring functions that compare predicted vs expected (severity_match, category_match)
- **Experiment**: A named snapshot of scores — enables side-by-side comparison between prompt versions

#### 5. Annotation Queues (Manual Eval)
- Created in LangSmith UI under Annotation Queues
- Define a rubric with feedback types:
  - **Categorical** — fixed labels (e.g., error_type: wrong_severity | wrong_category)
  - **Continuous** — numeric scale (e.g., reasoning_quality: 1-5)
  - **Freeform** — open text for notes and observations
- Runs are sent to the queue via `client.add_runs_to_annotation_queue()`
- Reviewers score each run against the rubric in a focused UI
- Annotations attach to the run objects and are queryable via `client.list_feedback()`

#### 6. The Prompt Iteration Loop
1. Run classifier → traces go to LangSmith
2. Run eval → experiment scores appear in dashboard
3. Send runs to annotation queue → manual review with rubric
4. Pull feedback → `summarize_feedback.py` extracts notes
5. Synthesize themes → `--synthesize` flag uses Claude to identify top failure patterns
6. Write new prompt version → add to `_PROMPTS` dict in `src/prompts.py`
7. Re-run eval → compare experiments side by side
8. Repeat

#### 7. Prompt Engineering vs. Data Enrichment
Two kinds of output quality problems:
- **Model had the info but used it wrong** → fix with prompt changes (e.g., adding severity criteria)
- **Model didn't have the info** → fix with enrichment before the LLM call (e.g., domain reputation lookup from AbuseIPDB)

Enrichment is pipeline-side Python code that calls external APIs and adds context to the user message before it reaches Claude.

---

### Results

| Metric | v1 | v2 | Change |
|--------|----|----|--------|
| category_match | 0.93 | 0.93 | — |
| severity_match | 0.67 | 0.87 | +0.20 |

v2 added explicit severity criteria definitions. The 20-point severity improvement confirmed that Claude was over-predicting "critical" because v1 gave no guidance on distinguishing severity levels.

---

### Key Files
- `src/tracing.py` — `init_client()` with `wrap_anthropic`
- `src/classifier.py` — `@traceable` classify_alert function
- `src/prompts.py` — versioned prompts (v1 and v2), `_PROMPTS` dict
- `evals/run_eval.py` — eval runner with `langsmith.evaluate()`
- `evals/scorers.py` — severity_accuracy, category_accuracy, overall_score
- `scripts/classify.py` — CLI for single and batch classification
- `scripts/send_to_review.py` — sends runs to annotation queue
- `scripts/summarize_feedback.py` — pulls annotations, optionally synthesizes themes
- `data/golden_set.json` — 15 hand-labeled examples for eval

---

### Next Steps to Explore
- [ ] Investigate the 2 remaining severity mismatches in v2 via annotation queue
- [ ] Add data enrichment (domain reputation, IP geolocation) before the LLM call
- [ ] Try an LLM-as-judge evaluator for reasoning quality
- [ ] Explore pairwise annotation queues (compare two outputs side-by-side)
- [ ] Add a v3 prompt incorporating engagement metrics for phishing alerts
