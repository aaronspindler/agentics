"""Provider dispatch for LLM API calls."""

from __future__ import annotations

from .errors import ProviderError


def generate_response(
    *,
    provider: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
    tools: list[dict] | None = None,
    messages: list[dict] | None = None,
    timeout_seconds: float = 120.0,
) -> dict:
    """Dispatch an LLM call to the selected provider.

    Returns the raw API response body as a dict.
    """
    if provider == "anthropic":
        from .anthropic_client import AnthropicClient

        client = AnthropicClient(timeout_seconds=timeout_seconds)
        return client.generate(
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=max_tokens,
            tools=tools,
            messages=messages,
        )
    elif provider == "openai":
        from .openai_client import OpenAIClient

        client = OpenAIClient(timeout_seconds=timeout_seconds)
        return client.generate(
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=max_tokens,
            tools=tools,
            messages=messages,
        )
    else:
        raise ProviderError(f"unsupported provider: {provider}")
