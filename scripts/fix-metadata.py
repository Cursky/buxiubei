#!/usr/bin/env python3
"""重刷视频提示词中 景别 / 运镜 / 对话 元数据（在已规整成 ### V01 格式后使用）。

抽取逻辑：
- 景别：每个 `镜头N：` 后、首个 `。` 前的第一个逗号段
- 运镜：同一段的第二个逗号段（如无则留空）
- 对话：扫描 `> 角色 说：` 的角色名，去重保序
"""
import re
import sys
from pathlib import Path

V_BLOCK_PAT = re.compile(
    r'(### V(\d+) \| [^\n]+\n\n'
    r'\*\*场景\*\*：[^\n]+\n)'
    r'\*\*景别\*\*：[^\n]*\| \*\*运镜\*\*：[^\n]*\n'
    r'(\*\*素材引用\*\*：[^\n]+\n)'
    r'\*\*对话\*\*：[^\n]*\n\n'
    r'(\*\*提示词\*\*：\n\n'
    r'(> [\s\S]*?))'
    r'(?=\n---|\Z)',
)

SHOT_PAT = re.compile(r'镜头\s*(\d+)：([^。\n]+)。')
DIALOG_PAT = re.compile(r'>\s*([^（\n]+?)(?:（[^）]*）)?\s*说：')


def extract_metadata(body: str):
    shots = SHOT_PAT.findall(body)
    jings, yuns = [], []
    for _num, head in shots:
        parts = [p.strip() for p in head.split('，', 1)]
        jings.append(parts[0])
        yuns.append(parts[1] if len(parts) > 1 else '')
    speakers = []
    for m in DIALOG_PAT.finditer(body):
        name = m.group(1).strip()
        if name and name not in speakers:
            speakers.append(name)
    return '→'.join(jings), '→'.join(yuns), ('、'.join(speakers) if speakers else '（无）')


def replace(match: re.Match) -> str:
    head = match.group(1)
    mat = match.group(3)
    body_section = match.group(4)
    body = match.group(5)
    jing, yun, dialog = extract_metadata(body)
    return (
        f'{head}'
        f'**景别**：{jing} | **运镜**：{yun}\n'
        f'{mat}'
        f'**对话**：{dialog}\n\n'
        f'{body_section}'
    )


def process(path: Path) -> bool:
    text = path.read_text(encoding='utf-8')
    updated = V_BLOCK_PAT.sub(replace, text)
    if updated == text:
        print(f'unchanged: {path}')
        return False
    path.write_text(updated, encoding='utf-8')
    print(f'fixed: {path}')
    return True


def main() -> int:
    root = Path('视频提示词')
    for p in sorted(root.glob('EP*_提示词.md')):
        process(p)
    return 0


if __name__ == '__main__':
    sys.exit(main())
