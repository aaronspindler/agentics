"""CLI entrypoint for the agentic harness."""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
from pathlib import Path

from .config import DEFAULT_MAX_ITERATIONS, DEFAULT_MODEL, HarnessConfig, load_config
from .handoff.reader import get_latest_iteration, read_handoff
from .orchestrator import HarnessOrchestrator, HarnessResult


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="agentic-harness",
        description="Multi-agent orchestration harness for long-running development tasks.",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # --- run ---
    run_parser = subparsers.add_parser(
        "run", help="Full planner → generator → evaluator workflow"
    )
    _add_common_args(run_parser)
    _add_brief_args(run_parser)
    run_parser.add_argument(
        "--max-iterations",
        type=int,
        default=DEFAULT_MAX_ITERATIONS,
        help=f"Max generator↔evaluator iterations (default: {DEFAULT_MAX_ITERATIONS})",
    )
    run_parser.add_argument(
        "--no-evaluate",
        action="store_true",
        help="Skip evaluation phase (plan + generate only)",
    )
    run_parser.add_argument(
        "--auto-commit",
        action="store_true",
        help="Auto-commit passing changes",
    )

    # --- plan ---
    plan_parser = subparsers.add_parser("plan", help="Run only the Planner agent")
    _add_common_args(plan_parser)
    _add_brief_args(plan_parser)

    # --- generate ---
    gen_parser = subparsers.add_parser(
        "generate", help="Run only the Generator against an existing spec"
    )
    _add_common_args(gen_parser)
    gen_parser.add_argument(
        "--workspace", required=True, help="Path to existing workspace directory"
    )

    # --- evaluate ---
    eval_parser = subparsers.add_parser(
        "evaluate", help="Run only the Evaluator against existing changes"
    )
    _add_common_args(eval_parser)
    eval_parser.add_argument(
        "--workspace", required=True, help="Path to existing workspace directory"
    )

    # --- status ---
    status_parser = subparsers.add_parser(
        "status", help="Show current harness state from the workspace"
    )
    status_parser.add_argument(
        "--workspace", required=True, help="Path to workspace directory"
    )

    # --- reset ---
    reset_parser = subparsers.add_parser(
        "reset", help="Clear workspace and start fresh"
    )
    reset_parser.add_argument(
        "--workspace", required=True, help="Path to workspace directory"
    )

    return parser.parse_args(argv)


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--provider",
        choices=["anthropic", "openai"],
        default="anthropic",
        help="LLM provider (default: anthropic)",
    )
    parser.add_argument(
        "--model", default=DEFAULT_MODEL, help=f"Model to use (default: {DEFAULT_MODEL})"
    )
    parser.add_argument(
        "--project",
        default=".",
        help="Target project directory (default: current directory)",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Harness config file (default: .harness.yaml in project dir)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without calling APIs",
    )


def _add_brief_args(parser: argparse.ArgumentParser) -> None:
    brief_group = parser.add_mutually_exclusive_group(required=True)
    brief_group.add_argument("--brief", help="Path to task brief (markdown file)")
    brief_group.add_argument("--brief-text", help="Inline task brief text")


def _load_brief(args: argparse.Namespace) -> str:
    if args.brief:
        path = Path(args.brief)
        if not path.is_file():
            print(f"error: brief file not found: {args.brief}", file=sys.stderr)
            sys.exit(1)
        return path.read_text(encoding="utf-8")
    return args.brief_text


def _build_config(args: argparse.Namespace) -> HarnessConfig:
    config_path = getattr(args, "config", None)
    if not config_path:
        project = Path(getattr(args, "project", ".")).resolve()
        candidate = project / ".harness.yaml"
        if candidate.is_file():
            config_path = str(candidate)

    config = load_config(config_path)

    # CLI overrides
    if hasattr(args, "provider") and args.provider:
        config.provider = args.provider
    if hasattr(args, "model") and args.model != DEFAULT_MODEL:
        config.models.planner = args.model
        config.models.generator = args.model
        config.models.evaluator = args.model
    if hasattr(args, "max_iterations"):
        config.max_iterations = args.max_iterations
    if hasattr(args, "auto_commit") and args.auto_commit:
        config.auto_commit = True

    return config


def _print_result(result: HarnessResult) -> None:
    print(f"\n{'=' * 60}")
    print(f"Harness result: {result.status}")
    if result.iterations:
        print(f"Iterations: {result.iterations}")
    print(f"Workspace: {result.workspace}")
    if result.error:
        print(f"Error: {result.error}")
    if result.evaluation:
        verdict = result.evaluation.get("verdict", "unknown")
        summary = result.evaluation.get("summary", "")
        print(f"Verdict: {verdict}")
        if summary:
            print(f"Summary: {summary}")
    print(f"{'=' * 60}")


