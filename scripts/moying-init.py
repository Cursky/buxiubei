#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
moying-init.py — MoYing 项目初始化脚本

从小说文件或已拆分剧本创建标准项目目录结构。

用法：
    python moying-init.py <source> [--output <dir>]

    source: 小说 .txt 文件 或 已拆分的剧本目录
    --output: 项目输出目录（默认: 当前目录/项目名）

退出码：
    0 = 成功
    1 = 用户错误（参数错误、文件不存在）
    2 = 系统错误（IO 失败、编码无法识别）
"""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple


# ── 编码检测 ──────────────────────────────────────────────

ENCODINGS = ["utf-8", "gbk", "gb2312", "gb18030"]


def detect_encoding(file_path: Path) -> str:
    """检测文件编码，按优先级尝试 UTF-8 → GBK → GB2312 → GB18030。"""
    for enc in ENCODINGS:
        try:
            with open(file_path, "r", encoding=enc) as f:
                f.read()
            return enc
        except (UnicodeDecodeError, LookupError):
            continue
    print(f"⚠️  无法确定编码，使用 UTF-8（忽略错误字符）: {file_path.name}", file=sys.stderr)
    return "utf-8"  # fallback with errors='ignore'


def read_file(file_path: Path) -> Tuple[str, List[str]]:
    """读取文件并返回 (encoding, lines)。"""
    encoding = detect_encoding(file_path)
    with open(file_path, "r", encoding=encoding, errors="ignore") as f:
        lines = f.readlines()
    return encoding, lines


# ── 章节拆分 ──────────────────────────────────────────────

CHAPTER_PATTERNS = [
    # 第X章 / 第XX章（中文数字和阿拉伯数字）
    r"^第[一二三四五六七八九十百千零\d]+章.*$",
    # Chapter X / CHAPTER X
    r"^(?:Chapter|CHAPTER|chapter)\s*\d+.*$",
    # 第X回 / 第XX回
    r"^第[一二三四五六七八九十百千零\d]+回.*$",
    # 数字 + 章/回/节
    r"^\d+[.、\s]*[章回节].*$",
    # 宽松匹配（必须以"第"开头）
    r"^第\s*\d+\s*[章回节]\s.*$",
]


def is_chapter_title(line: str) -> bool:
    """判断一行是否为章节标题。"""
    stripped = line.strip()
    if not stripped:
        return False
    return any(re.match(p, stripped, re.IGNORECASE) for p in CHAPTER_PATTERNS)


def split_chapters(lines: List[str]) -> List[dict]:
    """将文本按章节拆分，返回章节列表。

    每个章节: {"number": int, "title": str, "content": str}
    """
    chapters: List[dict] = []
    current_title: Optional[str] = None
    current_lines: List[str] = []

    for line in lines:
        if is_chapter_title(line):
            if current_title is not None:
                chapters.append({
                    "number": len(chapters) + 1,
                    "title": current_title,
                    "content": "".join(current_lines).strip(),
                })
            current_title = line.strip()
            current_lines = []
        elif current_title is not None:
            current_lines.append(line)

    # 最后一章
    if current_title is not None:
        chapters.append({
            "number": len(chapters) + 1,
            "title": current_title,
            "content": "".join(current_lines).strip(),
        })

    return chapters


# ── 剧本检测 ──────────────────────────────────────────────

SCENE_HEADER_RE = re.compile(r"^\d+-\d+\s+(?:日|夜)")


def is_screenplay_file(file_path: Path) -> bool:
    """检测文件是否为已拆分的剧本（包含场景头 X-X 日/夜）。"""
    try:
        _, lines = read_file(file_path)
        return any(SCENE_HEADER_RE.match(line.strip()) for line in lines[:100])
    except Exception:
        return False


def is_screenplay_dir(dir_path: Path) -> bool:
    """检测目录是否包含剧本文件。"""
    md_files = list(dir_path.glob("*.md")) + list(dir_path.glob("*.txt"))
    if not md_files:
        return False
    # 至少一个文件包含场景头
    return any(is_screenplay_file(f) for f in md_files[:10])


# ── 目录创建 ──────────────────────────────────────────────

PROJECT_DIRS = [
    "源文件",
    "剧本",
    "素材提取",
    "分镜设计",
    "视频提示词",
    "台词本",
    "音乐提示词",
]


def create_project_structure(project_dir: Path) -> None:
    """创建扁平化项目目录结构。"""
    project_dir.mkdir(parents=True, exist_ok=True)
    for d in PROJECT_DIRS:
        (project_dir / d).mkdir(exist_ok=True)

    # 画风设定.md 占位
    style_file = project_dir / "画风设定.md"
    if not style_file.exists():
        style_file.write_text(
            "# 画风设定\n\n"
            "**画风类型**: （待确认，运行 /moying 设定）\n"
            "**画幅**: 16:9\n"
            "**画风前缀**:\n"
            "> （待填写）\n",
            encoding="utf-8",
        )


def init_pipeline_status(project_dir: Path, project_name: str) -> None:
    """创建初始 pipeline-status.md。"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    content = f"""# Pipeline Status

**项目**: {project_name}
**创建时间**: {now}
**最后更新**: {now}

## 全局步骤

| 步骤 | 状态 | 更新时间 |
|------|------|---------|
| script-analysis | not-started | {now} |
| extract | not-started | {now} |
| episode-split | not-started | {now} |

## 按集步骤

