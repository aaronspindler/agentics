"""Response schema parsing and validation."""

from __future__ import annotations

import json
from typing import Any

VALID_STATUSES = {"pass", "fail"}
VALID_SEVERITIES = {"low", "medium", "high"}


class SchemaError(ValueError):
    """Raised when model output does not match the expected contract."""


def _strip_code_fence(raw_text: str) -> str:
    text = raw_text.strip()
    if not text.startswith("```"):
        return text

    lines = text.splitlines()
    if len(lines) < 2:
        return text
    if lines[-1].strip() != "```":
        return text

    return "\n".join(lines[1:-1]).strip()


def parse_model_response(raw_text: str) -> dict[str, Any]:
    """Parse raw model text and validate the contract."""
    cleaned = _strip_code_fence(raw_text)

    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise SchemaError(f"model response is not valid JSON: {exc}") from exc

    if not isinstance(payload, dict):
        raise SchemaError("model response root must be a JSON object")

    status = payload.get("status")
    summary = payload.get("summary")
    findings = payload.get("findings")
    suggested_patch = payload.get("suggested_patch")

    if status not in VALID_STATUSES:
        raise SchemaError("field 'status' must be 'pass' or 'fail'")
    if not isinstance(summary, str) or not summary.strip():
        raise SchemaError("field 'summary' must be a non-empty string")
    if not isinstance(findings, list):
        raise SchemaError("field 'findings' must be a list")

    validated_findings: list[dict[str, Any]] = []
    for index, finding in enumerate(findings):
        if not isinstance(finding, dict):
            raise SchemaError(f"finding at index {index} must be an object")

        severity = finding.get("severity")
        title = finding.get("title")
        file_path = finding.get("file")
        line = finding.get("line")
        reason = finding.get("reason")
        recommendation = finding.get("recommendation")

        if severity not in VALID_SEVERITIES:
            raise SchemaError(f"finding {index}: invalid severity")
        if not isinstance(title, str) or not title.strip():
            raise SchemaError(f"finding {index}: 'title' must be a non-empty string")
        if file_path is not None and not isinstance(file_path, str):
            raise SchemaError(f"finding {index}: 'file' must be a string or null")
        if line is not None and (not isinstance(line, int) or line < 1):
            raise SchemaError(f"finding {index}: 'line' must be a positive integer or null")
        if not isinstance(reason, str) or not reason.strip():
            raise SchemaError(f"finding {index}: 'reason' must be a non-empty string")
        if not isinstance(recommendation, str) or not recommendation.strip():
            raise SchemaError(
                f"finding {index}: 'recommendation' must be a non-empty string"
            )

        validated_findings.append(
            {
                "severity": severity,
                "title": title,
                "file": file_path,
                "line": line,
                "reason": reason,
                "recommendation": recommendation,
            }
        )

    if status == "fail" and not validated_findings:
        raise SchemaError("status 'fail' requires at least one finding")

    if suggested_patch is not None and not isinstance(suggested_patch, str):
        raise SchemaError("field 'suggested_patch' must be a string or null")

    return {
        "status": status,
        "summary": summary.strip(),
        "findings": validated_findings,
        "suggested_patch": suggested_patch,
    }
