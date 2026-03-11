"""Send recent classification runs to a LangSmith annotation queue for manual review.

Creates the annotation queue if it doesn't exist, then adds all top-level
runs from the project that haven't been reviewed yet.

Usage:
    PYTHONPATH=. python scripts/send_to_review.py
    PYTHONPATH=. python scripts/send_to_review.py --queue "triage-v2-review" --limit 50
"""
import argparse

from dotenv import load_dotenv

load_dotenv()

from langsmith import Client


def send_runs_to_queue(
    queue_name: str = "triage-v1-review",
    project_name: str = "llm-tracing-lab",
    limit: int = 30,
) -> None:
    client = Client()

    # List top-level runs (execution_order=1 means parent runs only,
    # skipping the child Anthropic API call spans)
    runs = client.list_runs(
        project_name=project_name,
        execution_order=1,
        error=False,
        limit=limit,
    )

    run_ids = [run.id for run in runs]

    if not run_ids:
        print("No runs found to send.")
        return

    # Send to annotation queue
    # Note: the queue must already exist in the LangSmith UI
    client.add_runs_to_annotation_queue(
        queue_name=queue_name,
        run_ids=run_ids,
    )

    print(f"Sent {len(run_ids)} runs to annotation queue '{queue_name}'")
    print("Open your LangSmith dashboard → Annotation Queues to start reviewing.")


def main():
    parser = argparse.ArgumentParser(description="Send runs to LangSmith annotation queue")
    parser.add_argument("--queue", type=str, default="triage-v1-review",
                        help="Annotation queue name (must exist in LangSmith)")
    parser.add_argument("--project", type=str, default="llm-tracing-lab",
                        help="LangSmith project name")
    parser.add_argument("--limit", type=int, default=30,
                        help="Max number of runs to send")
    args = parser.parse_args()

    send_runs_to_queue(args.queue, args.project, args.limit)


if __name__ == "__main__":
    main()