| 步骤 | EP01 |
|------|------|
| screenplay | not-started |
| storyboard | not-started |
| video-prompt | not-started |
| dialogue-script | not-started |
| music-prompt | not-started |
"""
    (project_dir / "pipeline-status.md").write_text(content, encoding="utf-8")


# ── 文件名清理 ────────────────────────────────────────────

def sanitize_filename(title: str, max_length: int = 50) -> str:
    """移除文件名非法字符。"""
    cleaned = re.sub(r'[<>:"/\\|?*]', "", title)
    return cleaned[:max_length].strip()


# ── 主流程 ────────────────────────────────────────────────

def init_from_novel(source: Path, project_dir: Path) -> None:
    """从小说文件初始化项目。"""
    print(f"📖 读取小说: {source.name}")
    encoding, lines = read_file(source)
    print(f"   编码: {encoding}, 总行数: {len(lines)}")

    chapters = split_chapters(lines)
    if not chapters:
        print("⚠️  未检测到章节结构，将整个文件作为单章节处理")
        full_text = "".join(lines).strip()
        chapters = [{"number": 1, "title": source.stem, "content": full_text}]

    print(f"   章节数: {len(chapters)}")

    # 创建项目结构
    create_project_structure(project_dir)
    project_name = project_dir.name
    init_pipeline_status(project_dir, project_name)

    # 写入源文件
    source_dir = project_dir / "源文件"
    for ch in chapters:
        filename = f"{ch['number']:03d}_{sanitize_filename(ch['title'])}.txt"
        (source_dir / filename).write_text(
            f"{ch['title']}\n\n{ch['content']}", encoding="utf-8"
        )

    total_chars = sum(len(ch["content"]) for ch in chapters)
    print(f"✅ 项目已创建: {project_dir}")
    print(f"   {len(chapters)} 个章节, 共 {total_chars} 字符")
    print(f"   下一步: cd {project_dir} && 运行 /moying")


def init_from_screenplay(source: Path, project_dir: Path) -> None:
    """从剧本目录/文件初始化项目。"""
    print(f"🎬 检测到剧本格式: {source}")

    create_project_structure(project_dir)
    project_name = project_dir.name
    init_pipeline_status(project_dir, project_name)

    screenplay_dir = project_dir / "剧本"
    copied = 0

    if source.is_dir():
        for f in sorted(source.iterdir()):
            if f.suffix in (".md", ".txt") and f.is_file():
                dest = screenplay_dir / f.name
                _, lines = read_file(f)
                dest.write_text("".join(lines), encoding="utf-8")
                copied += 1
    else:
        dest = screenplay_dir / source.name
        _, lines = read_file(source)
        dest.write_text("".join(lines), encoding="utf-8")
        copied = 1

    print(f"✅ 项目已创建: {project_dir}")
    print(f"   {copied} 个剧本文件已导入到 剧本/")
    print(f"   下一步: cd {project_dir} && 运行 /moying")


def scaffold_only(project_dir: Path) -> None:
    """Create project directory structure without processing any source files."""
    create_project_structure(project_dir)
    project_name = project_dir.name
    if not (project_dir / "pipeline-status.md").exists():
        init_pipeline_status(project_dir, project_name)
    print(f"✅ 项目目录结构已创建: {project_dir}")


def scan_source_files(project_dir: Path) -> None:
    """List files in 源文件/ directory as JSON."""
    import json

    source_dir = project_dir / "源文件"
    if not source_dir.exists():
        print(json.dumps({"files": [], "count": 0}, ensure_ascii=False))
        return

    files = []
    for f in sorted(source_dir.iterdir()):
        if f.is_file() and f.suffix in (".txt", ".md"):
            is_script = is_screenplay_file(f)
            files.append({
                "name": f.name,
                "size": f.stat().st_size,
                "type": "screenplay" if is_script else "novel_chapter",
            })

    print(json.dumps({"files": files, "count": len(files)}, ensure_ascii=False))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="MoYing 项目初始化 — 从小说或剧本创建标准项目目录",
        epilog="示例: python moying-init.py 我的小说.txt --output 我的项目/",
    )
    parser.add_argument("source", nargs="?", help="小说 .txt 文件 或 已拆分的剧本目录")
    parser.add_argument("--output", "-o", help="项目输出目录（默认：基于源文件名或当前目录）")
    parser.add_argument("--scaffold-only", action="store_true",
                        help="仅创建目录结构，不处理源文件")
    parser.add_argument("--scan", action="store_true",
                        help="扫描 源文件/ 目录并输出文件列表（JSON）")
    args = parser.parse_args()

    # Determine project directory
    if args.output:
        project_dir = Path(args.output).resolve()
    elif args.source:
        project_dir = Path.cwd() / Path(args.source).stem
    else:
        project_dir = Path.cwd()

    if args.scaffold_only:
        try:
            scaffold_only(project_dir)
            return 0
        except Exception as e:
            print(f"❌ 系统错误: {e}", file=sys.stderr)
            return 2

    if args.scan:
        try:
            scan_source_files(project_dir)
            return 0
        except Exception as e:
            print(f"❌ 系统错误: {e}", file=sys.stderr)
            return 2

    if not args.source:
        parser.error("source 参数是必需的（除非使用 --scaffold-only 或 --scan）")

    source = Path(args.source).resolve()
    if not source.exists():
        print(f"❌ 源文件/目录不存在: {args.source}", file=sys.stderr)
        return 1

    try:
        if source.is_dir():
            if is_screenplay_dir(source):
                init_from_screenplay(source, project_dir)
            else:
                print(f"❌ 目录中未检测到剧本文件: {source}", file=sys.stderr)
                return 1
        elif source.is_file():
            if is_screenplay_file(source):
                init_from_screenplay(source, project_dir)
            else:
                init_from_novel(source, project_dir)
        else:
            print(f"❌ 不支持的源类型: {source}", file=sys.stderr)
            return 1
    except Exception as e:
        print(f"❌ 系统错误: {e}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
