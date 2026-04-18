"""harness/plugins.py — Plugin management for MoYing optimization skills.

Handles scanning, registering, enabling, and loading plugin knowledge
from SKILL.md files that contain PLUGIN-META and OPT-KNOWLEDGE markers.
"""

import json
import os
import re
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

from harness.paths import MOYING_HOME_ENV, get_moying_home  # re-exported

__all_reexports__ = ("MOYING_HOME_ENV", "get_moying_home")

PLUGIN_META_RE = re.compile(
    r"<!--\s*PLUGIN-META\s*\n(.*?)\n\s*-->", re.DOTALL
)
OPT_KNOWLEDGE_RE = re.compile(
    r"<!--\s*OPT-KNOWLEDGE-START\s*-->\s*\n(.*?)\n\s*<!--\s*OPT-KNOWLEDGE-END\s*-->",
    re.DOTALL,
)


@dataclass
class PluginInfo:
    name: str
    type: str = "optimization"
    trigger: str = ""
    scope: str = ""
    status: str = "available"
    knowledge: str = ""


# ── SKILL.md parsing ─────────────────────────────────────────


def parse_plugin_meta(content: str) -> Optional[dict]:
    """Parse PLUGIN-META block from SKILL.md content.

    Returns dict with type/trigger/scope keys, or None if no marker found.
    """
    m = PLUGIN_META_RE.search(content)
    if not m:
        return None
    meta: Dict[str, str] = {}
    for line in m.group(1).strip().splitlines():
        if ":" in line:
            key, val = line.split(":", 1)
            meta[key.strip()] = val.strip()
    return meta


def extract_knowledge(content: str) -> str:
    """Extract OPT-KNOWLEDGE region from SKILL.md content."""
    m = OPT_KNOWLEDGE_RE.search(content)
    return m.group(1).strip() if m else ""


# ── Scanning ─────────────────────────────────────────────────


def scan_plugins(skills_dir: Path) -> List[PluginInfo]:
    """Scan a skills directory for SKILL.md files containing PLUGIN-META."""
    plugins: List[PluginInfo] = []
    if not skills_dir.is_dir():
        return plugins
    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            continue
        content = skill_file.read_text(encoding="utf-8")
        meta = parse_plugin_meta(content)
        if meta:
            plugins.append(
                PluginInfo(
                    name=skill_dir.name,
                    type=meta.get("type", "optimization"),
                    trigger=meta.get("trigger", ""),
                    scope=meta.get("scope", ""),
                )
            )
    return plugins


def is_plugin_skill(skill_dir: Path) -> bool:
    """Check if a skill directory contains a plugin (has PLUGIN-META).

    Uses the full multi-line PLUGIN_META_RE so that documentation that
    *mentions* the `<!-- PLUGIN-META ... -->` marker inline (e.g.
    moying-agent describing the plugin convention) is not mis-detected
    as a plugin itself.
    """
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.exists():
        return False
    content = skill_file.read_text(encoding="utf-8")
    return PLUGIN_META_RE.search(content) is not None


# ── Registry (global) ────────────────────────────────────────


def write_registry(registry_path: Path, plugins: List[PluginInfo]) -> None:
    """Write plugins/registry.md as a Markdown table."""
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# 可用插件\n",
        "",
        "| 名称 | 类型 | 触发条件 | 应用范围 |",
        "|------|------|---------|---------|",
    ]
    for p in plugins:
        lines.append(f"| {p.name} | {p.type} | {p.trigger} | {p.scope} |")
    lines.append("")
    registry_path.write_text("\n".join(lines), encoding="utf-8")


