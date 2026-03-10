import pytest

from src.prompts import get_prompt, PROMPT_V1


def test_prompt_v1_exists():
    assert isinstance(PROMPT_V1, str)
    assert "severity" in PROMPT_V1.lower()
    assert "category" in PROMPT_V1.lower()


def test_get_prompt_v1():
    prompt = get_prompt("v1")
    assert prompt == PROMPT_V1


def test_get_prompt_invalid_version():
    with pytest.raises(KeyError):
        get_prompt("v999")
