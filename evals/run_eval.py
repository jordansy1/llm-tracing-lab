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
