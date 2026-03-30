"""Main orchestration loop: planner → generator ↔ evaluator."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .agents.evaluator import run_evaluator
from .agents.generator import run_generator
from .agents.planner import run_planner
from .config import HarnessConfig
from .handoff.reader import read_handoff
from .handoff.writer import (
    append_log,
    write_brief,
    write_handoff,
    write_iteration_handoff,
)

logger = logging.getLogger(__name__)


@dataclass
class HarnessResult:
    status: str  # "complete", "max_iterations_reached", "error"
    iterations: int = 0
    workspace: str = ""
    spec: dict = field(default_factory=dict)
    evaluation: dict = field(default_factory=dict)
    error: str = ""


class HarnessOrchestrator:
    """Orchestrates the planner → generator ↔ evaluator loop."""

    def __init__(
        self,
        *,
        config: HarnessConfig,
        project_path: str,
        root_path: str | None = None,
        workspace: Path | None = None,
        harness_root: Path | None = None,
    ) -> None:
        self.config = config
        self.project_path = str(Path(project_path).resolve())
        self.root_path = root_path
        self.harness_root = harness_root

        if workspace:
            self.workspace = workspace
        else:
            ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
            self.workspace = Path(project_path) / config.workspace_dir / f"run-{ts}"

    def run(self, brief: str) -> HarnessResult:
        """Execute the full planner → generator ↔ evaluator workflow."""
        self.workspace.mkdir(parents=True, exist_ok=True)
        write_brief(self.workspace, brief)
        self._log("harness started")

        # Phase 1: Planning
        self._log("phase=plan starting planner agent")
        try:
            spec = run_planner(
                brief=brief,
                config=self.config,
                project_path=self.project_path,
                root_path=self.root_path,
                harness_root=self.harness_root,
            )
        except Exception as exc:
            self._log(f"phase=plan error: {exc}")
            return HarnessResult(
                status="error",
                workspace=str(self.workspace),
                error=f"planner failed: {exc}",
            )

        write_handoff(self.workspace, "spec.json", spec)
        write_handoff(self.workspace, "sprint_contract.json", spec.get("contract", {}))
        self._log("phase=plan completed, spec written")

        # Phase 2: Generate ↔ Evaluate loop
        feedback: dict[str, Any] | None = None
        evaluation: dict[str, Any] = {}

        for iteration in range(1, self.config.max_iterations + 1):
            self._log(f"iteration={iteration}/{self.config.max_iterations} starting generator")

            # Generator (context reset: fresh call with spec + feedback)
            try:
                summary = run_generator(
                    spec=spec,
                    feedback=feedback,
                    config=self.config,
                    project_path=self.project_path,
                    root_path=self.root_path,
                    harness_root=self.harness_root,
                )
            except Exception as exc:
                self._log(f"iteration={iteration} generator error: {exc}")
                write_iteration_handoff(
                    self.workspace, iteration, "changes.json", {"error": str(exc)}
                )
                return HarnessResult(
                    status="error",
                    iterations=iteration,
                    workspace=str(self.workspace),
                    spec=spec,
                    error=f"generator failed at iteration {iteration}: {exc}",
                )

            write_iteration_handoff(
                self.workspace, iteration, "changes.json", {"summary": summary}
            )
            self._log(f"iteration={iteration} generator completed")

            # Evaluator (context reset: fresh call with spec + current code state)
            self._log(f"iteration={iteration} starting evaluator")
            try:
                evaluation = run_evaluator(
                    spec=spec,
                    config=self.config,
                    project_path=self.project_path,
                    root_path=self.root_path,
                    harness_root=self.harness_root,
                )
            except Exception as exc:
                self._log(f"iteration={iteration} evaluator error: {exc}")
                write_iteration_handoff(
                    self.workspace, iteration, "evaluation.json", {"error": str(exc)}
                )
                return HarnessResult(
                    status="error",
                    iterations=iteration,
                    workspace=str(self.workspace),
                    spec=spec,
                    error=f"evaluator failed at iteration {iteration}: {exc}",
                )

            write_iteration_handoff(
                self.workspace, iteration, "evaluation.json", evaluation
            )
            self._log(
                f"iteration={iteration} evaluator verdict={evaluation.get('verdict', 'unknown')}"
            )

            if evaluation.get("verdict") == "pass":
                write_handoff(self.workspace, "result.json", {
                    "status": "complete",
                    "iterations": iteration,
                    "verdict": "pass",
                })
                self._log(f"harness completed successfully after {iteration} iteration(s)")
                return HarnessResult(
                    status="complete",
                    iterations=iteration,
                    workspace=str(self.workspace),
                    spec=spec,
                    evaluation=evaluation,
                )

            # Prepare feedback for next generator iteration
            feedback = {
                "findings": evaluation.get("findings", []),
                "passing_criteria_unmet": evaluation.get("passing_criteria_unmet", []),
                "summary": evaluation.get("summary", ""),
            }
            write_iteration_handoff(
                self.workspace, iteration, "feedback.json", feedback
            )

        # Max iterations reached
        write_handoff(self.workspace, "result.json", {
            "status": "max_iterations_reached",
            "iterations": self.config.max_iterations,
            "verdict": "fail",
        })
        self._log(
            f"harness reached max iterations ({self.config.max_iterations})"
        )
        return HarnessResult(
            status="max_iterations_reached",
            iterations=self.config.max_iterations,
            workspace=str(self.workspace),
            spec=spec,
            evaluation=evaluation,
        )

    def run_plan_only(self, brief: str) -> HarnessResult:
        """Run only the Planner agent."""
        self.workspace.mkdir(parents=True, exist_ok=True)
        write_brief(self.workspace, brief)
        self._log("harness started (plan-only mode)")

        try:
            spec = run_planner(
                brief=brief,
                config=self.config,
                project_path=self.project_path,
                root_path=self.root_path,
                harness_root=self.harness_root,
            )
        except Exception as exc:
            self._log(f"planner error: {exc}")
            return HarnessResult(
                status="error",
                workspace=str(self.workspace),
                error=f"planner failed: {exc}",
            )

        write_handoff(self.workspace, "spec.json", spec)
        write_handoff(self.workspace, "sprint_contract.json", spec.get("contract", {}))
        self._log("plan-only completed, spec written")

        return HarnessResult(
            status="complete",
            workspace=str(self.workspace),
            spec=spec,
        )

    def run_generate_only(self) -> HarnessResult:
        """Run only the Generator against an existing spec in the workspace."""
        spec = read_handoff(self.workspace, "spec.json")
        if not spec:
            return HarnessResult(
                status="error",
                workspace=str(self.workspace),
                error="no spec.json found in workspace",
            )

        self._log("starting generator (generate-only mode)")
        feedback = read_handoff(self.workspace, "feedback.json")

        try:
            summary = run_generator(
                spec=spec,
                feedback=feedback,
                config=self.config,
                project_path=self.project_path,
                root_path=self.root_path,
                harness_root=self.harness_root,
            )
        except Exception as exc:
            self._log(f"generator error: {exc}")
            return HarnessResult(
                status="error",
                workspace=str(self.workspace),
                spec=spec,
                error=f"generator failed: {exc}",
            )

        write_handoff(self.workspace, "latest_changes.json", {"summary": summary})
        self._log("generate-only completed")

        return HarnessResult(
            status="complete",
            workspace=str(self.workspace),
            spec=spec,
        )

    def run_evaluate_only(self) -> HarnessResult:
        """Run only the Evaluator against existing changes in the workspace."""
        spec = read_handoff(self.workspace, "spec.json")
        if not spec:
            return HarnessResult(
                status="error",
                workspace=str(self.workspace),
                error="no spec.json found in workspace",
            )

        self._log("starting evaluator (evaluate-only mode)")

        try:
            evaluation = run_evaluator(
                spec=spec,
                config=self.config,
                project_path=self.project_path,
                root_path=self.root_path,
                harness_root=self.harness_root,
            )
        except Exception as exc:
            self._log(f"evaluator error: {exc}")
            return HarnessResult(
                status="error",
                workspace=str(self.workspace),
                spec=spec,
                error=f"evaluator failed: {exc}",
            )

        write_handoff(self.workspace, "latest_evaluation.json", evaluation)
        self._log(f"evaluate-only completed, verdict={evaluation.get('verdict', 'unknown')}")

        return HarnessResult(
            status="complete",
            workspace=str(self.workspace),
            spec=spec,
            evaluation=evaluation,
        )

    def _log(self, message: str) -> None:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        entry = f"[{ts}] {message}"
        logger.info(message)
        append_log(self.workspace, entry)
