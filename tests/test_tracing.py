from unittest.mock import MagicMock, patch

from src.tracing import init_client


@patch("src.tracing.wrap_anthropic")
@patch("src.tracing.anthropic.Anthropic")
def test_init_client_returns_wrapped_anthropic(mock_anthropic_cls, mock_wrap):
    """init_client should create an Anthropic client and wrap it for tracing."""
    mock_raw_client = MagicMock()
    mock_anthropic_cls.return_value = mock_raw_client
    mock_wrapped = MagicMock()
    mock_wrap.return_value = mock_wrapped

    result = init_client()

    mock_anthropic_cls.assert_called_once()
    mock_wrap.assert_called_once_with(mock_raw_client)
    assert result is mock_wrapped
