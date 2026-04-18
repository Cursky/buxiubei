"""Pipeline status file reading and writing.

Reads/writes pipeline-status.md in Markdown table format.
Uses regex parsing only — no external dependencies.
"""

from __future__ import annotations

import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

STATUS_FILE = "pipeline-status.md"
VALID_STATUSES = {"not-started", "in-progress", "complete"}

# Matches table rows: | col1 | col2 | col3 | ...
_TABLE_ROW_RE = re.compile(r"^\|(.+)\|$")
_SEPARATOR_RE = re.compile(r"^[\|\s\-:]+$")


def _parse_table(lines: list[str]) -> list[list[str]]:
    """Parse Markdown table lines into a list of cell rows."""
    rows: list[list[str]] = []
    for line in lines:
        line = line.strip()
        if _SEPARATOR_RE.match(line):
            continue
        m = _TABLE_ROW_RE.match(line)
        if m:
            cells = [c.strip() for c in m.group(1).split("|")]
            rows.append(cells)
    return rows


def read_pipeline_status(project_dir: Path) -> dict[str, Any]:
    """Read pipeline-status.md and return structured status dict.

    Returns:
        {
            "global": {"script-analysis": "complete", ...},
            "episodes": {"screenplay": {"EP01": "complete", ...}, ...}
        }
    """
    status_path = project_dir / STATUS_FILE
    if not status_path.exists():
        raise FileNotFoundError(f"Pipeline status file not found: {status_path}")

    text = status_path.read_text(encoding="utf-8")
    result: dict[str, Any] = {"global": {}, "episodes": {}}

    sections = re.split(r"^## ", text, flags=re.MULTILINE)
    for section in sections:
        lines = section.strip().splitlines()
        if not lines:
            continue

        header = lines[0].strip()
        table_rows = _parse_table(lines[1:])
        if len(table_rows) < 2:  # need header + at least 1 data row
            continue

        if "全局" in header:
            for row in table_rows[1:]:
                if len(row) >= 2:
                    result["global"][row[0]] = row[1]

        elif "按集" in header:
            header_row = table_rows[0]
            episodes = header_row[1:]
            for row in table_rows[1:]:
                if len(row) < 2:
                    continue
                step = row[0]
                result["episodes"][step] = {}
                for i, ep in enumerate(episodes):
                    if i + 1 < len(row):
                        result["episodes"][step][ep] = row[i + 1]

    return result


def write_pipeline_status(
    project_dir: Path, status: dict[str, Any]
) -> None:
    """Write status dict to pipeline-status.md atomically."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "# Pipeline Status\n",
        f"**项目**: {project_dir.name}\n",
        f"**最后更新**: {now}\n",
        "\n## 全局步骤\n",
        "| 步骤 | 状态 | 更新时间 |",
        "|------|------|---------|",
    ]

    for step, st in status.get("global", {}).items():
        lines.append(f"| {step} | {st} | {now} |")

    episodes_data = status.get("episodes", {})
    if episodes_data:
        all_eps: set[str] = set()
        for step_eps in episodes_data.values():
            all_eps.update(step_eps.keys())
        eps_sorted = sorted(all_eps)

        if eps_sorted:
            lines.append("\n## 按集步骤\n")
            header = "| 步骤 | " + " | ".join(eps_sorted) + " |"
            sep = "|------" + "|------" * len(eps_sorted) + "|"
            lines.append(header)
            lines.append(sep)

            for step, ep_map in episodes_data.items():
                row = f"| {step}"
                for ep in eps_sorted:
                    row += f" | {ep_map.get(ep, 'not-started')}"
                row += " |"
                lines.append(row)

    content = "\n".join(lines) + "\n"
    _atomic_write(project_dir / STATUS_FILE, content)


def update_step_status(
    project_dir: Path,
    step: str,
    episode: str | None,
    status_val: str,
) -> None:
    """Update a single step/episode status entry."""
    if status_val not in VALID_STATUSES:
        raise ValueError(
            f"Invalid status '{status_val}'. Must be one of: {VALID_STATUSES}"
        )

    current = read_pipeline_status(project_dir)

    if episode is None:
        current["global"][step] = status_val
    else:
        if step not in current["episodes"]:
            current["episodes"][step] = {}
        current["episodes"][step][episode] = status_val

    write_pipeline_status(project_dir, current)


def _atomic_write(path: Path, content: str) -> None:
    """Write content to file atomically via temp file + rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = tempfile.NamedTemporaryFile(
        mode="w",
        dir=path.parent,
        suffix=".tmp",
        delete=False,
        encoding="utf-8",
    )
    try:
        tmp.write(content)
        tmp.close()
        Path(tmp.name).replace(path)
    except Exception:
        Path(tmp.name).unlink(missing_ok=True)
        raise
