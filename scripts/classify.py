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
