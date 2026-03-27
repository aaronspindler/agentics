"""Provider dispatch."""

from __future__ import annotations

from .anthropic_client import AnthropicClient
from .errors import ProviderError
from .openai_client import OpenAIClient


def generate_response(
    provider: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
    timeout_seconds: float,
) -> str:
    """Generate raw model output text for a configured provider."""
    if provider == "openai":
        client = OpenAIClient(timeout_seconds=timeout_seconds)
        return client.generate(
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=max_tokens,
        )

    if provider == "anthropic":
        client = AnthropicClient(timeout_seconds=timeout_seconds)
        return client.generate(
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=max_tokens,
        )

    raise ProviderError(f"unsupported provider: {provider}")


__all__ = ["ProviderError", "generate_response"]
