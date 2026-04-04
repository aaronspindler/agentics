"""Context assembler: loads .ai/ docs and CLAUDE.md per agent role."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class AgentRole(Enum):
    PLANNER = "planner"
    GENERATOR = "generator"
    EVALUATOR = "evaluator"


# Which .ai/ doc patterns to load per role
ROLE_DOC_PATTERNS: dict[AgentRole, list[str]] = {
    AgentRole.PLANNER: [
        "PROJECT_OVERVIEW*",
        "ARCHITECTURE*",
        "GLOSSARY*",
        "PATTERNS*",
        "PRINCIPLES*",
    ],
    AgentRole.GENERATOR: [
        "ARCHITECTURE*",
        "PATTERNS*",
        "*STYLE*",
        "TESTING*",
        "DATABASE_MODELS*",
    ],
    AgentRole.EVALUATOR: [
        "PRINCIPLES*",
        "SECURITY*",
        "TESTING*",
        "*STYLE*",
        "review-prompts/*",
    ],
}


@dataclass
class ProjectContext:
    project_path: str
    project_type: str
    claude_md: str = ""
    root_claude_md: str = ""
    ai_docs: dict[str, str] = field(default_factory=dict)

    def to_prompt_section(self) -> str:
        """Format the context as a string for injection into system prompts."""
        sections: list[str] = []

        if self.root_claude_md:
            sections.append(f"# Root Repository Guidance\n\n{self.root_claude_md}")

        if self.claude_md:
            sections.append(f"# Project Guidance (CLAUDE.md)\n\n{self.claude_md}")

        if self.ai_docs:
            sections.append("# Project Documentation (.ai/)")
            for name, content in sorted(self.ai_docs.items()):
                sections.append(f"\n## {name}\n\n{content}")

        return "\n\n---\n\n".join(sections)


class ContextAssembler:
    """Loads project context selectively based on agent role."""

    def __init__(self, project_path: str, root_path: str | None = None) -> None:
        self.project_path = Path(project_path).resolve()
        self.root_path = Path(root_path).resolve() if root_path else None

    def assemble(self, role: AgentRole) -> ProjectContext:
        """Assemble context for a specific agent role."""
        from .projects.detector import detect_project_type

        project_type = detect_project_type(self.project_path)

        ctx = ProjectContext(
            project_path=str(self.project_path),
            project_type=project_type.value,
        )

        # Load CLAUDE.md from project
        claude_md_path = self.project_path / "CLAUDE.md"
        if claude_md_path.is_file():
            ctx.claude_md = self._read_safe(claude_md_path)

        # Load root CLAUDE.md if different
        if self.root_path and self.root_path != self.project_path:
            root_claude = self.root_path / "CLAUDE.md"
            if root_claude.is_file():
                ctx.root_claude_md = self._read_safe(root_claude)

        # Load .ai/ docs matching the role's patterns
        ai_dir = self.project_path / ".ai"
        if ai_dir.is_dir():
            patterns = ROLE_DOC_PATTERNS.get(role, [])
            ctx.ai_docs = self._load_matching_docs(ai_dir, patterns)

        return ctx

    def _load_matching_docs(self, ai_dir: Path, patterns: list[str]) -> dict[str, str]:
        """Load .ai/ files matching the given glob patterns."""
        docs: dict[str, str] = {}
        seen: set[Path] = set()

        for pattern in patterns:
            for match in sorted(ai_dir.glob(pattern)):
                if match.is_file() and match not in seen and match.suffix == ".md":
                    seen.add(match)
                    rel_name = str(match.relative_to(ai_dir))
                    content = self._read_safe(match)
                    if content:
                        docs[rel_name] = content

        return docs

    @staticmethod
    def _read_safe(path: Path, max_chars: int = 50_000) -> str:
        """Read a file, truncating if too large."""
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""
        if len(text) > max_chars:
            text = text[:max_chars] + "\n... (truncated)"
        return text
