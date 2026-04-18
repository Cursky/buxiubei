"""Project analysis — naming consistency, format compliance, constitution checks.

Orchestrates multiple analysis passes over a MoYing project directory and
returns a formatted Markdown report.
"""

from __future__ import annotations

import re
from pathlib import Path

from harness.completion import COMPLETE_MARKER
from harness.project_config import load_constitution

# Canonical character table is expected here (relative to project root)
_CHARACTER_TABLE_REL = "素材提取/角色表.md"

# Episode screenplay files follow this pattern
_EP_SCREENPLAY_PATTERN = re.compile(r"^EP(\d+)_剧本\.md$")

# Lines like `### 角色名` define canonical names in the character table
_CHARACTER_HEADING_RE = re.compile(r"^###\s+(.+)$")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_analysis(project_dir: Path) -> str:
    """Orchestrate all analysis checks and return a formatted Markdown report."""
    harness_dir = project_dir / ".harness"

    naming_findings = check_naming_consistency(project_dir)
    format_findings = check_format_compliance(project_dir)
    constitution_findings = check_constitution_compliance(project_dir, harness_dir)

    lines: list[str] = ["# 项目分析报告\n"]

    lines.append("## 角色名一致性\n")
    if naming_findings:
        for f in naming_findings:
            lines.append(f"- {f}")
    else:
        lines.append("- 未发现命名不一致问题")
    lines.append("")

    lines.append("## 格式合规性\n")
    if format_findings:
        for f in format_findings:
            lines.append(f"- {f}")
    else:
        lines.append("- 未发现格式问题")
    lines.append("")

    lines.append("## 原则合规性\n")
    if constitution_findings:
        for f in constitution_findings:
            lines.append(f"- {f}")
    else:
        lines.append("- 未发现原则违规")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------


def check_naming_consistency(project_dir: Path) -> list[str]:
    """Check that character names in .md files match the canonical character table.

    Extracts canonical names from 素材提取/角色表.md (lines matching ``### {name}``),
    then scans all .md files in the project for names that differ by exactly
    one character (likely typos).

    Returns a list of finding strings.
    """
    findings: list[str] = []

    char_table = project_dir / _CHARACTER_TABLE_REL
    if not char_table.exists():
        return findings

    canonical_names = _extract_canonical_names(char_table)
    if not canonical_names:
        return findings

    # Scan all .md files in the project (excluding the character table itself)
    for md_file in sorted(project_dir.rglob("*.md")):
        if md_file.resolve() == char_table.resolve():
            continue
        try:
            text = md_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        # Find all Chinese-word-like tokens that could be character names
        # We look for occurrences of names that are close but not equal to canonical
        for candidate in _extract_name_candidates(text, canonical_names):
            for canonical in canonical_names:
                if candidate != canonical and _edit_distance_one(candidate, canonical):
                    rel = md_file.relative_to(project_dir)
                    findings.append(
                        f"{rel}: 角色名 '{candidate}' 与角色表 '{canonical}' 不一致"
                    )
    return findings


def check_format_compliance(project_dir: Path) -> list[str]:
    """Verify STEP_COMPLETE markers and EP numbering continuity.

    Returns a list of finding strings.
    """
    findings: list[str] = []

    # Check STEP_COMPLETE markers across all per-episode output directories
    ep_dirs = [
        ("剧本", "EP*_剧本.md"),
        ("分镜设计", "EP*_分镜.md"),
        ("视频提示词", "EP*_提示词.md"),
        ("台词本", "EP*_台词本.md"),
        ("音乐提示词", "EP*_音乐.md"),
    ]

    for dir_name, pattern in ep_dirs:
        target_dir = project_dir / dir_name
        if not target_dir.exists():
            continue
        ep_numbers: list[int] = []
        for md_file in sorted(target_dir.glob(pattern)):
            m = re.match(r"EP(\d+)", md_file.name)
            if m:
                ep_numbers.append(int(m.group(1)))
            try:
                text = md_file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                findings.append(f"{dir_name}/{md_file.name}: 无法读取文件")
                continue
            if COMPLETE_MARKER not in text:
                findings.append(f"{dir_name}/{md_file.name}: 缺少 STEP_COMPLETE 标记")

        # Check EP numbering continuity
        if ep_numbers:
            ep_numbers.sort()
            for expected, actual in enumerate(ep_numbers, start=ep_numbers[0]):
                if actual != expected:
                    findings.append(
                        f"{dir_name}/: EP编号不连续 — 预期 EP{expected:02d}, 实际 EP{actual:02d}"
                    )
                    break

    # Check global files
    for global_file in ["剧本分析.md", "集拆分.md"]:
        path = project_dir / global_file
        if path.exists():
            try:
                text = path.read_text(encoding="utf-8")
                if COMPLETE_MARKER not in text:
                    findings.append(f"{global_file}: 缺少 STEP_COMPLETE 标记")
            except (OSError, UnicodeDecodeError):
                findings.append(f"{global_file}: 无法读取文件")

    return findings


