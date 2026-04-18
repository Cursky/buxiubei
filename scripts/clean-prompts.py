#!/usr/bin/env python3
"""清理三集视频提示词：
1. 提示词内容最前面加 EP{NN}-V{NN} 标识
2. 删除 （参考 `角色图/...`, ...） 引用路径
3. 删除 （DOTA2 官方...） 等英雄/技能描述
4. 删除 （...状态...） 角色状态描述
5. 删除 （依据...） 剧本原文引用
"""
import re
import sys
from pathlib import Path

PATTERNS = [
    r'（参考 [^）]*）',
    r'（[^）]*DOTA2[^）]*）',
    r'（[^）]*状态[^）]*）',
    r'（依据[^）]*）',
    r'（本镜头[^）]*）',
    r'（我方[^）]*）',
]


def clean(text: str) -> str:
    # Remove qualifier parentheticals
    for pat in PATTERNS:
        text = re.sub(pat, '', text)
    # Tidy artifacts left behind
    text = re.sub(r'、、+', '、', text)
    text = re.sub(r' +作为', ' 作为', text)
    text = re.sub(r' +。', '。', text)
    text = re.sub(r' +，', '，', text)
    text = re.sub(r' +、', '、', text)
    text = re.sub(r'  +', ' ', text)
    # Normalize 作为角色外貌参考/背景参考 — keep as-is, just no leading space
    return text


def strip_material_line_parens(text: str) -> str:
    """素材引用行（紧跟 V 号码的那一行）只保留名字，去掉所有 （...） 限定。"""

    def strip(match: re.Match) -> str:
        prefix = match.group(1)
        line = match.group(2)
        line = re.sub(r'（[^）]*）', '', line)
        line = re.sub(r'  +', ' ', line)
        line = re.sub(r' +作为', '作为', line)
        line = re.sub(r' +。', '。', line)
        line = re.sub(r' +、', '、', line)
        return prefix + line

    return re.sub(
        r'(> \*\*EP\d+-V\d+\*\*\n> )([^\n]*)',
        strip,
        text,
    )


def add_v_markers(text: str) -> str:
    """在每个 V 块的提示词正文最前面加 > **EP{NN}-V{NN}** 标识。"""

    def inject(match: re.Match) -> str:
        v_id = match.group(1)
        section = match.group(0)
        # Idempotent: skip if V marker already injected
        if f'> **{v_id}**' in section:
            return section
        return re.sub(
            r'(\*\*提示词\*\*：\n\n)> ',
            r'\1> **' + v_id + r'**\n> ',
            section,
            count=1,
        )

    return re.sub(
        r'### (EP\d+-V\d+) \|.*?(?=\n### |\Z)',
        inject,
        text,
        flags=re.DOTALL,
    )


def main() -> int:
    root = Path('视频提示词')
    files = sorted(root.glob('EP*_提示词.md'))
    if not files:
        print('no EP prompt files found', file=sys.stderr)
        return 1
    for path in files:
        original = path.read_text(encoding='utf-8')
        updated = strip_material_line_parens(add_v_markers(clean(original)))
        if updated == original:
            print(f'unchanged: {path}')
            continue
        path.write_text(updated, encoding='utf-8')
        delta = len(original) - len(updated)
        print(f'cleaned: {path} (-{delta} chars)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
