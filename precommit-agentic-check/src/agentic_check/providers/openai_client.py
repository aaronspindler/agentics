"""OpenAI provider client."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from .errors import ProviderError


class OpenAIClient:
    """Simple OpenAI Chat Completions client using stdlib HTTP."""

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

    def generate(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
    ) -> str:
        payload = {
            "model": model,
            "temperature": 0,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

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
            data = json.loads(body.decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise ProviderError("unexpected OpenAI response format") from exc

        if isinstance(content, str):
            return content
        if isinstance(content, list):
            chunks = [
                item.get("text", "")
                for item in content
                if isinstance(item, dict) and item.get("type") == "text"
            ]
            text = "\n".join(part for part in chunks if part)
            if text:
                return text

        raise ProviderError("OpenAI response did not include text content")
