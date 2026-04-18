"""Step completion detection via file markers.

Scans project files for <!-- STEP_COMPLETE --> markers and reconciles
against pipeline-status.md. File markers are the truth source.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from harness.state import read_pipeline_status, write_pipeline_status

COMPLETE_MARKER = "<!-- STEP_COMPLETE -->"

# Known file paths for each global step (relative to project root)
GLOBAL_STEP_FILES: dict[str, str] = {
    "script-analysis": "剧本分析.md",
    "extract": "素材提取/角色表.md",
    "episode-split": "集拆分.md",
}

# Known file patterns for per-episode steps
EPISODE_STEP_PATTERNS: dict[str, str] = {
    "screenplay": "剧本/EP{ep}_剧本.md",
    "storyboard": "分镜设计/EP{ep}_分镜.md",
    "video-prompt": "视频提示词/EP{ep}_提示词.md",
    "dialogue-script": "台词本/EP{ep}_台词本.md",
    "music-prompt": "音乐提示词/EP{ep}_音乐.md",
}


def check_step_complete(file_path: Path) -> bool:
    """Check if a file contains the STEP_COMPLETE marker.

    Returns False for non-existent files.
    """
    if not file_path.exists():
        return False
    try:
        text = file_path.read_text(encoding="utf-8")
        return COMPLETE_MARKER in text
    except (OSError, UnicodeDecodeError):
        return False


def _discover_episodes(project_dir: Path) -> list[str]:
    """Discover which episodes exist by scanning 剧本/ directory."""
    screenplay_dir = project_dir / "剧本"
    if not screenplay_dir.exists():
        return []

    episodes: list[str] = []
    for f in sorted(screenplay_dir.glob("EP*_剧本.md")):
        name = f.stem  # EP01_剧本
        ep = name.split("_")[0]  # EP01
        episodes.append(ep)
    return episodes


def scan_project_completion(project_dir: Path) -> dict[str, Any]:
    """Scan project files for STEP_COMPLETE markers.

    Returns status dict in same format as read_pipeline_status().
    """
    result: dict[str, Any] = {"global": {}, "episodes": {}}

    for step, rel_path in GLOBAL_STEP_FILES.items():
        fpath = project_dir / rel_path
        if fpath.exists():
            if check_step_complete(fpath):
                result["global"][step] = "complete"
            else:
                result["global"][step] = "in-progress"
        else:
            result["global"][step] = "not-started"

    episodes = _discover_episodes(project_dir)
    if not episodes:
        try:
            current = read_pipeline_status(project_dir)
            for step_eps in current.get("episodes", {}).values():
                episodes = sorted(set(episodes) | set(step_eps.keys()))
        except FileNotFoundError:
            pass

    for step, pattern in EPISODE_STEP_PATTERNS.items():
        result["episodes"][step] = {}
        for ep in episodes:
            # Normalize: "EP01" → "01", "EP1" → "01"
            ep_num = ep.replace("EP", "").zfill(2)
            fpath = project_dir / pattern.format(ep=ep_num)

            if fpath.exists():
                if check_step_complete(fpath):
                    result["episodes"][step][ep] = "complete"
                else:
                    result["episodes"][step][ep] = "in-progress"
            else:
                result["episodes"][step][ep] = "not-started"

    return result


def reconcile_status(project_dir: Path) -> list[str]:
    """Compare pipeline-status.md with actual file markers.

    File markers are the truth source. Updates pipeline-status.md
    to match and returns list of discrepancies found.
    """
    discrepancies: list[str] = []

    try:
        recorded = read_pipeline_status(project_dir)
    except FileNotFoundError:
        discrepancies.append("pipeline-status.md not found, creating from scan")
        actual = scan_project_completion(project_dir)
        write_pipeline_status(project_dir, actual)
        return discrepancies

    actual = scan_project_completion(project_dir)
    needs_update = False

    for step in set(recorded["global"]) | set(actual["global"]):
        rec = recorded["global"].get(step, "not-started")
        act = actual["global"].get(step, "not-started")
        if rec != act:
            discrepancies.append(
                f"{step}: status={rec} but marker={act}"
            )
            needs_update = True

    for step in set(recorded.get("episodes", {})) | set(
        actual.get("episodes", {})
    ):
        rec_eps = recorded.get("episodes", {}).get(step, {})
        act_eps = actual.get("episodes", {}).get(step, {})
        for ep in set(rec_eps) | set(act_eps):
            rec = rec_eps.get(ep, "not-started")
            act = act_eps.get(ep, "not-started")
            if rec != act:
                discrepancies.append(
                    f"{step}.{ep}: status={rec} but marker={act}"
                )
                needs_update = True

    if needs_update:
        merged = {
            "global": {**recorded["global"], **actual["global"]},
            "episodes": {},
        }
        for step in set(recorded.get("episodes", {})) | set(
            actual.get("episodes", {})
        ):
            merged["episodes"][step] = {
                **recorded.get("episodes", {}).get(step, {}),
                **actual.get("episodes", {}).get(step, {}),
            }
        write_pipeline_status(project_dir, merged)

    return discrepancies
