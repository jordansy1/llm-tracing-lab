import json
import re

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

    # Strip markdown code fences if Claude wraps the JSON
    cleaned = raw_text.strip()
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)```", cleaned, re.DOTALL)
    if fence_match:
        cleaned = fence_match.group(1).strip()

    try:
        data = json.loads(cleaned)
        return Classification(**data)
    except (json.JSONDecodeError, ValueError) as e:
        raise ValueError(
            f"Failed to parse classification from Claude response: {e}\n"
            f"Raw response: {raw_text!r}"
        )
