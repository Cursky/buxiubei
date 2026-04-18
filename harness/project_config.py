"""Project configuration — read/write .harness/constitution.md and project-spec.md.

Manages guiding principles (constitution) and static key-value project spec.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from harness.memory import load_clarifications
from harness.state import _atomic_write

CONSTITUTION_FILE = "constitution.md"
PROJECT_SPEC_FILE = "project-spec.md"

# - [P001] description | 添加: YYYY-MM-DD
_PRINCIPLE_RE = re.compile(
    r"^-\s+\[(?P<id>P\d+)\]\s+(?P<desc>.+?)\s*\|\s*添加:\s*(?P<date>\S+)$"
)

# key: value  (first colon splits key from value)
_KV_RE = re.compile(r"^([^:]+):\s*(.+)$")


# ---------------------------------------------------------------------------
# Constitution
# ---------------------------------------------------------------------------


def load_constitution(harness_dir: Path) -> list[dict]:
    """Parse .harness/constitution.md into a list of principle dicts.

    Returns list of {"id": "P001", "description": str, "date": str}.
    """
    path = harness_dir / CONSTITUTION_FILE
    if not path.exists():
        return []

    entries: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = _PRINCIPLE_RE.match(line.strip())
        if m:
            entries.append(
                {
                    "id": m.group("id"),
                    "description": m.group("desc"),
                    "date": m.group("date"),
                }
            )
    return entries


def add_principle(harness_dir: Path, description: str) -> dict:
    """Auto-increment P{NNN} ID, append principle to file, return created entry.

    Returns {"id": "P001", "description": str, "date": str}.
    """
    entries = load_constitution(harness_dir)
    today = datetime.now().strftime("%Y-%m-%d")

    # Determine next ID
    max_num = 0
    for e in entries:
        try:
            num = int(e["id"][1:])  # strip leading 'P'
            max_num = max(max_num, num)
        except ValueError:
            pass
    new_id = f"P{max_num + 1:03d}"

    new_entry: dict = {"id": new_id, "description": description, "date": today}
    entries.append(new_entry)
    _write_constitution(harness_dir, entries)
    return new_entry


def remove_principle(harness_dir: Path, principle_id: str) -> None:
    """Remove a principle by ID (case-insensitive match on the numeric part)."""
    entries = load_constitution(harness_dir)
    norm = principle_id.upper()
    filtered = [e for e in entries if e["id"].upper() != norm]
    if len(filtered) == len(entries):
        raise KeyError(f"Principle '{principle_id}' not found in constitution")
    _write_constitution(harness_dir, filtered)


def _write_constitution(harness_dir: Path, entries: list[dict]) -> None:
    """Serialise all entries back to constitution.md atomically."""
    lines = ["# 项目原则 (Constitution)\n"]
    for e in entries:
        lines.append(f"- [{e['id']}] {e['description']} | 添加: {e['date']}")
    if not entries:
        lines.append("")

    _atomic_write(
        harness_dir / CONSTITUTION_FILE, "\n".join(lines) + "\n"
    )


# ---------------------------------------------------------------------------
# Project spec
# ---------------------------------------------------------------------------


def load_project_spec(harness_dir: Path) -> dict[str, str]:
    """Parse .harness/project-spec.md key-value pairs.

    Returns mapping of {key: value}.  Lines not matching ``key: value``
    format (headers, blank lines, etc.) are silently ignored.
    """
    path = harness_dir / PROJECT_SPEC_FILE
    if not path.exists():
        return {}

    spec: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        m = _KV_RE.match(stripped)
        if m:
            spec[m.group(1).strip()] = m.group(2).strip()
    return spec


# ---------------------------------------------------------------------------
# Full context
# ---------------------------------------------------------------------------


def load_full_context(harness_dir: Path) -> str:
    """Return clarifications + constitution + project-spec as Markdown string."""
    parts: list[str] = []

    # 1. Clarifications
    clarifications = load_clarifications(harness_dir)
    active_clarifications = [c for c in clarifications if not c["archived"]]
    if active_clarifications:
        parts.append("## 活跃澄清\n")
        for c in active_clarifications:
            parts.append(f"- [{c['date']}] {c['content']}")
        parts.append("")

    # 2. Constitution
    principles = load_constitution(harness_dir)
    if principles:
        parts.append("## 项目原则\n")
        for p in principles:
            parts.append(
                f"- [{p['id']}] {p['description']} | 添加: {p['date']}"
            )
        parts.append("")

    # 3. Project spec
    spec = load_project_spec(harness_dir)
    if spec:
        parts.append("## 项目规格\n")
        for key, value in spec.items():
            parts.append(f"- {key}: {value}")
        parts.append("")

    return "\n".join(parts)