def read_registry(registry_path: Path) -> List[PluginInfo]:
    """Read plugins/registry.md and return plugin list."""
    if not registry_path.exists():
        return []
    content = registry_path.read_text(encoding="utf-8")
    plugins: List[PluginInfo] = []
    for line in content.splitlines():
        line = line.strip()
        if not line.startswith("|") or line.startswith("| 名称") or line.startswith("|--"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 5:
            plugins.append(
                PluginInfo(
                    name=parts[1],
                    type=parts[2],
                    trigger=parts[3],
                    scope=parts[4],
                )
            )
    return plugins


# ── Project-level plugin management ──────────────────────────


def read_enabled_plugins(harness_dir: Path) -> List[str]:
    """Read .harness/plugins.md — return names where status is 'active'."""
    plugins_file = Path(harness_dir) / "plugins.md"
    if not plugins_file.exists():
        return []
    content = plugins_file.read_text(encoding="utf-8")
    names: List[str] = []
    for line in content.splitlines():
        if "| active |" not in line:
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 4 and parts[1]:
            names.append(parts[1])
    return names


def _ensure_plugins_md(harness_dir: Path) -> Path:
    """Ensure .harness/plugins.md exists with table header."""
    plugins_file = Path(harness_dir) / "plugins.md"
    if not plugins_file.exists():
        plugins_file.write_text(
            "# 已启用插件\n\n"
            "| 插件 | 类型 | 状态 | 启用时间 |\n"
            "|------|------|------|---------|\n",
            encoding="utf-8",
        )
    return plugins_file


def enable_plugin(
    plugin_name: str,
    harness_dir: Union[str, Path],
    commands_dir: Union[str, Path],
) -> bool:
    """Enable a plugin: copy from ~/.moying/skills/ to commands_dir, register in plugins.md.

    Returns True on success, False if plugin not found.
    """
    harness_dir = Path(harness_dir)
    commands_dir = Path(commands_dir)
    moying_home = get_moying_home()
    src = moying_home / "skills" / plugin_name

    if not src.is_dir():
        return False

    # Copy skill to project commands
    dst = commands_dir / plugin_name
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)

    # Read PLUGIN-META for type info
    skill_file = src / "SKILL.md"
    plugin_type = "optimization"
    if skill_file.exists():
        meta = parse_plugin_meta(skill_file.read_text(encoding="utf-8"))
        if meta:
            plugin_type = meta.get("type", "optimization")

    # Register in .harness/plugins.md
    plugins_file = _ensure_plugins_md(harness_dir)
    content = plugins_file.read_text(encoding="utf-8")

    # Check if already registered
    if f"| {plugin_name} |" in content:
        # Update status to active
        lines = content.splitlines()
        new_lines = []
        for line in lines:
            if f"| {plugin_name} |" in line:
                today = datetime.now().strftime("%Y-%m-%d")
                line = f"| {plugin_name} | {plugin_type} | active | {today} |"
            new_lines.append(line)
        plugins_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    else:
        # Append new row
        today = datetime.now().strftime("%Y-%m-%d")
        row = f"| {plugin_name} | {plugin_type} | active | {today} |\n"
        with open(plugins_file, "a", encoding="utf-8") as f:
            f.write(row)

    return True


def disable_plugin(plugin_name: str, harness_dir: Union[str, Path]) -> bool:
    """Mark a plugin as inactive in .harness/plugins.md."""
    plugins_file = Path(harness_dir) / "plugins.md"
    if not plugins_file.exists():
        return False
    content = plugins_file.read_text(encoding="utf-8")
    if f"| {plugin_name} |" not in content:
        return False
    lines = content.splitlines()
    new_lines = []
    for line in lines:
        if f"| {plugin_name} |" in line:
            line = line.replace("| active |", "| inactive |")
        new_lines.append(line)
    plugins_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    return True


# ── Knowledge loading ────────────────────────────────────────


def load_active_knowledge(
    harness_dir: Union[str, Path],
    commands_dir: Union[str, Path],
    plugin_type: Optional[str] = None,
) -> List[dict]:
    """Load metadata + knowledge for all active plugins.

    Args:
        harness_dir: Path to .harness/ directory.
        commands_dir: Path to .claude/commands/ directory.
        plugin_type: If specified, only return plugins matching this type
                     (e.g., "optimization"). None returns all types.

    Returns list of dicts: [{name, type, trigger, scope, knowledge}, ...]
    """
    harness_dir = Path(harness_dir)
    commands_dir = Path(commands_dir)
    enabled = read_enabled_plugins(harness_dir)
    results: List[dict] = []
    for name in enabled:
        skill_file = commands_dir / name / "SKILL.md"
        if not skill_file.exists():
            continue
        content = skill_file.read_text(encoding="utf-8")
        meta = parse_plugin_meta(content)
        if not meta:
            continue
        if plugin_type and meta.get("type", "") != plugin_type:
            continue
        results.append(
            {
                "name": name,
                "type": meta.get("type", ""),
                "trigger": meta.get("trigger", ""),
                "scope": meta.get("scope", ""),
                "knowledge": extract_knowledge(content),
            }
        )
    return results


def load_active_meta(
    harness_dir: Union[str, Path],
    commands_dir: Union[str, Path],
    plugin_type: Optional[str] = None,
) -> List[dict]:
    """Load metadata only (no knowledge) for all active plugins."""
    results = load_active_knowledge(harness_dir, commands_dir, plugin_type)
    for r in results:
        r.pop("knowledge", None)
    return results


# ── Global memory ────────────────────────────────────────────


