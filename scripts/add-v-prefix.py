#!/usr/bin/env python3
"""在每个 V 块的提示词正文最前面加一行 `> VXX`（如 V01、V02），
位于 `**提示词**：\\n\\n> ` 之后、素材引用行之前。幂等：若已有则跳过。
"""
import re
import sys
from pathlib import Path


V_TITLE_PAT = re.compile(
    r'(### V(\d+) \| [^\n]+\n[\s\S]*?\*\*提示词\*\*：\n\n)(> )',
)


def inject(match: re.Match) -> str:
    head = match.group(1)
    v_num = match.group(2)
    # Check if the next line after `**提示词**：\n\n` already starts with `> V{num}`
    after = match.group(3)
    return f'{head}> V{v_num}\n{after}'


def is_already_prefixed(text: str, v_num: str) -> bool:
    return f'**提示词**：\n\n> V{v_num}\n' in text


def process(path: Path) -> bool:
    text = path.read_text(encoding='utf-8')

    # iterate V blocks manually to skip idempotent
    new_parts = []
    last = 0
    for m in V_TITLE_PAT.finditer(text):
        v_num = m.group(2)
        if is_already_prefixed(text, v_num):
            new_parts.append(text[last:m.end()])
        else:
            new_parts.append(text[last:m.start()])
            new_parts.append(inject(m))
        last = m.end()
    new_parts.append(text[last:])
    updated = ''.join(new_parts)

    if updated == text:
        print(f'unchanged: {path}')
        return False
    path.write_text(updated, encoding='utf-8')
    print(f'prefixed: {path}')
    return True


def main() -> int:
    root = Path('视频提示词')
    files = sorted(root.glob('EP*_提示词.md'))
    if not files:
        print('no EP prompt files found', file=sys.stderr)
        return 1
    for p in files:
        process(p)
    return 0


if __name__ == '__main__':
    sys.exit(main())
