"""Plan directory management — read/write .harness/plans/.

Manages auto-numbered plan directories and their tasks.md task lists.
"""

from __future__ import annotations

import re
from pathlib import Path

from harness.state import _atomic_write

PLANS_DIR = "plans"

# Matches task lines:
# - [ ] T001 description | 输入: x | 输出: y | 命令: z
_TASK_RE = re.compile(
    r"^- \[([xX ])\] (T\d+)\s+(.+?)(?:\s*\|\s*输入:\s*(.+?))?(?:\s*\|\s*输出:\s*(.+?))?(?:\s*\|\s*命令:\s*(.+))?$"
)


# ---------------------------------------------------------------------------
# Plan directory helpers
# ---------------------------------------------------------------------------


def get_next_plan_number(harness_dir: Path) -> int:
    """Scan .harness/plans/ for NNN-* dirs and return the next available number."""
    plans_dir = harness_dir / PLANS_DIR
    if not plans_dir.exists():
        return 1

    max_num = 0
    for entry in plans_dir.iterdir():
        if entry.is_dir():
            m = re.match(r"^(\d{3})", entry.name)
            if m:
                try:
                    num = int(m.group(1))
                    max_num = max(max_num, num)
                except ValueError:
                    pass
    return max_num + 1


def create_plan_dir(harness_dir: Path, number: int, name: str) -> Path:
    """Create .harness/plans/{NNN}-{name}/ and return the path."""
    slug = _slugify(name)
    dir_name = f"{number:03d}-{slug}"
    plan_path = harness_dir / PLANS_DIR / dir_name
    plan_path.mkdir(parents=True, exist_ok=True)
    return plan_path


# ---------------------------------------------------------------------------
# Task parsing
# ---------------------------------------------------------------------------


def parse_tasks(tasks_path: Path) -> list[dict]:
    """Parse tasks.md into a list of task dicts.

    Returns list of::

        {
            "id": "T001",
            "description": str,
            "input": str,
            "output": str,
            "command": str,
            "done": bool,
        }
    """
    if not tasks_path.exists():
        return []

    tasks: list[dict] = []
    for line in tasks_path.read_text(encoding="utf-8").splitlines():
        m = _TASK_RE.match(line.rstrip())
        if m:
            checkbox, task_id, description, inp, out, cmd = m.groups()
            tasks.append(
                {
                    "id": task_id,
                    "description": description.strip(),
                    "input": (inp or "").strip(),
                    "output": (out or "").strip(),
                    "command": (cmd or "").strip(),
                    "done": checkbox.lower() == "x",
                }
            )
    return tasks


def mark_task_done(tasks_path: Path, task_id: str) -> None:
    """Toggle task checkbox from ``[ ]`` to ``[x]`` for the given task ID."""
    if not tasks_path.exists():
        raise FileNotFoundError(f"Tasks file not found: {tasks_path}")

    lines = tasks_path.read_text(encoding="utf-8").splitlines(keepends=True)
    updated = False
    new_lines: list[str] = []
    for line in lines:
        m = _TASK_RE.match(line.rstrip())
        if m and m.group(2) == task_id:
            # Replace first occurrence of `[ ]` with `[x]`
            new_line = line.replace("[ ]", "[x]", 1)
            new_lines.append(new_line)
            updated = True
        else:
            new_lines.append(line)

    if not updated:
        raise KeyError(f"Task '{task_id}' not found in {tasks_path}")

    _atomic_write(tasks_path, "".join(new_lines))


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _slugify(text: str, max_length: int = 50) -> str:
    """Convert text to a filename-safe slug (keeps Chinese characters)."""
    slug = re.sub(r"[^\w\u4e00-\u9fff]", "-", text.lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:max_length]
