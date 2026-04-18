"""Acceptance criteria validation for pipeline step outputs.

Validates step outputs against acceptance criteria before marking complete.
Criteria can be generic (file exists, marker present) or step-specific.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

from harness.completion import COMPLETE_MARKER


@dataclass
class AcceptanceCriterion:
    """A single acceptance criterion for a pipeline step."""

    id: str
    description: str
    check_fn: Callable[[Path], bool]


@dataclass
class ValidationResult:
    """Result of validating a single criterion."""

    criterion_id: str
    description: str
    passed: bool
    detail: str = ""


def _check_file_exists_and_nonempty(path: Path) -> bool:
    """Check that a file exists and is not empty."""
    return path.exists() and path.stat().st_size > 0


def _check_step_complete_marker(path: Path) -> bool:
    """Check that a file contains the STEP_COMPLETE marker."""
    if not path.exists():
        return False
    try:
        text = path.read_text(encoding="utf-8")
        return COMPLETE_MARKER in text
    except (OSError, UnicodeDecodeError):
        return False


def _check_file_size_within_bounds(
    path: Path, min_bytes: int = 50, max_bytes: int = 500_000
) -> bool:
    """Check that file size is within reasonable bounds."""
    if not path.exists():
        return False
    size = path.stat().st_size
    return min_bytes <= size <= max_bytes


# ── Built-in Criteria ─────────────────────────────────────

GENERIC_CRITERIA = [
    AcceptanceCriterion(
        id="GEN-001",
        description="文件存在且非空",
        check_fn=_check_file_exists_and_nonempty,
    ),
    AcceptanceCriterion(
        id="GEN-002",
        description="包含 STEP_COMPLETE 标记",
        check_fn=_check_step_complete_marker,
    ),
    AcceptanceCriterion(
        id="GEN-003",
        description="文件大小在合理范围内",
        check_fn=_check_file_size_within_bounds,
    ),
]


def validate_step_output(
    step_name: str,
    output_path: Path,
    criteria: list[AcceptanceCriterion] | None = None,
) -> list[ValidationResult]:
    """Run all criteria against an output file.

    Args:
        step_name: Name of the pipeline step.
        output_path: Path to the output file to validate.
        criteria: Custom criteria; defaults to GENERIC_CRITERIA.

    Returns:
        List of ValidationResult for each criterion.
    """
    if criteria is None:
        criteria = GENERIC_CRITERIA

    results: list[ValidationResult] = []
    for crit in criteria:
        try:
            passed = crit.check_fn(output_path)
            results.append(
                ValidationResult(
                    criterion_id=crit.id,
                    description=crit.description,
                    passed=passed,
                    detail="" if passed else f"文件: {output_path}",
                )
            )
        except Exception as e:
            results.append(
                ValidationResult(
                    criterion_id=crit.id,
                    description=crit.description,
                    passed=False,
                    detail=f"检查异常: {e}",
                )
            )

    return results


def log_validation(
    project_dir: Path,
    step_name: str,
    results: list[ValidationResult],
) -> None:
    """Append validation record to validation-log.md."""
    log_path = project_dir / "validation-log.md"
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines: list[str] = []
    if not log_path.exists():
        lines.append("# Validation Log\n")

    lines.append(f"\n## {step_name} — {now}\n")
    lines.append("| 条目 | 描述 | 结果 | 详情 |")
    lines.append("|------|------|------|------|")

    for r in results:
        status = "✅ PASS" if r.passed else "❌ FAIL"
        lines.append(f"| {r.criterion_id} | {r.description} | {status} | {r.detail} |")

    lines.append("")

    with open(log_path, "a", encoding="utf-8") as f:
        f.write("\n".join(lines))
