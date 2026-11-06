"""Load the canonical catalog and assemble self-contained installation bundles."""

from __future__ import annotations

import json
import re
import stat
import tomllib
from pathlib import Path, PurePosixPath

GROUPS = {"core", "github", "docs", "ops", "maintenance"}


def relative_path(value: str) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValueError(f"Unsafe relative path: {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in value.split("/")):
        raise ValueError(f"Unsafe relative path: {value!r}")
    return path


def checked_path(root: Path, relative: str) -> Path:
    path = root
    for part in relative_path(relative).parts:
        path = path / part
        if path.is_symlink():
            raise ValueError(f"Symlink in catalog: {path}")
    if not path.exists():
        raise ValueError(f"Missing catalog resource: {path}")
    return path


class Catalog:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        raw = json.loads(checked_path(self.root, "catalog.json").read_text())
        if raw.get("schema_version") != 1 or not isinstance(raw.get("version"), str):
            raise ValueError("Unsupported catalog schema or missing version")
        self.version = raw["version"]
        self.items: dict[str, dict] = {}
        seen_names: set[tuple[str, str]] = set()
        destinations: set[tuple[str, str]] = set()
        for item in raw.get("items", []):
            kind, name = item.get("kind"), item.get("name", "")
            if kind not in {"skill", "agent"} or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", name):
                raise ValueError(f"Invalid catalog item: {item!r}")
            if kind == "skill" and "_" in name:
                raise ValueError(f"Invalid skill name: {name}")
            identifier = item.get("id")
            if identifier != f"{kind}:{name}" or identifier in self.items or (kind, name) in seen_names:
                raise ValueError(f"Duplicate or invalid catalog ID: {identifier}")
            if item.get("group") not in GROUPS:
                raise ValueError(f"Invalid group for {identifier}")
            source = checked_path(self.root, item["path"])
            if (kind == "skill" and not source.is_dir()) or (kind == "agent" and not source.is_file()):
                raise ValueError(f"Invalid source type for {identifier}")
            destination = (kind, name if kind == "skill" else source.name)
            if destination in destinations:
                raise ValueError(f"Duplicate installation destination: {destination}")
            destinations.add(destination)
            if not isinstance(item.get("dependencies", []), list) or not isinstance(item.get("resources", {}), dict):
                raise ValueError(f"Invalid dependencies/resources for {identifier}")
            if kind == "agent" and (source.suffix != ".toml" or item.get("resources")):
                raise ValueError(f"Agents must be single TOML files: {identifier}")
            self.items[identifier] = item
            seen_names.add((kind, name))
        if not self.items:
            raise ValueError("Empty catalog")
        for identifier, item in self.items.items():
            for dep in item.get("dependencies", []):
                if dep not in self.items:
                    raise ValueError(f"Unknown dependency {dep!r} for {identifier}")
            self.bundle(identifier)

    def select(self, *, skills=(), agents=(), groups=(), all_items=False) -> list[str]:
        unknown = set(groups) - GROUPS
        if unknown:
            raise ValueError(f"Unknown groups: {', '.join(sorted(unknown))}")
        selected = set(self.items) if all_items else set()
        selected.update(f"skill:{name}" for name in skills)
        selected.update(f"agent:{name}" for name in agents)
        selected.update(key for key, item in self.items.items() if item["group"] in groups)
        if selected - self.items.keys():
            raise ValueError(f"Unknown items: {', '.join(sorted(selected - self.items.keys()))}")
        visited: set[str] = set()

        def visit(key: str, trail: set[str]):
            if key in trail:
                raise ValueError(f"Cyclic catalog dependency: {key}")
            if key in visited:
                return
            for dep in self.items[key].get("dependencies", []):
                visit(dep, trail | {key})
            visited.add(key)

        for key in selected:
            visit(key, set())
        return sorted(visited)

    def bundle(self, identifier: str) -> dict[str, tuple[bytes, int]]:
        item = self.items[identifier]
        source = checked_path(self.root, item["path"])
        files: dict[str, tuple[bytes, int]] = {}

        def add(path: Path, target: str):
            relative_path(target)
            if path.is_symlink() or not path.is_file():
                raise ValueError(f"Expected regular catalog file: {path}")
            mode = stat.S_IMODE(path.stat().st_mode) & 0o777
            contents = (path.read_bytes(), mode)
            if target in files and files[target] != contents:
                raise ValueError(f"Conflicting bundled resource: {identifier}/{target}")
            files[target] = contents

        if item["kind"] == "skill":
            for path in sorted(source.rglob("*")):
                if path.is_symlink():
                    raise ValueError(f"Symlink in catalog: {path}")
                if path.is_file():
                    add(path, path.relative_to(source).as_posix())
        else:
            add(source, source.name)
        for target, resource in item.get("resources", {}).items():
            resource_path = checked_path(self.root, resource)
            if resource_path.is_dir():
                for path in sorted(resource_path.rglob("*")):
                    if path.is_symlink():
                        raise ValueError(f"Symlink in resource: {path}")
                    if path.is_file():
                        add(path, f"{target}/{path.relative_to(resource_path).as_posix()}")
            else:
                add(resource_path, target)
        for name in files:
            if any(parent.as_posix() in files for parent in Path(name).parents if parent != Path(".")):
                raise ValueError(f"File/directory collision in bundle: {identifier}/{name}")
        if item["kind"] == "agent":
            data = tomllib.loads(files[source.name][0].decode())
            if data.get("name") != item["name"] or not all(isinstance(data.get(k), str) and data[k].strip() for k in ("description", "developer_instructions")):
                raise ValueError(f"Invalid agent definition: {identifier}")
        else:
            skill = files.get("SKILL.md", (b"", 0))[0].decode()
            front = re.match(r"\A---\s*\n(.*?)\n---(?:\n|$)", skill, re.S)
            if not front:
                raise ValueError(f"Missing skill frontmatter: {identifier}")
            header = front.group(1)
            name_match = re.search(r"^name:\s*['\"]?([^\n'\"]+)['\"]?\s*$", header, re.M)
            if not name_match or name_match.group(1).strip() != item["name"] or not re.search(r"^description:\s*\S", header, re.M):
                raise ValueError(f"Invalid skill name/description: {identifier}")
        return files


def default_catalog() -> Catalog:
    packaged = Path(__file__).parent / "data"
    if packaged.is_dir():
        return Catalog(packaged)
    return Catalog(Path(__file__).resolve().parents[2])
