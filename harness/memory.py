"""Clarification persistence — read/write .harness/clarifications.md.

Manages active and archived clarifications with conflict detection.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

CLARIFICATIONS_FILE = "clarifications.md"
_ENTRY_RE = re.compile(r"^-\s+\[(\d{4}-\d{2}-\d{2})\]\s+(.+)$")


def _char_ngrams(text: str, n: int = 3) -> set[str]:
    """Generate character n-grams from text (works for Chinese)."""
    return {text[i:i + n] for i in range(len(text) - n + 1)} if len(text) >= n else set()


def load_clarifications(harness_dir: Path) -> list[dict[str, Any]]:
    """Parse clarifications.md into a list of entries.

    Returns list of {"date": str, "content": str, "archived": bool}
    """
    path = harness_dir / CLARIFICATIONS_FILE
    if not path.exists():
        return []

    text = path.read_text(encoding="utf-8")
    entries: list[dict[str, Any]] = []
    in_archived = False

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("## 已归档"):
            in_archived = True
            continue
        if stripped.startswith("## 活跃"):
            in_archived = False
            continue

        m = _ENTRY_RE.match(stripped)
        if m:
            entries.append({
                "date": m.group(1),
                "content": m.group(2),
                "archived": in_archived,
            })

    return entries


def add_clarification(
    harness_dir: Path, text: str
) -> dict[str, Any]:
    """Add a new clarification. Returns the created entry.

    Detects conflicts by simple keyword overlap with existing entries.
    If a conflict is found, the old entry is archived.
    """
    entries = load_clarifications(harness_dir)
    today = datetime.now().strftime("%Y-%m-%d")
    new_entry = {"date": today, "content": text, "archived": False}

    # Conflict detection: character n-gram overlap (works for Chinese)
    text_lower = text.lower()
    new_ngrams = _char_ngrams(text_lower, 3)
    for entry in entries:
        if entry["archived"]:
            continue
        old_ngrams = _char_ngrams(entry["content"].lower(), 3)
        if not old_ngrams or not new_ngrams:
            continue
        overlap = len(old_ngrams & new_ngrams) / min(len(old_ngrams), len(new_ngrams))
        if overlap > 0.5:
            entry["archived"] = True
            entry["content"] = f"(已被 {today} 条目覆盖) {entry['content']}"

    entries.append(new_entry)
    _write_clarifications(harness_dir, entries)
    return new_entry


def archive_clarification(
    harness_dir: Path, index: int, reason: str
) -> None:
    """Archive an active clarification by its 0-based index."""
    entries = load_clarifications(harness_dir)
    active = [e for e in entries if not e["archived"]]
    if not active or index < 0 or index >= len(active):
        raise IndexError(
            f"Index {index} out of range"
            + (f" (0-{len(active)-1})" if active else " (no active entries)")
        )

    target = active[index]
    target["archived"] = True
    target["content"] = f"({reason}) {target['content']}"
    _write_clarifications(harness_dir, entries)


def _write_clarifications(
    harness_dir: Path, entries: list[dict[str, Any]]
) -> None:
    """Write all entries back to clarifications.md."""
    active = [e for e in entries if not e["archived"]]
    archived = [e for e in entries if e["archived"]]

    lines = ["# 项目澄清记录\n", "\n## 活跃澄清\n"]
    for e in active:
        lines.append(f"- [{e['date']}] {e['content']}")
    if not active:
        lines.append("")

    lines.append("\n## 已归档\n")
    for e in archived:
        lines.append(f"- [{e['date']}] {e['content']}")
    if not archived:
        lines.append("")

    from harness.state import _atomic_write
    _atomic_write(harness_dir / CLARIFICATIONS_FILE, "\n".join(lines) + "\n")
