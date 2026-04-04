"""OpenAI provider client with tool_use (function calling) support."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from .errors import ProviderError


def _anthropic_tools_to_openai(tools: list[dict]) -> list[dict]:
    """Convert Anthropic-style tool defs to OpenAI function-calling format."""
    converted: list[dict] = []
    for tool in tools:
        converted.append(
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("input_schema", {}),
                },
            }
        )
    return converted


class OpenAIClient:
    """OpenAI Chat Completions client using stdlib HTTP, with function calling."""

    def __init__(self, timeout_seconds: float) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ProviderError("OPENAI_API_KEY is not set")

        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com").rstrip("/")
        if base_url.endswith("/v1"):
            self.url = f"{base_url}/chat/completions"
        else:
            self.url = f"{base_url}/v1/chat/completions"
        self.timeout_seconds = timeout_seconds

    def _request(self, payload: dict) -> dict:
        request = urllib.request.Request(
            self.url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                body = response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise ProviderError(f"OpenAI API error ({exc.code}): {detail}") from exc
        except urllib.error.URLError as exc:
            raise ProviderError(f"OpenAI request failed: {exc.reason}") from exc

        try:
            return json.loads(body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ProviderError("unexpected OpenAI response format") from exc

    def generate(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        tools: list[dict] | None = None,
        messages: list[dict] | None = None,
    ) -> dict:
        """Call the Chat Completions API and return the full response body.

        Accepts Anthropic-style tool definitions and converts them to
        OpenAI function-calling format internally.
        """
        if messages is None:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        else:
            messages = [{"role": "system", "content": system_prompt}] + messages

        payload: dict = {
            "model": model,
            "temperature": 0,
            "max_tokens": max_tokens,
            "messages": messages,
        }

        if tools:
            payload["tools"] = _anthropic_tools_to_openai(tools)

        data = self._request(payload)

        try:
            _ = data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError("unexpected OpenAI response format") from exc

        return data

    def extract_text(self, response: dict) -> str:
        """Extract text content from a response."""
        try:
            content = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            return ""
        return content or ""

    def extract_tool_calls(self, response: dict) -> list[dict]:
        """Extract function call blocks from a response."""
        try:
            tool_calls = response["choices"][0]["message"].get("tool_calls", [])
        except (KeyError, IndexError, TypeError):
            return []
        return tool_calls or []
