"""Base agent class with tool-use execution loop."""

from __future__ import annotations

import json
import logging
from typing import Any

from ..context import AgentRole, ProjectContext
from ..providers import generate_response
from ..tools.file_ops import list_directory, read_file, write_file
from ..tools.git_ops import git_commit, git_diff, git_status
from ..tools.shell import run_command

logger = logging.getLogger(__name__)

MAX_TOOL_TURNS = 50


class AgentError(RuntimeError):
    """An agent execution failed."""


class BaseAgent:
    """Base agent that handles the tool-use loop with an LLM provider.

    Each agent invocation is a fresh API call (context reset pattern).
    The agent loops until it gets a text response (end_turn) or hits
    the max tool turn limit.
    """

    def __init__(
        self,
        *,
        role: AgentRole,
        provider: str,
        model: str,
        system_prompt: str,
        tools: list[dict],
        project_root: str,
        context: ProjectContext | None = None,
        timeout_seconds: float = 120.0,
        max_tool_turns: int = MAX_TOOL_TURNS,
        allowed_shell_prefixes: list[str] | None = None,
        auto_commit: bool = False,
    ) -> None:
        self.role = role
        self.provider = provider
        self.model = model
        self.tools = tools
        self.project_root = project_root
        self.context = context
        self.timeout_seconds = timeout_seconds
        self.max_tool_turns = max_tool_turns
        self.allowed_shell_prefixes = allowed_shell_prefixes
        self.auto_commit = auto_commit

        # Build the full system prompt with context
        parts = [system_prompt]
        if context:
            parts.append(context.to_prompt_section())
        self.system_prompt = "\n\n---\n\n".join(parts)

    def run(self, user_prompt: str) -> str:
        """Execute the agent and return the final text response.

        Runs the tool-use loop: send message → if tool_use, execute
        tools and send results → repeat until text response.
        """
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": user_prompt},
        ]

        for turn in range(self.max_tool_turns):
            logger.info(
                "agent=%s turn=%d/%d calling %s/%s",
                self.role.value,
                turn + 1,
                self.max_tool_turns,
                self.provider,
                self.model,
            )

            response = generate_response(
                provider=self.provider,
                model=self.model,
                system_prompt=self.system_prompt,
                user_prompt="",  # Not used when messages provided
                max_tokens=8192,
                tools=self.tools if self.tools else None,
                messages=messages,
                timeout_seconds=self.timeout_seconds,
            )

            # Handle based on provider
            if self.provider == "anthropic":
                return self._handle_anthropic_loop(response, messages)
            else:
                return self._handle_openai_loop(response, messages)

        raise AgentError(
            f"agent {self.role.value} exceeded max tool turns ({self.max_tool_turns})"
        )

    def _handle_anthropic_loop(
        self, response: dict, messages: list[dict]
    ) -> str:
        """Handle the Anthropic tool-use loop until end_turn."""
        for turn in range(self.max_tool_turns):
            stop_reason = response.get("stop_reason", "end_turn")
            content = response.get("content", [])

            # Append assistant response to messages
            messages.append({"role": "assistant", "content": content})

            if stop_reason == "end_turn" or stop_reason != "tool_use":
                # Extract final text
                texts = []
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text = block.get("text", "")
                        if text:
                            texts.append(text)
                return "\n".join(texts)

            # Execute tool calls
            tool_results: list[dict] = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    tool_name = block.get("name", "")
                    tool_input = block.get("input", {})
                    tool_id = block.get("id", "")

                    logger.info(
                        "agent=%s executing tool=%s",
                        self.role.value,
                        tool_name,
                    )

                    result = self._execute_tool(tool_name, tool_input)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": json.dumps(result),
                        }
                    )

            messages.append({"role": "user", "content": tool_results})

            # Next API call
            response = generate_response(
                provider=self.provider,
                model=self.model,
                system_prompt=self.system_prompt,
                user_prompt="",
                max_tokens=8192,
                tools=self.tools if self.tools else None,
                messages=messages,
                timeout_seconds=self.timeout_seconds,
            )

        raise AgentError(
            f"agent {self.role.value} exceeded max tool turns ({self.max_tool_turns})"
        )

    def _handle_openai_loop(
        self, response: dict, messages: list[dict]
    ) -> str:
        """Handle the OpenAI function-calling loop."""
        for turn in range(self.max_tool_turns):
            try:
                message = response["choices"][0]["message"]
            except (KeyError, IndexError, TypeError) as exc:
                raise AgentError(f"unexpected OpenAI response: {exc}") from exc

            tool_calls = message.get("tool_calls")
            if not tool_calls:
                return message.get("content", "")

            # Append assistant message
            messages.append(message)

            # Execute each tool call
            for tc in tool_calls:
                func = tc.get("function", {})
                tool_name = func.get("name", "")
                try:
                    tool_input = json.loads(func.get("arguments", "{}"))
                except json.JSONDecodeError:
                    tool_input = {}

                logger.info(
                    "agent=%s executing tool=%s",
                    self.role.value,
                    tool_name,
                )

                result = self._execute_tool(tool_name, tool_input)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.get("id", ""),
                        "content": json.dumps(result),
                    }
                )

            # Next API call
            response = generate_response(
                provider=self.provider,
                model=self.model,
                system_prompt=self.system_prompt,
                user_prompt="",
                max_tokens=8192,
                tools=self.tools if self.tools else None,
                messages=messages,
                timeout_seconds=self.timeout_seconds,
            )

        raise AgentError(
            f"agent {self.role.value} exceeded max tool turns ({self.max_tool_turns})"
        )

    def _execute_tool(self, name: str, inputs: dict) -> dict[str, Any]:
        """Dispatch a tool call to the appropriate handler."""
        if name == "read_file":
            return read_file(
                path=inputs.get("path", ""),
                project_root=self.project_root,
                max_lines=inputs.get("max_lines", 2000),
            )
        elif name == "write_file":
            return write_file(
                path=inputs.get("path", ""),
                content=inputs.get("content", ""),
                project_root=self.project_root,
            )
        elif name == "list_directory":
            return list_directory(
                path=inputs.get("path", "."),
                project_root=self.project_root,
                pattern=inputs.get("pattern", "*"),
            )
        elif name == "run_command":
            return run_command(
                command=inputs.get("command", ""),
                cwd=self.project_root,
                timeout=inputs.get("timeout", 120),
                allowed_prefixes=self.allowed_shell_prefixes,
            )
        elif name == "git_diff":
            return git_diff(
                cwd=self.project_root,
                staged=inputs.get("staged", False),
            )
        elif name == "git_status":
            return git_status(cwd=self.project_root)
        elif name == "git_commit":
            if not self.auto_commit:
                return {"error": "auto-commit is disabled"}
            return git_commit(
                cwd=self.project_root,
                message=inputs.get("message", ""),
                files=inputs.get("files"),
            )
        else:
            return {"error": f"unknown tool: {name}"}
