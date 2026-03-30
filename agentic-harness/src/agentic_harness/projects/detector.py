"""Auto-detect project type from directory contents."""

from __future__ import annotations

from enum import Enum
from pathlib import Path


class ProjectType(Enum):
    PYTHON_POETRY = "python-poetry"
    PYTHON_PANTS = "python-pants"
    PYTHON_SETUPTOOLS = "python-setuptools"
    TYPESCRIPT_PNPM = "typescript-pnpm"
    TYPESCRIPT_NPM = "typescript-npm"
    TERRAFORM = "terraform"
    UNKNOWN = "unknown"


def detect_project_type(path: str | Path) -> ProjectType:
    """Detect the project type from the directory contents."""
    p = Path(path)

    # Python: check pyproject.toml
    pyproject = p / "pyproject.toml"
    if pyproject.is_file():
        try:
            content = pyproject.read_text(encoding="utf-8")
        except OSError:
            content = ""
        if "[tool.poetry]" in content:
            return ProjectType.PYTHON_POETRY
        if "pants" in content.lower():
            return ProjectType.PYTHON_PANTS
        return ProjectType.PYTHON_SETUPTOOLS

    # Pants: check pants.toml
    if (p / "pants.toml").is_file():
        return ProjectType.PYTHON_PANTS

    # TypeScript: check package.json
    if (p / "package.json").is_file():
        if (p / "pnpm-workspace.yaml").is_file() or (p / "pnpm-lock.yaml").is_file():
            return ProjectType.TYPESCRIPT_PNPM
        return ProjectType.TYPESCRIPT_NPM

    # Terraform: check for .tf files
    if any(p.glob("*.tf")):
        return ProjectType.TERRAFORM

    return ProjectType.UNKNOWN