def cmd_run(args: argparse.Namespace) -> int:
    brief = _load_brief(args)
    config = _build_config(args)
    project_path = str(Path(args.project).resolve())

    if args.dry_run:
        print("DRY RUN — would execute:")
        print(f"  Provider: {config.provider}")
        print(f"  Models: planner={config.models.planner}, generator={config.models.generator}, evaluator={config.models.evaluator}")
        print(f"  Project: {project_path}")
        print(f"  Max iterations: {config.max_iterations}")
        print(f"  Brief: {brief[:200]}...")
        return 0

    orchestrator = HarnessOrchestrator(
        config=config,
        project_path=project_path,
    )

    result = orchestrator.run(brief)
    _print_result(result)
    return 0 if result.status == "complete" else 1


def cmd_plan(args: argparse.Namespace) -> int:
    brief = _load_brief(args)
    config = _build_config(args)
    project_path = str(Path(args.project).resolve())

    if args.dry_run:
        print("DRY RUN — would run Planner agent")
        print(f"  Provider: {config.provider}")
        print(f"  Model: {config.models.planner}")
        print(f"  Project: {project_path}")
        return 0

    orchestrator = HarnessOrchestrator(
        config=config,
        project_path=project_path,
    )

    result = orchestrator.run_plan_only(brief)
    _print_result(result)

    if result.spec:
        print("\nSpec written to:", Path(result.workspace) / "spec.json")
        print(json.dumps(result.spec, indent=2))

    return 0 if result.status == "complete" else 1


def cmd_generate(args: argparse.Namespace) -> int:
    config = _build_config(args)
    project_path = str(Path(args.project).resolve())
    workspace = Path(args.workspace)

    if not workspace.is_dir():
        print(f"error: workspace not found: {workspace}", file=sys.stderr)
        return 1

    orchestrator = HarnessOrchestrator(
        config=config,
        project_path=project_path,
        workspace=workspace,
    )

    result = orchestrator.run_generate_only()
    _print_result(result)
    return 0 if result.status == "complete" else 1


def cmd_evaluate(args: argparse.Namespace) -> int:
    config = _build_config(args)
    project_path = str(Path(args.project).resolve())
    workspace = Path(args.workspace)

    if not workspace.is_dir():
        print(f"error: workspace not found: {workspace}", file=sys.stderr)
        return 1

    orchestrator = HarnessOrchestrator(
        config=config,
        project_path=project_path,
        workspace=workspace,
    )

    result = orchestrator.run_evaluate_only()
    _print_result(result)
    return 0 if result.status == "complete" else 1


def cmd_status(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace)
    if not workspace.is_dir():
        print(f"error: workspace not found: {workspace}", file=sys.stderr)
        return 1

    result_data = read_handoff(workspace, "result.json")
    spec = read_handoff(workspace, "spec.json")
    latest_iter = get_latest_iteration(workspace)

    print(f"Workspace: {workspace}")
    print(f"Iterations completed: {latest_iter}")

    if spec:
        print(f"Spec: {spec.get('title', 'untitled')}")

    if result_data:
        print(f"Status: {result_data.get('status', 'unknown')}")
        print(f"Verdict: {result_data.get('verdict', 'unknown')}")
    else:
        print("Status: in_progress (no result.json yet)")

    # Show latest evaluation if available
    if latest_iter > 0:
        from .handoff.reader import read_iteration_handoff

        eval_data = read_iteration_handoff(workspace, latest_iter, "evaluation.json")
        if eval_data:
            print(f"\nLatest evaluation (iteration {latest_iter}):")
            print(f"  Verdict: {eval_data.get('verdict', 'unknown')}")
            print(f"  Summary: {eval_data.get('summary', '')}")
            findings = eval_data.get("findings", [])
            if findings:
                print(f"  Findings: {len(findings)}")
                for f in findings:
                    print(f"    [{f.get('severity')}] {f.get('title')}")

    return 0


def cmd_reset(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace)
    if not workspace.is_dir():
        print(f"error: workspace not found: {workspace}", file=sys.stderr)
        return 1

    shutil.rmtree(workspace)
    print(f"Workspace cleared: {workspace}")
    return 0


COMMANDS = {
    "run": cmd_run,
    "plan": cmd_plan,
    "generate": cmd_generate,
    "evaluate": cmd_evaluate,
    "status": cmd_status,
    "reset": cmd_reset,
}


def run(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.verbose:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(name)s %(levelname)s %(message)s",
        )

    if not args.command:
        parse_args(["--help"])
        return 1

    handler = COMMANDS.get(args.command)
    if not handler:
        print(f"error: unknown command '{args.command}'", file=sys.stderr)
        return 1

    return handler(args)


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
