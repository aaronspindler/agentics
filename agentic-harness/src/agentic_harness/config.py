"""Configuration loading and validation."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# stdlib yaml-like parser (no PyYAML dependency)
# We use a simple key-value parser for the subset of YAML we need,
# falling back to defaults for anything missing.

DEFAULT_MAX_ITERATIONS = 5
DEFAULT_TIMEOUT_SECONDS = 120.0
DEFAULT_MODEL = "claude-sonnet-4-20250514"


class ConfigError(ValueError):
    """Invalid or missing configuration."""


@dataclass
class ModelsConfig:
    planner: str = DEFAULT_MODEL
    generator: str = DEFAULT_MODEL
    evaluator: str = DEFAULT_MODEL


@dataclass
class ProjectConfig:
    name: str = ""
    type: str = ""  # auto-detected if empty
    test_command: str = ""
    lint_command: str = ""


@dataclass
class SecurityConfig:
    protected_files: list[str] = field(default_factory=lambda: [".env", "*.pem", "*.key"])
    prohibited_patterns: list[str] = field(default_factory=list)


@dataclass
class HarnessConfig:
    provider: str = "anthropic"
    models: ModelsConfig = field(default_factory=ModelsConfig)
    project: ProjectConfig = field(default_factory=ProjectConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    max_iterations: int = DEFAULT_MAX_ITERATIONS
    auto_commit: bool = False
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    workspace_dir: str = ".harness"


def _try_parse_yaml(text: str) -> dict[str, Any]:
    """Minimal YAML-subset parser for flat and one-level-nested dicts.

    Only handles the simple config structure we need. For full YAML,
    users can install PyYAML and we detect it at import time.
    """
    try:
        import yaml  # type: ignore[import-untyped]

        return yaml.safe_load(text) or {}
    except ImportError:
        pass

    # Fallback: very simple line-by-line parser for flat YAML
    result: dict[str, Any] = {}
    current_section: dict[str, Any] | None = None
    current_key: str | None = None

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        indent = len(line) - len(line.lstrip())

        if indent == 0 and ":" in stripped:
            key, _, value = stripped.partition(":")
            key = key.strip()
            value = value.strip()
            if value:
                result[key] = _coerce_value(value)
                current_section = None
                current_key = None
            else:
                result[key] = {}
                current_section = result[key]
                current_key = key
        elif indent > 0 and current_section is not None and ":" in stripped:
            key, _, value = stripped.partition(":")
            key = key.strip()
            value = value.strip()
            if value.startswith("[") and value.endswith("]"):
                # Simple inline list: [a, b, c]
                items = [v.strip().strip('"').strip("'") for v in value[1:-1].split(",")]
                current_section[key] = [i for i in items if i]
            else:
                current_section[key] = _coerce_value(value)
        elif indent > 0 and stripped.startswith("- "):
            # List item under current section
            item = stripped[2:].strip().strip('"').strip("'")
            if current_key and isinstance(result.get(current_key), dict):
                # Find the last key added to current_section that is a list
                pass  # Skip complex list handling in fallback

    return result


def _coerce_value(value: str) -> Any:
    """Coerce a string value to Python type."""
    if value.lower() in ("true", "yes"):
        return True
    if value.lower() in ("false", "no"):
        return False
    if value.lower() in ("null", "none", "~"):
        return None
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    # Strip quotes
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    return value


def load_config(config_path: str | Path | None = None) -> HarnessConfig:
    """Load harness configuration from a YAML file.

    Falls back to defaults for any missing fields. Environment variables
    override file-based config.
    """
    raw: dict[str, Any] = {}

    if config_path:
        path = Path(config_path)
        if path.is_file():
            raw = _try_parse_yaml(path.read_text(encoding="utf-8"))

    config = HarnessConfig()

    # Provider
    config.provider = os.getenv(
        "AGENTIC_HARNESS_PROVIDER", raw.get("provider", config.provider)
    )

    # Models
    models_raw = raw.get("models", {})
    if isinstance(models_raw, dict):
        config.models = ModelsConfig(
            planner=models_raw.get("planner", DEFAULT_MODEL),
            generator=models_raw.get("generator", DEFAULT_MODEL),
            evaluator=models_raw.get("evaluator", DEFAULT_MODEL),
        )

    # Project
    project_raw = raw.get("project", {})
    if isinstance(project_raw, dict):
        config.project = ProjectConfig(
            name=project_raw.get("name", ""),
            type=project_raw.get("type", ""),
            test_command=project_raw.get("test_command", ""),
            lint_command=project_raw.get("lint_command", ""),
        )

    # Security
    security_raw = raw.get("security", {})
    if isinstance(security_raw, dict):
        config.security = SecurityConfig(
            protected_files=security_raw.get("protected_files", config.security.protected_files),
            prohibited_patterns=security_raw.get(
                "prohibited_patterns", config.security.prohibited_patterns
            ),
        )

    # Orchestration
    orchestration_raw = raw.get("orchestration", {})
    if isinstance(orchestration_raw, dict):
        config.max_iterations = orchestration_raw.get("max_iterations", DEFAULT_MAX_ITERATIONS)
        config.auto_commit = orchestration_raw.get("auto_commit", False)

    # Env overrides
    timeout_env = os.getenv("AGENTIC_HARNESS_TIMEOUT_SECONDS")
    if timeout_env:
        try:
            config.timeout_seconds = float(timeout_env)
        except ValueError:
            pass

    max_iter_env = os.getenv("AGENTIC_HARNESS_MAX_ITERATIONS")
    if max_iter_env:
        try:
            config.max_iterations = int(max_iter_env)
        except ValueError:
            pass

    workspace_env = os.getenv("AGENTIC_HARNESS_WORKSPACE")
    if workspace_env:
        config.workspace_dir = workspace_env

    return config