def check_constitution_compliance(
    project_dir: Path, harness_dir: Path
) -> list[str]:
    """Check project files for violations of constitution principles.

    For each principle whose description contains quotable keywords (text
    enclosed in 「」 brackets), grep all .md project files for those keywords.
    Reports files where the keyword appears in a context that may violate the
    principle.

    Returns a list of finding strings.
    """
    findings: list[str] = []

    principles = load_constitution(harness_dir)
    if not principles:
        return findings

    # Collect all project .md file texts once, excluding the harness dir itself
    md_files: list[tuple[Path, str]] = []
    harness_resolved = harness_dir.resolve()
    for md_file in sorted(project_dir.rglob("*.md")):
        # Skip files that live inside the harness directory
        try:
            md_file.resolve().relative_to(harness_resolved)
            continue  # inside harness dir — skip
        except ValueError:
            pass
        try:
            text = md_file.read_text(encoding="utf-8")
            md_files.append((md_file, text))
        except (OSError, UnicodeDecodeError):
            continue

    for principle in principles:
        desc = principle["description"]
        keywords = _extract_quoted_keywords(desc)
        if not keywords:
            continue

        # Determine if this is a prohibition ("禁止"/"不要"/"不得") or requirement ("必须"/"使用")
        is_prohibition = any(w in desc for w in ("禁止", "不要", "不得", "避免", "禁用"))

        for keyword in keywords:
            for md_file, text in md_files:
                if is_prohibition and keyword in text:
                    rel = md_file.relative_to(project_dir)
                    findings.append(
                        f"{rel}: 违反原则 [{principle['id']}] — 包含被禁止的 '{keyword}'"
                    )
                elif not is_prohibition and keyword not in text:
                    # Positive rule: keyword should be present (only check relevant files)
                    # Skip files that wouldn't contain the keyword naturally
                    pass  # too noisy to report absence in every file

    return findings


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _extract_canonical_names(char_table: Path) -> list[str]:
    """Extract ``### Name`` headings from the character table as canonical names."""
    names: list[str] = []
    try:
        for line in char_table.read_text(encoding="utf-8").splitlines():
            m = _CHARACTER_HEADING_RE.match(line.strip())
            if m:
                names.append(m.group(1).strip())
    except (OSError, UnicodeDecodeError):
        pass
    return names


def _extract_name_candidates(text: str, canonical_names: list[str]) -> list[str]:
    """Find tokens in text that could be character name variants.

    For each canonical name of length N we extract every N-length sliding window
    of Chinese characters from contiguous Chinese runs in the text.
    """
    candidates: set[str] = set()
    # All contiguous Chinese-character runs
    runs = re.findall(r"[\u4e00-\u9fff]+", text)
    for canonical in canonical_names:
        length = len(canonical)
        for run in runs:
            # Sliding window of exactly canonical length
            for i in range(len(run) - length + 1):
                window = run[i: i + length]
                candidates.add(window)
    return list(candidates)


def _edit_distance_one(a: str, b: str) -> bool:
    """Return True if strings differ by exactly one character substitution.

    Handles same-length strings only (single-char substitution check).
    For Chinese names, a common typo is one character being different.
    """
    if len(a) != len(b):
        return False
    diffs = sum(ca != cb for ca, cb in zip(a, b))
    return diffs == 1


def _extract_quoted_keywords(text: str) -> list[str]:
    """Extract text enclosed in 「」 brackets from a string."""
    return re.findall(r"「(.+?)」", text)
