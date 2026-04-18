"""Adaptive constraint management.

Tracks constraints across iterations with add/confirm/suspend/remove lifecycle.
AI-suggested constraints require user confirmation before activation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

CONSTRAINTS_FILE = "constraints.md"


@dataclass
class Constraint:
    """A pipeline constraint with lifecycle tracking."""

    id: str  # "C001"
    description: str
    source: str  # "user" | "ai-suggested"
    status: str  # "active" | "suspended" | "removed"
    created_at: str  # YYYY-MM-DD
    confirmed_at: str | None = None
    suspended_at: str | None = None
    removed_at: str | None = None
    reason: str | None = None


# Regex for parsing constraint lines:
# - [C001] description | 来源: user | 添加: 2026-04-08
_CONSTRAINT_RE = re.compile(
    r"^-\s+\[(?P<id>C\d+)\]\s+(?P<desc>.+?)\s*\|\s*来源:\s*(?P<source>\S+)"
    r"(?:\s*\|\s*添加:\s*(?P<created>\S+))?"
    r"(?:\s*\|\s*确认:\s*(?P<confirmed>\S+))?"
    r"(?:\s*\|\s*暂停:\s*(?P<suspended>\S+))?"
    r"(?:\s*\|\s*移除:\s*(?P<removed>\S+))?"
    r"(?:\s*\|\s*原因:\s*(?P<reason>.+))?$"
)


def load_constraints(project_dir: Path) -> list[Constraint]:
    """Parse constraints.md and return all constraints."""
    path = project_dir / CONSTRAINTS_FILE
    if not path.exists():
        return []

    text = path.read_text(encoding="utf-8")
    constraints: list[Constraint] = []
    current_status = "active"

    for line in text.splitlines():
        stripped = line.strip()

        # Detect section headers
        if stripped.startswith("## Active"):
            current_status = "active"
            continue
        elif stripped.startswith("## Suspended"):
            current_status = "suspended"
            continue
        elif stripped.startswith("## Removed"):
            current_status = "removed"
            continue

        m = _CONSTRAINT_RE.match(stripped)
        if m:
            constraints.append(
                Constraint(
                    id=m.group("id"),
                    description=m.group("desc").strip(),
                    source=m.group("source"),
                    status=current_status,
                    created_at=m.group("created") or "",
                    confirmed_at=m.group("confirmed"),
                    suspended_at=m.group("suspended"),
                    removed_at=m.group("removed"),
                    reason=m.group("reason").strip() if m.group("reason") else None,
                )
            )

    return constraints


def _next_id(constraints: list[Constraint]) -> str:
    """Generate the next constraint ID."""
    max_num = 0
    for c in constraints:
        try:
            num = int(c.id[1:])
            max_num = max(max_num, num)
        except ValueError:
            pass
    return f"C{max_num + 1:03d}"


def _write_constraints(project_dir: Path, constraints: list[Constraint]) -> None:
    """Write all constraints to constraints.md."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "# Pipeline Constraints\n",
        f"**项目**: {project_dir.name}",
        f"**最后更新**: {now}\n",
    ]

    for section_status, section_title in [
        ("active", "Active Constraints"),
        ("suspended", "Suspended Constraints"),
        ("removed", "Removed Constraints"),
    ]:
        lines.append(f"\n## {section_title}\n")
        section_items = [c for c in constraints if c.status == section_status]
        if not section_items:
            lines.append("（无）")
            continue
        for c in section_items:
            parts = [f"- [{c.id}] {c.description} | 来源: {c.source}"]
            if c.created_at:
                parts.append(f"添加: {c.created_at}")
            if c.confirmed_at:
                parts.append(f"确认: {c.confirmed_at}")
            if c.suspended_at:
                parts.append(f"暂停: {c.suspended_at}")
            if c.removed_at:
                parts.append(f"移除: {c.removed_at}")
            if c.reason:
                parts.append(f"原因: {c.reason}")
            lines.append(" | ".join(parts))

    from harness.state import _atomic_write

    _atomic_write(project_dir / CONSTRAINTS_FILE, "\n".join(lines) + "\n")


def add_constraint(
    project_dir: Path,
    description: str,
    source: str = "user",
) -> Constraint:
    """Add a new constraint. Returns the created Constraint."""
    if source not in ("user", "ai-suggested"):
        raise ValueError(f"Invalid source: {source}. Must be 'user' or 'ai-suggested'")

    constraints = load_constraints(project_dir)
    new_id = _next_id(constraints)
    today = datetime.now().strftime("%Y-%m-%d")

    new_constraint = Constraint(
        id=new_id,
        description=description,
        source=source,
        status="active",
        created_at=today,
    )
    constraints.append(new_constraint)
    _write_constraints(project_dir, constraints)
    return new_constraint


def confirm_constraint(project_dir: Path, constraint_id: str) -> None:
    """Confirm an ai-suggested constraint by adding confirmed date."""
    constraints = load_constraints(project_dir)
    for c in constraints:
        if c.id == constraint_id:
            if c.source != "ai-suggested":
                raise ValueError(
                    f"Constraint {constraint_id} is not ai-suggested, "
                    f"cannot confirm (source={c.source})"
                )
            c.confirmed_at = datetime.now().strftime("%Y-%m-%d")
            _write_constraints(project_dir, constraints)
            return
    raise ValueError(f"Constraint {constraint_id} not found")


def suspend_constraint(
    project_dir: Path, constraint_id: str, reason: str
) -> None:
    """Move a constraint from Active to Suspended."""
    constraints = load_constraints(project_dir)
    for c in constraints:
        if c.id == constraint_id:
            c.status = "suspended"
            c.suspended_at = datetime.now().strftime("%Y-%m-%d")
            c.reason = reason
            _write_constraints(project_dir, constraints)
            return
    raise ValueError(f"Constraint {constraint_id} not found")


def remove_constraint(
    project_dir: Path, constraint_id: str, reason: str
) -> None:
    """Move a constraint to Removed."""
    constraints = load_constraints(project_dir)
    for c in constraints:
        if c.id == constraint_id:
            c.status = "removed"
            c.removed_at = datetime.now().strftime("%Y-%m-%d")
            c.reason = reason
            _write_constraints(project_dir, constraints)
            return
    raise ValueError(f"Constraint {constraint_id} not found")
