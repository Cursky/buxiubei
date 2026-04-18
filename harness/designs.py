"""Design document management — read/write .harness/designs/*.md.

Manages auto-numbered design documents from /moying-brainstorm.
"""

from __future__ import annotations

import re
from pathlib import Path


def get_next_design_number(harness_dir: Path) -> int:
    """Scan .harness/designs/ and return next available number."""
    designs_dir = harness_dir / "designs"
    if not designs_dir.exists():
        return 1

    max_num = 0
    for f in designs_dir.glob("[0-9][0-9][0-9]-*.md"):
        name = f.stem
        num_str = name.split("-")[0]
        try:
            num = int(num_str)
            max_num = max(max_num, num)
        except ValueError:
            pass
    return max_num + 1


def save_design(
    harness_dir: Path,
    number: int,
    topic: str,
    content: str,
) -> Path:
    """Write a design document and return its path."""
    designs_dir = harness_dir / "designs"
    designs_dir.mkdir(parents=True, exist_ok=True)

    slug = _slugify(topic)
    filename = f"{number:03d}-{slug}.md"
    path = designs_dir / filename

    from harness.state import _atomic_write
    _atomic_write(path, content)
    return path


def list_designs(harness_dir: Path) -> list[dict[str, str]]:
    """List all design documents with number and title."""
    designs_dir = harness_dir / "designs"
    if not designs_dir.exists():
        return []

    designs: list[dict[str, str]] = []
    for f in sorted(designs_dir.glob("[0-9][0-9][0-9]-*.md")):
        name = f.stem
        parts = name.split("-", 1)
        designs.append({
            "number": parts[0],
            "topic": parts[1] if len(parts) > 1 else "",
            "path": str(f),
        })
    return designs


def _slugify(text: str, max_length: int = 50) -> str:
    """Convert text to a filename-safe slug."""
    # Keep Chinese characters, alphanumeric, replace rest with hyphen
    slug = re.sub(r"[^\w\u4e00-\u9fff]", "-", text.lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:max_length]
