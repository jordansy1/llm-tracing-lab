"""Pull annotation feedback from LangSmith and summarize failure themes.

Fetches all human feedback from reviewed runs, groups notes by failure
pattern, and optionally uses Claude to synthesize themes into prompt
improvement suggestions.

Usage:
    PYTHONPATH=. python scripts/summarize_feedback.py
    PYTHONPATH=. python scripts/summarize_feedback.py --synthesize
"""
import argparse
import json
from collections import defaultdict

from dotenv import load_dotenv

load_dotenv()

from langsmith import Client

from src.tracing import init_client


def collect_feedback(project_name: str = "llm-tracing-lab") -> list[dict]:
    """Pull all runs that have human feedback attached."""
    client = Client()

    runs = client.list_runs(
        project_name=project_name,
        execution_order=1,
        has_feedback=True,
    )

    results = []
    for run in runs:
        feedbacks = list(client.list_feedback(run_ids=[run.id]))

        entry = {
            "run_id": str(run.id),
            "alert_text": run.inputs.get("alert", {}).get("raw_text", "")
                if isinstance(run.inputs.get("alert"), dict)
                else str(run.inputs),
            "predicted": run.outputs or {},
            "feedback": {},
        }

        for fb in feedbacks:
            entry["feedback"][fb.key] = {
                "score": fb.score,
                "comment": fb.comment,
            }

        results.append(entry)

    return results


def print_summary(results: list[dict]) -> None:
    """Print a summary of feedback grouped by failure type."""
    total = len(results)
    if total == 0:
        print("No feedback found. Review some runs in LangSmith first.")
        return

    severity_wrong = []
    category_wrong = []
    all_notes = []

    for r in results:
        fb = r["feedback"]
        if fb.get("severity_correct", {}).get("score") == 0:
            severity_wrong.append(r)
        if fb.get("category_correct", {}).get("score") == 0:
            category_wrong.append(r)

        note = fb.get("notes", {}).get("comment", "")
        if note:
            all_notes.append({"alert": r["alert_text"][:80], "note": note})

    print(f"=== Feedback Summary ({total} reviewed runs) ===\n")
    print(f"Severity incorrect: {len(severity_wrong)}/{total}")
    print(f"Category incorrect: {len(category_wrong)}/{total}")
    print(f"Runs with notes:    {len(all_notes)}/{total}\n")

    if all_notes:
        print("--- Reviewer Notes ---")
        for n in all_notes:
            print(f"  [{n['alert']}...]")
            print(f"    {n['note']}\n")


def synthesize_themes(results: list[dict]) -> None:
    """Use Claude to identify common failure themes and suggest prompt fixes."""
    all_notes = []
    for r in results:
        note = r["feedback"].get("notes", {}).get("comment", "")
        if note:
            all_notes.append({
                "alert_snippet": r["alert_text"][:120],
                "predicted": {
                    k: v for k, v in r["predicted"].items()
                    if k in ("severity", "category", "reasoning")
                },
                "reviewer_note": note,
            })

    if not all_notes:
        print("\nNo reviewer notes to synthesize.")
        return

    client = init_client()
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system="""You are analyzing reviewer feedback on an LLM security alert classifier.
Given a set of reviewer notes about classification failures, identify:
1. The top 3-5 recurring failure themes (e.g., "model over-predicts critical severity")
2. For each theme, a specific prompt modification that would address it
3. Priority ranking of which fixes would have the most impact

Be concise and actionable. Format as a numbered list.""",
        messages=[{"role": "user", "content": json.dumps(all_notes, indent=2)}],
    )

    print("\n=== AI-Synthesized Themes & Suggested Fixes ===\n")
    text = response.content[0].text
    # Replace Unicode characters that Windows cp1252 can't encode
    text = text.encode("ascii", errors="replace").decode("ascii")
    print(text)


def main():
    parser = argparse.ArgumentParser(description="Summarize annotation feedback from LangSmith")
    parser.add_argument("--project", type=str, default="llm-tracing-lab")
    parser.add_argument("--synthesize", action="store_true",
                        help="Use Claude to synthesize notes into prompt fix suggestions")
    args = parser.parse_args()

    results = collect_feedback(args.project)
    print_summary(results)

    if args.synthesize:
        synthesize_themes(results)


if __name__ == "__main__":
    main()
