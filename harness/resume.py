"""Pipeline resume context generation.

Builds a comprehensive status summary for AI assistants to read
at session start, enabling context-free resume of interrupted work.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from harness.completion import reconcile_status
from harness.state import read_pipeline_status
from harness.status_report import format_status_table, suggest_next_step


def generate_resume_context(project_dir: Path) -> str:
    """Generate a full resume context for the current project.

    Steps:
    1. Reconcile pipeline-status.md with actual file markers
    2. Read reconciled status
    3. Format status report with emoji indicators
    4. Include active constraints count
    5. Suggest next step
    6. Return formatted Markdown summary
    """
    discrepancies = reconcile_status(project_dir)

    try:
        status = read_pipeline_status(project_dir)
    except FileNotFoundError:
        return _no_project_message(project_dir)

    lines = [
        "## 项目状态摘要\n",
        f"**项目**: {project_dir.name}",
        f"**查询时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n",
    ]

    if discrepancies:
        lines.append("### 状态校正")
        lines.append("以下状态与文件实际标记不一致，已自动修正：")
        for d in discrepancies:
            lines.append(f"- ⚠️ {d}")
        lines.append("")

    status_table = format_status_table(status)
    if status_table.strip():
        lines.append(status_table)

    # Include active constraints summary
    try:
        from harness.constraints import load_constraints

        constraints = load_constraints(project_dir)
        active = [c for c in constraints if c.status == "active"]
        if active:
            lines.append(f"### 活跃约束 ({len(active)}条)")
            for c in active:
                lines.append(f"- [{c.id}] {c.description}")
            lines.append("")
    except FileNotFoundError:
        pass  # constraints.md does not exist yet
    except Exception as e:
        lines.append(f"### 约束加载警告\n⚠️ 读取约束文件失败: {e}\n")

    next_cmd = suggest_next_step(status)
    if next_cmd:
        lines.append("### 建议下一步")
        lines.append(f"➡️ `{next_cmd}`\n")
    else:
        lines.append("### 状态")
        lines.append("✅ 所有步骤已完成！\n")

    return "\n".join(lines)


def _no_project_message(project_dir: Path) -> str:
    """Return message when no pipeline-status.md exists."""
    return (
        "## 项目状态摘要\n\n"
        f"**项目**: {project_dir.name}\n\n"
        "⚠️ 未找到 pipeline-status.md。\n"
        "请先运行 CLI 初始化脚本创建项目结构，"
        "或使用 `/moying` 开始项目初始化。\n"
    )
