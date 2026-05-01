"""Maps project types to their default commands."""

from __future__ import annotations

from .detector import ProjectType

# Default commands per project type
PROJECT_COMMANDS: dict[ProjectType, dict[str, str]] = {
    ProjectType.PYTHON_POETRY: {
        "install": "poetry install",
        "test": "poetry run pytest",
        "lint": "poetry run pre-commit run --all-files",
        "format": "poetry run black src/ tests/ && poetry run isort src/ tests/ --profile black",
    },
    ProjectType.PYTHON_PANTS: {
        "install": "pants export --resolve=python-default",
        "test": "just test",
        "lint": "pants lint ::",
    },
    ProjectType.PYTHON_SETUPTOOLS: {
        "install": "pip install -e .",
        "test": "python -m pytest",
        "lint": "pre-commit run --all-files",
    },
    ProjectType.TYPESCRIPT_PNPM: {
        "install": "pnpm install",
        "test": "pnpm test",
        "lint": "pnpm run lint",
        "format": "pnpm run format",
    },
    ProjectType.TYPESCRIPT_NPM: {
        "install": "npm install",
        "test": "npm test",
        "lint": "npm run lint",
    },
    ProjectType.TERRAFORM: {
        "validate": "terraform validate",
        "format": "terraform fmt -recursive",
        "lint": "terraform fmt -check",
    },
    ProjectType.UNKNOWN: {},
}


def get_command(project_type: ProjectType, command_name: str) -> str | None:
    """Get the default command for a project type."""
    commands = PROJECT_COMMANDS.get(project_type, {})
    return commands.get(command_name)
