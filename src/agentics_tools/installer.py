"""Conservative managed-copy installation; never adopts or overwrites unknown files."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import tempfile
import tomllib
from dataclasses import dataclass
from pathlib import Path

from .catalog import Catalog, relative_path


@dataclass
class Layout:
    home: Path
    codex_home: Path | None = None

    def __post_init__(self):
        self.home = Path(self.home).expanduser().resolve()
        self.codex_home = Path(self.codex_home or self.home / ".codex").expanduser().resolve()

    @property
    def skill_root(self) -> Path:
        return self.home / ".agents" / "skills"

    @property
    def agent_root(self) -> Path:
        return self.codex_home / "agents"

    @property
    def state_path(self) -> Path:
        return self.codex_home / "agentics" / "installed.json"


def _check_ancestors(path: Path, root: Path):
    if not path.is_relative_to(root):
        raise ValueError(f"Destination escapes installation root: {path}")
    for parent in reversed((path, *path.parents)):
        if parent == root or parent.is_relative_to(root):
            if parent.is_symlink():
                raise ValueError(f"Symlink in installation path: {parent}")
            if parent != path and parent.exists() and not parent.is_dir():
                raise ValueError(f"Not a directory: {parent}")


def _destination(layout: Layout, record: dict) -> Path:
    if record["kind"] == "skill":
        path = layout.skill_root / record["name"]
        _check_ancestors(path, layout.home)
    else:
        filename = record.get("filename", Path(record.get("path", "")).name)
        if not filename or len(relative_path(filename).parts) != 1 or not filename.endswith(".toml"):
            raise ValueError("Unsafe agent filename in installation state")
        path = layout.agent_root / filename
        _check_ancestors(path, layout.codex_home)
    return path


def _file_info(data: bytes, mode: int) -> dict:
    return {"type": "file", "sha256": hashlib.sha256(data).hexdigest(), "mode": mode}


def _bundle_snapshot(bundle: dict) -> dict:
    result = {}
    for relative, (contents, mode) in bundle.items():
        result[relative] = _file_info(contents, mode)
        for parent in Path(relative).parents:
            if parent != Path("."):
                result[parent.as_posix()] = {"type": "directory"}
    return result


def _bundle(catalog: Catalog, key: str, record=None) -> dict:
    bundle = catalog.bundle(key)
    if catalog.items[key]["kind"] == "agent" and record:
        # Source filename changes do not orphan an already installed role.
        bundle = {record["filename"]: next(iter(bundle.values()))}
    return bundle


def _snapshot(path: Path, kind: str) -> dict:
    if path.is_symlink():
        raise ValueError(f"Symlink at managed destination: {path}")
    if not path.exists():
        return {}
    if kind == "agent":
        if not path.is_file():
            raise ValueError(f"Expected managed file: {path}")
        return {path.name: _file_info(path.read_bytes(), stat.S_IMODE(path.stat().st_mode))}
    if not path.is_dir():
        raise ValueError(f"Expected managed directory: {path}")
    result = {}
    for child in sorted(path.rglob("*")):
        if child.is_symlink():
            raise ValueError(f"Symlink in managed bundle: {child}")
        relative = child.relative_to(path).as_posix()
        if child.is_dir():
            result[relative] = {"type": "directory"}
        elif child.is_file():
            result[relative] = _file_info(child.read_bytes(), stat.S_IMODE(child.stat().st_mode))
        else:
            raise ValueError(f"Unsupported file in managed bundle: {child}")
    return result


def _read_state(layout: Layout) -> dict:
    _check_ancestors(layout.state_path, layout.codex_home)
    if not layout.state_path.exists():
        return {"schema_version": 1, "items": {}}
    state = json.loads(layout.state_path.read_text())
    if state.get("schema_version") != 1 or not isinstance(state.get("items"), dict):
        raise ValueError("Invalid Agentics installation state")
    for key, record in state["items"].items():
        kind, name = record.get("kind"), record.get("name", "")
        if kind not in {"skill", "agent"} or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", name) or key != f"{kind}:{name}":
            raise ValueError(f"Invalid managed item: {key}")
        _destination(layout, record)
        if not isinstance(record.get("files"), dict) or not record["files"]:
            raise ValueError(f"Invalid managed snapshot: {key}")
        for relative, info in record["files"].items():
            relative_path(relative)
            if info.get("type") not in {"file", "directory"}:
                raise ValueError(f"Invalid managed file: {key}/{relative}")
    return state


def installed_ids(layout: Layout) -> list[str]:
    """Return owned identities even if their files are modified or collide."""
    return sorted(_read_state(layout)["items"])


def _role_collisions(layout: Layout, item: dict, destination: Path) -> list[str]:
    collisions = []
    _check_ancestors(layout.agent_root, layout.codex_home)
    if layout.agent_root.exists():
        for role in layout.agent_root.glob("*.toml"):
            if role == destination:
                continue
            if role.is_symlink():
                raise ValueError(f"Symlink in agent directory: {role}")
            try:
                role_data = tomllib.loads(role.read_text())
            except (OSError, ValueError) as exc:
                raise ValueError(f"Cannot inspect agent definition: {role}: {exc}") from exc
            if role_data.get("name") == item["name"]:
                collisions.append(str(role))
    config = layout.codex_home / "config.toml"
    _check_ancestors(config, layout.codex_home)
    if config.exists():
        config_data = tomllib.loads(config.read_text())
        if isinstance(config_data.get("agents", {}).get(item["name"]), dict):
            collisions.append(f"{config} [agents.{item['name']}]")
        for role_name, registration in config_data.get("agents", {}).items():
            if not isinstance(registration, dict) or not registration.get("config_file"):
                continue
            role_path = Path(registration["config_file"]).expanduser()
            if not role_path.is_absolute():
                role_path = config.parent / role_path
            if role_path.is_file():
                role_data = tomllib.loads(role_path.read_text())
                if role_data.get("name") == item["name"]:
                    collisions.append(f"{config} [agents.{role_name}]")
    return collisions


def _skill_collisions(layout: Layout, item: dict, destination: Path) -> list[str]:
    collisions = []
    _check_ancestors(layout.skill_root, layout.home)
    if layout.skill_root.exists():
        for folder in layout.skill_root.iterdir():
            if folder == destination:
                continue
            manifest = folder / "SKILL.md"
            if manifest.is_file():
                match = re.search(r"^name:\s*['\"]?([^\n'\"]+)['\"]?\s*$", manifest.read_text(), re.M)
                if match and match.group(1).strip() == item["name"]:
                    collisions.append(str(folder))
    return collisions


def status(catalog: Catalog, layout: Layout, ids=None) -> list[dict]:
    state = _read_state(layout)
    selected = sorted(set(ids if ids is not None else set(catalog.items) | set(state["items"])))
    rows = []
    for key in selected:
        item = catalog.items.get(key)
        record = state["items"].get(key)
        if item is None and record is None:
            raise ValueError(f"Unknown item: {key}")
        destination = _destination(layout, record or item)
        row = {"id": key, "path": str(destination)}
        try:
            actual = _snapshot(destination, (record or item)["kind"])
        except ValueError:
            actual = None
        collisions = []
        if item:
            checker = _role_collisions if item["kind"] == "agent" else _skill_collisions
            collisions = checker(layout, item, destination)
        if collisions:
            row.update(status="collision", conflicts=collisions)
        elif record is None:
            row["status"] = "collision" if destination.exists() or destination.is_symlink() else "not-installed"
        elif not destination.exists() and not destination.is_symlink():
            row["status"] = "missing"
        elif actual != record["files"]:
            row["status"] = "modified"
        elif item is None:
            row["status"] = "source-unavailable"
        elif (actual == _bundle_snapshot(_bundle(catalog, key, record))
              and sorted(record.get("dependencies", [])) == sorted(item.get("dependencies", []))
              and record.get("version") == catalog.version):
            row["status"] = "current"
        else:
            row["status"] = "update-available"
        rows.append(row)
    return rows


def _record(catalog: Catalog, key: str, bundle: dict) -> dict:
    item = catalog.items[key]
    return {
        "kind": item["kind"], "name": item["name"],
        "filename": next(iter(bundle)) if item["kind"] == "agent" else None,
        "version": catalog.version, "files": _bundle_snapshot(bundle),
        "dependencies": item.get("dependencies", []),
    }


def _plan(operation: str, catalog: Catalog, layout: Layout, ids: list[str]):
    state = _read_state(layout)
    rows = status(catalog, layout, ids)
    errors, changes = [], []
    for row in rows:
        key, current = row["id"], row["status"]
        if current in {"collision", "modified", "missing"}:
            errors.append(f"{key}: {current} ({row['path']})")
        elif operation == "install":
            if current == "not-installed":
                changes.append((key, "install"))
            elif current != "current":
                errors.append(f"{key}: already installed; use update")
        elif operation == "update":
            if current == "not-installed":
                errors.append(f"{key}: not installed; use install")
            elif current == "source-unavailable":
                errors.append(f"{key}: source unavailable")
            elif current == "update-available":
                changes.append((key, "update"))
        elif operation == "uninstall" and current != "not-installed":
            changes.append((key, "uninstall"))
    if operation == "uninstall":
        removed = {key for key, _ in changes}
        for key, record in state["items"].items():
            if key not in removed and removed.intersection(record.get("dependencies", [])):
                errors.append(f"{key}: depends on an item selected for uninstall")
    else:
        available = set(state["items"]) | {key for key, action in changes if action == "install"}
        for key in ids:
            if key not in catalog.items:
                continue
            for dependency in catalog.items[key].get("dependencies", []):
                if dependency not in available:
                    errors.append(f"{key}: install required dependency {dependency} first")
    if errors:
        raise ValueError("Operation refused before writing:\n" + "\n".join(errors))
    return state, rows, changes


def _remove(path: Path):
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink(missing_ok=True)


def _operate(operation: str, catalog: Catalog, layout: Layout, ids, dry_run: bool):
    ids = list(ids)
    state, rows, changes = _plan(operation, catalog, layout, ids)
    for row in rows:
        row["action"] = next((action for key, action in changes if key == row["id"]), "unchanged")
        row["dry_run"] = dry_run
    if dry_run or not changes:
        return rows
    layout.state_path.parent.mkdir(parents=True, exist_ok=True)
    lock = layout.state_path.with_suffix(".lock")
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise ValueError(f"Installation lock exists: {lock}; inspect any interrupted operation before retrying") from exc
    staged = []
    completed = []
    preserve_recovery = False
    try:
        os.write(descriptor, str(os.getpid()).encode())
        os.close(descriptor)
        state, _, changes = _plan(operation, catalog, layout, ids)
        # Stage every bundle before replacing any destination.
        for key, action in changes:
            item = catalog.items.get(key) or state["items"][key]
            destination = _destination(layout, state["items"].get(key) or item)
            destination.parent.mkdir(parents=True, exist_ok=True)
            staging = Path(tempfile.mkdtemp(prefix=".agentics-", dir=destination.parent))
            payload = staging / "payload"
            bundle = None if action == "uninstall" else _bundle(catalog, key, state["items"].get(key))
            if bundle:
                if item["kind"] == "agent":
                    contents, mode = next(iter(bundle.values()))
                    payload.write_bytes(contents)
                    payload.chmod(mode)
                else:
                    payload.mkdir()
                    for relative, (contents, mode) in bundle.items():
                        output = payload / relative
                        output.parent.mkdir(parents=True, exist_ok=True)
                        output.write_bytes(contents)
                        output.chmod(mode)
            staged.append((key, action, destination, staging, payload, bundle))
        for key, action, destination, staging, payload, bundle in staged:
            backup = staging / "backup"
            existed = destination.exists()
            if existed:
                destination.rename(backup)
            completed.append((destination, backup, existed))
            if action == "uninstall":
                del state["items"][key]
            else:
                payload.rename(destination)
                state["items"][key] = _record(catalog, key, bundle)
        state["catalog_version"] = catalog.version
        state_fd, state_name = tempfile.mkstemp(prefix=".installed-", dir=layout.state_path.parent)
        state_temp = Path(state_name)
        try:
            with os.fdopen(state_fd, "w") as stream:
                stream.write(json.dumps(state, indent=2, sort_keys=True) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            state_temp.replace(layout.state_path)
        finally:
            state_temp.unlink(missing_ok=True)
    except BaseException as operation_error:
        recovery_errors = []
        for destination, backup, existed in reversed(completed):
            try:
                _remove(destination)
                if existed:
                    backup.rename(destination)
            except BaseException as recovery_error:
                recovery_errors.append(f"{destination}: {recovery_error}")
        if recovery_errors:
            preserve_recovery = True
            recovery_paths = ", ".join(str(staging) for _, _, _, staging, _, _ in staged)
            raise RuntimeError(
                f"Operation failed and rollback incomplete. Installation lock retained at {lock}. "
                f"Recovery data retained in: {recovery_paths}\n" + "\n".join(recovery_errors)
            ) from operation_error
        raise
    finally:
        if not preserve_recovery:
            for _, _, _, staging, _, _ in staged:
                shutil.rmtree(staging, ignore_errors=True)
            lock.unlink(missing_ok=True)
    return rows


def install(catalog: Catalog, layout: Layout, ids, dry_run=False):
    return _operate("install", catalog, layout, ids, dry_run)


def update(catalog: Catalog, layout: Layout, ids, dry_run=False):
    return _operate("update", catalog, layout, ids, dry_run)


def uninstall(catalog: Catalog, layout: Layout, ids, dry_run=False):
    return _operate("uninstall", catalog, layout, ids, dry_run)
