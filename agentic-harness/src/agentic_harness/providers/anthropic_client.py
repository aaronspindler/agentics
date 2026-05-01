"""Anthropic provider client with tool_use support."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from .errors import ProviderError


class AnthropicClient:
    """Anthropic Messages client using stdlib HTTP, extended with tool_use."""

    def __init__(self, timeout_seconds: float) -> None:
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ProviderError("ANTHROPIC_API_KEY is not set")

        self.url = "https://api.anthropic.com/v1/messages"
        self.timeout_seconds = timeout_seconds

    def _request(self, payload: dict) -> dict:
        """Make a single API request and return the parsed response body."""
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
            return json.loads(body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ProviderError("unexpected Anthropic response format") from exc

    def generate(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        tools: list[dict] | None = None,
        messages: list[dict] | None = None,
    ) -> dict:
        """Call the Messages API and return the full response body.

        When ``messages`` is provided, it is used directly (for multi-turn
        tool-use conversations). Otherwise a single user message is built
        from ``user_prompt``.

        Returns the raw response dict so the caller can inspect
        ``stop_reason`` and handle ``tool_use`` blocks.
        """
        if messages is None:
            messages = [{"role": "user", "content": user_prompt}]

        payload: dict = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": 0,
            "system": system_prompt,
            "messages": messages,
        }

        if tools:
            payload["tools"] = tools

        data = self._request(payload)

        content = data.get("content")
        if not isinstance(content, list):
            raise ProviderError("unexpected Anthropic response content format")

        return data

    def extract_text(self, response: dict) -> str:
        """Extract concatenated text blocks from a response."""
        content = response.get("content", [])
        texts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text")
                if isinstance(text, str) and text:
                    texts.append(text)
        return "\n".join(texts)

    def extract_tool_uses(self, response: dict) -> list[dict]:
        """Extract tool_use blocks from a response."""
        content = response.get("content", [])
        tool_uses: list[dict] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "tool_use":
                tool_uses.append(item)
        return tool_uses
