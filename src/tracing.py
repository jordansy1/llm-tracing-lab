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
