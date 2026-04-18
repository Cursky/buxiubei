"""Format pipeline status as human-readable reports.

Generates Markdown status tables and next-step recommendations.
"""

from __future__ import annotations

from typing import Any

# Pipeline step order for recommendation logic
STEP_ORDER = [
    "script-analysis",
    "extract",
    "episode-split",
    "screenplay",
    "storyboard",
    "video-prompt",
    "dialogue-script",
    "music-prompt",
]

GLOBAL_STEPS = {"script-analysis", "extract", "episode-split"}
EMOJI = {"complete": "✅", "in-progress": "🔄", "not-started": "⬜"}


def format_status_table(status: dict[str, Any]) -> str:
    """Render pipeline status as a readable Markdown report."""
    lines: list[str] = []

    global_data = status.get("global", {})
    if global_data:
        lines.append("### 全局步骤")
        for step in STEP_ORDER:
            if step in global_data:
                st = global_data[step]
                lines.append(f"- {EMOJI.get(st, '❓')} {step}: {st}")
        lines.append("")

    episodes_data = status.get("episodes", {})
    if episodes_data:
        all_eps: set[str] = set()
        for step_eps in episodes_data.values():
            all_eps.update(step_eps.keys())
        eps_sorted = sorted(all_eps)

        if eps_sorted:
            lines.append("### 按集步骤")
            for step in STEP_ORDER:
                if step not in episodes_data:
                    continue
                ep_map = episodes_data[step]
                statuses = [ep_map.get(ep, "not-started") for ep in eps_sorted]
                complete = [s for s in statuses if s == "complete"]
                in_prog = [s for s in statuses if s == "in-progress"]

                if len(complete) == len(eps_sorted):
                    lines.append(f"- ✅ {step}: 全部完成 ({len(eps_sorted)}集)")
                elif in_prog:
                    ip_eps = [
                        ep
                        for ep in eps_sorted
                        if ep_map.get(ep) == "in-progress"
                    ]
                    lines.append(
                        f"- 🔄 {step}: {len(complete)}/{len(eps_sorted)}集完成"
                        f", {', '.join(ip_eps)} 进行中"
                    )
                elif complete:
                    done_eps = sorted(
                        ep
                        for ep in eps_sorted
                        if ep_map.get(ep) == "complete"
                    )
                    rng = _format_ep_range(done_eps)
                    lines.append(
                        f"- ⬜ {step}: {rng} 已完成"
                        f", 剩余 {len(eps_sorted) - len(complete)}集"
                    )
                else:
                    lines.append(f"- ⬜ {step}: 未开始")
            lines.append("")

    return "\n".join(lines)


def suggest_next_step(status: dict[str, Any]) -> str | None:
    """Determine the next recommended slash command.

    Returns a string like "/screenplay EP04" or None if all done.
    """
    global_data = status.get("global", {})
    for step in STEP_ORDER:
        if step in GLOBAL_STEPS:
            st = global_data.get(step, "not-started")
            if st == "in-progress":
                return f"/{step} (继续)"
            if st == "not-started":
                return f"/{step}"

    episodes_data = status.get("episodes", {})
    for step in STEP_ORDER:
        if step in GLOBAL_STEPS or step not in episodes_data:
            continue

        ep_map = episodes_data[step]
        for ep in sorted(ep_map.keys()):
            st = ep_map[ep]
            if st == "in-progress":
                return f"/{step} {ep} (继续)"
            if st == "not-started":
                return f"/{step} {ep}"

    return None


def _format_ep_range(eps: list[str]) -> str:
    """Format episode list, using range for contiguous or comma-separated."""
    if not eps:
        return ""
    if len(eps) == 1:
        return eps[0]
    # Check if contiguous by comparing numeric parts
    try:
        nums = [int(ep.replace("EP", "")) for ep in eps]
        if nums == list(range(nums[0], nums[-1] + 1)):
            return f"{eps[0]}-{eps[-1]}"
    except ValueError:
        pass
    if len(eps) <= 5:
        return ", ".join(eps)
    return f"{eps[0]}, {eps[1]}, ... {eps[-1]} ({len(eps)}集)"
