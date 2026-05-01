"""Response schema contracts and validation for each agent role."""

from __future__ import annotations

import json
from typing import Any


class SchemaError(ValueError):
    """Raised when agent output does not match the expected contract."""


def _strip_code_fence(raw_text: str) -> str:
    text = raw_text.strip()
    if not text.startswith("```"):
        return text
    lines = text.splitlines()
    if len(lines) < 2 or lines[-1].strip() != "```":
        return text
    return "\n".join(lines[1:-1]).strip()


def _parse_json(raw_text: str) -> dict[str, Any]:
    cleaned = _strip_code_fence(raw_text)
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise SchemaError(f"agent response is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise SchemaError("agent response root must be a JSON object")
    return payload


def _require_str(payload: dict, field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise SchemaError(f"field '{field}' must be a non-empty string")
    return value.strip()


def _require_list(payload: dict, field: str) -> list:
    value = payload.get(field)
    if not isinstance(value, list):
        raise SchemaError(f"field '{field}' must be a list")
    return value


# --- Planner schema ---

SPEC_CONTRACT = {
    "title": "string",
    "description": "string",
    "target_project": "string",
    "files_to_modify": ["path1", "path2"],
    "files_to_create": ["path1"],
    "approach": "string",
    "contract": {
        "acceptance_criteria": ["..."],
        "test_requirements": ["..."],
        "security_checklist": ["..."],
        "style_requirements": ["..."],
        "out_of_scope": ["..."],
    },
}


def parse_planner_response(raw_text: str) -> dict[str, Any]:
    """Parse and validate the Planner agent's spec output."""
    payload = _parse_json(raw_text)

    title = _require_str(payload, "title")
    description = _require_str(payload, "description")
    approach = _require_str(payload, "approach")

    target_project = payload.get("target_project", "")
    files_to_modify = _require_list(payload, "files_to_modify")
    files_to_create = payload.get("files_to_create", [])
    if not isinstance(files_to_create, list):
        files_to_create = []

    contract = payload.get("contract")
    if not isinstance(contract, dict):
        raise SchemaError("field 'contract' must be an object")

    acceptance_criteria = contract.get("acceptance_criteria", [])
    if not isinstance(acceptance_criteria, list) or not acceptance_criteria:
        raise SchemaError("contract.acceptance_criteria must be a non-empty list")

    test_requirements = contract.get("test_requirements", [])
    if not isinstance(test_requirements, list):
        test_requirements = []

    return {
        "title": title,
        "description": description,
        "target_project": target_project,
        "files_to_modify": files_to_modify,
        "files_to_create": files_to_create,
        "approach": approach,
        "contract": {
            "acceptance_criteria": acceptance_criteria,
            "test_requirements": test_requirements,
            "security_checklist": contract.get("security_checklist", []),
            "style_requirements": contract.get("style_requirements", []),
            "out_of_scope": contract.get("out_of_scope", []),
        },
    }


# --- Evaluator schema ---

VALID_VERDICTS = {"pass", "fail"}
VALID_SEVERITIES = {"low", "medium", "high"}

EVALUATION_CONTRACT = {
    "verdict": "pass|fail",
    "summary": "string",
    "score": {
        "correctness": "int 1-10",
        "completeness": "int 1-10",
        "style_compliance": "int 1-10",
        "test_coverage": "int 1-10",
        "security": "int 1-10",
    },
    "findings": [
        {
            "severity": "low|medium|high",
            "category": "string",
            "title": "string",
            "file": "path or null",
            "reason": "string",
            "recommendation": "string",
        }
    ],
    "passing_criteria_met": ["..."],
    "passing_criteria_unmet": ["..."],
}


def parse_evaluator_response(raw_text: str) -> dict[str, Any]:
    """Parse and validate the Evaluator agent's grading output."""
    payload = _parse_json(raw_text)

    verdict = payload.get("verdict")
    if verdict not in VALID_VERDICTS:
        raise SchemaError("field 'verdict' must be 'pass' or 'fail'")

    summary = _require_str(payload, "summary")

    score = payload.get("score", {})
    if not isinstance(score, dict):
        score = {}

    findings = _require_list(payload, "findings")
    validated_findings: list[dict[str, Any]] = []
    for idx, finding in enumerate(findings):
        if not isinstance(finding, dict):
            raise SchemaError(f"finding at index {idx} must be an object")

        severity = finding.get("severity")
        if severity not in VALID_SEVERITIES:
            raise SchemaError(f"finding {idx}: invalid severity '{severity}'")

        title = finding.get("title")
        if not isinstance(title, str) or not title.strip():
            raise SchemaError(f"finding {idx}: 'title' must be a non-empty string")

        validated_findings.append(
            {
                "severity": severity,
                "category": finding.get("category", "general"),
                "title": title.strip(),
                "file": finding.get("file"),
                "reason": finding.get("reason", ""),
                "recommendation": finding.get("recommendation", ""),
            }
        )

    if verdict == "fail" and not validated_findings:
        raise SchemaError("verdict 'fail' requires at least one finding")

    return {
        "verdict": verdict,
        "summary": summary,
        "score": score,
        "findings": validated_findings,
        "passing_criteria_met": payload.get("passing_criteria_met", []),
        "passing_criteria_unmet": payload.get("passing_criteria_unmet", []),
    }
