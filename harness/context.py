"""Full context building for context-free session startup.

Orchestrates all context sources (pipeline status, constraints,
spec-kit memory, recent feedback) into a comprehensive Markdown
string that an AI assistant can read as first-response context.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from harness.constraints import load_constraints
from harness.resume import generate_resume_context


def build_full_context(project_dir: Path) -> str:
    """Build comprehensive context for AI session startup.

    Combines:
    1. Pipeline status (via generate_resume_context)
    2. Active constraints from constraints.md
    3. User corrections from .specify/memory/
    """
    parts: list[str] = []

    # 1. Pipeline status + resume context
    resume = generate_resume_context(project_dir)
    parts.append(resume)

    # 2. Active constraints
    constraints = load_constraints(project_dir)
    active = [c for c in constraints if c.status == "active"]
    if active:
        parts.append("### 活跃约束")
        for c in active:
            confirmed = " (已确认)" if c.confirmed_at else ""
            parts.append(f"- [{c.id}] {c.description}{confirmed}")
        parts.append("")

    # 3. Spec-kit memory (user corrections/preferences)
    memory_dir = project_dir / ".specify" / "memory"
    if memory_dir.exists():
        memory_entries = _read_memory_files(memory_dir)
        if memory_entries:
            parts.append("### 用户纠正 (来自 spec-kit memory)")
            for entry in memory_entries:
                parts.append(f"- {entry}")
            parts.append("")

    return "\n".join(parts)


def _read_memory_files(memory_dir: Path) -> list[str]:
    """Read .specify/memory/ files and extract relevant entries."""
    entries: list[str] = []
    for f in sorted(memory_dir.glob("*.md")):
        try:
            text = f.read_text(encoding="utf-8")
            # Extract the first non-frontmatter, non-empty line as summary
            in_frontmatter = False
            for line in text.splitlines():
                stripped = line.strip()
                if stripped == "---":
                    in_frontmatter = not in_frontmatter
                    continue
                if in_frontmatter or not stripped:
                    continue
                if stripped.startswith("#"):
                    continue
                entries.append(stripped)
                break
        except (OSError, UnicodeDecodeError):
            continue
    return entries
