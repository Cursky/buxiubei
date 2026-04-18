#!/usr/bin/env python3
"""在 超哥/鲷哥 的每一条说话行中加上「超哥声音」/「鲷哥声音」标签。

覆盖两种写法：
- 无限定：`超哥-电竞队服 说：...` → `超哥-电竞队服（超哥声音）说：...`
- 已有限定：`超哥-电竞队服（闪回语音）说：...` → `超哥-电竞队服（超哥声音，闪回语音）说：...`
鲷哥同规则；幂等：已含「超哥声音」/「鲷哥声音」的行跳过。
"""
import re
import sys
from pathlib import Path

NAMES = {
    '超哥-电竞队服': '超哥声音',
    '鲷哥-电竞队服': '鲷哥声音',
}


def tag(text: str) -> str:
    for name, voice in NAMES.items():
        # Case A: existing parenthetical qualifier — `名（xxx）说：`
        text = re.sub(
            rf'({re.escape(name)})（([^）]*)）说：',
            lambda m, voice=voice: (
                m.group(0) if voice in m.group(2)
                else f'{m.group(1)}（{voice}，{m.group(2)}）说：'
            ),
            text,
        )
        # Case B: no qualifier — `名 说：`
        text = re.sub(
            rf'({re.escape(name)}) 说：',
            lambda m, voice=voice: f'{m.group(1)}（{voice}）说：',
            text,
        )
    return text


def main() -> int:
    root = Path('视频提示词')
    files = sorted(root.glob('EP*_提示词.md'))
    if not files:
        print('no EP prompt files found', file=sys.stderr)
        return 1
    for path in files:
        original = path.read_text(encoding='utf-8')
        updated = tag(original)
        if updated == original:
            print(f'unchanged: {path}')
            continue
        path.write_text(updated, encoding='utf-8')
        added = updated.count('声音）') - original.count('声音）')
        print(f'tagged: {path} (+{added} voice tags)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