def check_global_memory() -> dict:
    """Check if global memory has content."""
    gm = get_moying_home() / "global-memory"
    result = {"has_clarifications": False, "has_constitution": False}
    for key, filename in [
        ("has_clarifications", "clarifications.md"),
        ("has_constitution", "constitution.md"),
    ]:
        f = gm / filename
        result[key] = f.exists() and f.stat().st_size > 50
    return result


def save_global_memory(content: str, memory_type: str = "clarification") -> None:
    """Append content to ~/.moying/global-memory/{type}s.md."""
    gm = get_moying_home() / "global-memory"
    gm.mkdir(parents=True, exist_ok=True)
    target = gm / f"{memory_type}s.md"
    today = datetime.now().strftime("%Y-%m-%d")
    entry = f"\n- [{today}] {content}\n"
    with open(target, "a", encoding="utf-8") as f:
        f.write(entry)


def load_global_memory(
    harness_dir: Union[str, Path],
    memory_type: str = "clarification",
) -> bool:
    """Merge global memory into project .harness/ file.

    Returns True if content was merged, False if no global memory.
    """
    gm = get_moying_home() / "global-memory"
    source = gm / f"{memory_type}s.md"
    if not source.exists() or source.stat().st_size < 10:
        return False

    harness_dir = Path(harness_dir)
    target_name = (
        "clarifications.md" if memory_type == "clarification" else "constitution.md"
    )
    target = harness_dir / target_name
    global_content = source.read_text(encoding="utf-8").strip()

    if target.exists():
        existing = target.read_text(encoding="utf-8")
        if "## 全局记忆（从 ~/.moying/ 加载）" in existing:
            return False  # Already merged (check section header, not content)
        with open(target, "a", encoding="utf-8") as f:
            f.write(f"\n\n## 全局记忆（从 ~/.moying/ 加载）\n\n{global_content}\n")
    else:
        target.write_text(
            f"# {target_name.replace('.md', '').title()}\n\n"
            f"## 全局记忆（从 ~/.moying/ 加载）\n\n{global_content}\n",
            encoding="utf-8",
        )
    return True


# ── CLI JSON helpers ─────────────────────────────────────────


def _find_project_root() -> Path:
    """Walk upward from CWD to find directory containing .harness/."""
    d = Path.cwd().resolve()
    while True:
        if (d / ".harness").is_dir():
            return d
        parent = d.parent
        if parent == d:
            break
        d = parent
    return Path.cwd()  # fallback to CWD


def _cli_list_available() -> str:
    """JSON output for --list-available."""
    moying_home = get_moying_home()
    registry = moying_home / "plugins" / "registry.md"
    if registry.exists():
        plugins = read_registry(registry)
    else:
        plugins = scan_plugins(moying_home / "skills")
    return json.dumps(
        [asdict(p) for p in plugins], ensure_ascii=False, indent=2
    )


def _cli_list_enabled() -> str:
    """JSON output for --list-enabled."""
    root = _find_project_root()
    harness_dir = root / ".harness"
    if not harness_dir.exists():
        return json.dumps([], ensure_ascii=False)
    enabled = read_enabled_plugins(harness_dir)
    commands_dir = root / ".claude" / "commands"
    results = []
    for name in enabled:
        skill_file = commands_dir / name / "SKILL.md"
        info = {"name": name, "type": "unknown", "status": "active"}
        if skill_file.exists():
            meta = parse_plugin_meta(skill_file.read_text(encoding="utf-8"))
            if meta:
                info["type"] = meta.get("type", "unknown")
        results.append(info)
    return json.dumps(results, ensure_ascii=False, indent=2)


def _cli_load_knowledge() -> str:
    """JSON output for --load-knowledge.

    Supports MOYING_PLUGIN_TYPE env var for type filtering.
    E.g., MOYING_PLUGIN_TYPE=optimization filters out workflow plugins.
    """
    root = _find_project_root()
    plugin_type = os.environ.get("MOYING_PLUGIN_TYPE")
    results = load_active_knowledge(
        root / ".harness", root / ".claude" / "commands", plugin_type
    )
    return json.dumps({"plugins": results}, ensure_ascii=False, indent=2)


def _cli_load_meta() -> str:
    """JSON output for --load-meta.

    Supports MOYING_PLUGIN_TYPE env var for type filtering.
    """
    root = _find_project_root()
    plugin_type = os.environ.get("MOYING_PLUGIN_TYPE")
    results = load_active_meta(
        root / ".harness", root / ".claude" / "commands", plugin_type
    )
    return json.dumps({"plugins": results}, ensure_ascii=False, indent=2)
