"""Anthropic provider client."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from .errors import ProviderError


class AnthropicClient:
    """Simple Anthropic Messages client using stdlib HTTP."""

    def __init__(self, timeout_seconds: float) -> None:
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ProviderError("ANTHROPIC_API_KEY is not set")

        self.url = "https://api.anthropic.com/v1/messages"
        self.timeout_seconds = timeout_seconds

    def generate(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
    ) -> str:
        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": 0,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }

        request = urllib.request.Request(
            self.url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                body = response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise ProviderError(f"Anthropic API error ({exc.code}): {detail}") from exc
        except urllib.error.URLError as exc:
            raise ProviderError(f"Anthropic request failed: {exc.reason}") from exc

        try:
            data = json.loads(body.decode("utf-8"))
            content = data["content"]
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            raise ProviderError("unexpected Anthropic response format") from exc

        if not isinstance(content, list):
            raise ProviderError("unexpected Anthropic response content format")

        texts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text")
                if isinstance(text, str) and text:
                    texts.append(text)

        if not texts:
            raise ProviderError("Anthropic response did not include text content")

        return "\n".join(texts)
