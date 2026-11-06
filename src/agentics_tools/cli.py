"""Agentics catalog, installation, and helper command line."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import __version__
from .catalog import Catalog, default_catalog
from . import installer


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="agentics", description=__doc__)
    result.add_argument("--version", action="version", version=__version__)
    result.add_argument("--catalog", type=Path, help="Use an explicit catalog directory")
    commands = result.add_subparsers(dest="command", required=True)
    for command in ("list", "install", "update", "status", "uninstall"):
        sub = commands.add_parser(command)
        sub.add_argument("--skill", action="append", default=[])
        sub.add_argument("--agent", action="append", default=[])
        sub.add_argument("--group", action="append", default=[])
        sub.add_argument("--all", action="store_true")
        sub.add_argument("--json", action="store_true", dest="as_json")
        if command != "list":
            sub.add_argument("--home", type=Path, default=Path.home(), help="User home (for isolated installation/testing)")
            sub.add_argument("--codex-home", type=Path, default=Path(os.environ["CODEX_HOME"]) if os.environ.get("CODEX_HOME") else None)
        if command in {"install", "update", "uninstall"}:
            sub.add_argument("--dry-run", action="store_true")
    commands.add_parser("validate", help="Validate catalog metadata, resources, and local links")
    workflows = commands.add_parser("workflows")
    workflows.add_argument("action", choices=("list", "show"))
    workflows.add_argument("name", nargs="?")
    tools = commands.add_parser("tools", help="Portable GitHub and preview tools")
    tools.add_argument("--repo-root", type=Path)
    tools.add_argument("tool", choices=("pr-threads", "preview", "preview-sync"))
    tools.add_argument("arguments", nargs=argparse.REMAINDER)
    return result


def _tools(args) -> int:
    from .tools import context, pr_threads, preview, preview_sync
    arguments = list(args.arguments)
    # Also accept the target after the namespace, before helper arguments.
    for index, value in enumerate(arguments):
        if value == "--repo-root":
            if args.repo_root is not None or index + 1 == len(arguments):
                raise ValueError("Pass --repo-root once with a directory")
            args.repo_root = Path(arguments[index + 1])
            del arguments[index:index + 2]
            break
        if value.startswith("--repo-root="):
            if args.repo_root is not None:
                raise ValueError("Pass --repo-root once")
            args.repo_root = Path(value.split("=", 1)[1])
            del arguments[index]
            break
    context.set_repo_root(args.repo_root)
    module = {"pr-threads": pr_threads, "preview": preview, "preview-sync": preview_sync}[args.tool]
    previous = sys.argv
    try:
        sys.argv = [f"agentics tools {args.tool}", *arguments]
        return module.main() or 0
    finally:
        sys.argv = previous
        context.set_repo_root(None)


def main(argv=None) -> int:
    command_parser = parser()
    args = command_parser.parse_args(argv)
    try:
        if args.command == "tools":
            return _tools(args)
        catalog = Catalog(args.catalog) if args.catalog else default_catalog()
        if args.command == "validate":
            from .validation import validate
            validate(catalog)
            print(f"Valid catalog {catalog.version}: {len(catalog.items)} items")
            return 0
        if args.command == "workflows":
            workflows = catalog.root / "workflows"
            if args.action == "list":
                for path in sorted(workflows.glob("*.md")):
                    print(path.stem)
            else:
                if args.name is None or not args.name.replace("-", "").isalnum():
                    raise ValueError("Pass a workflow ID from 'agentics workflows list'")
                path = workflows / f"{args.name}.md"
                if not path.is_file():
                    raise ValueError(f"Unknown workflow: {args.name}")
                print(path.read_text(), end="")
            return 0
        selection = bool(args.skill or args.agent or args.group or args.all)
        ids = catalog.select(skills=args.skill, agents=args.agent, groups=args.group, all_items=args.all)
        if args.command == "list":
            rows = [dict(id=key, kind=item["kind"], group=item["group"], dependencies=item.get("dependencies", [])) for key, item in catalog.items.items() if not selection or key in ids]
        else:
            layout = installer.Layout(args.home, args.codex_home)
            if args.command == "status":
                rows = installer.status(catalog, layout, ids if selection else None)
            else:
                if args.command == "install" and not selection:
                    command_parser.error("install requires --skill, --agent, --group, or --all")
                if args.command in {"update", "uninstall"}:
                    installed = set(installer.installed_ids(layout))
                    if args.all or not selection:
                        ids = sorted(installed)
                    elif args.command == "uninstall":
                        # Removing a skill does not implicitly remove its dependency roles.
                        ids = sorted({f"skill:{s}" for s in args.skill} | {f"agent:{a}" for a in args.agent} | {key for key, item in catalog.items.items() if item["group"] in args.group})
                rows = getattr(installer, args.command)(catalog, layout, ids, args.dry_run)
        if args.as_json:
            print(json.dumps(rows, indent=2))
        else:
            for row in rows:
                print(f"{row['id']}: {row.get('action', row.get('status', row.get('group')))}" + (f" [{row['status']}]" if 'action' in row else ""))
        return 0
    except (ValueError, OSError, RuntimeError) as exc:
        print(f"agentics: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
