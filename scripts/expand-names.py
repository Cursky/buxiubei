#!/usr/bin/env python3
"""把提示词正文/标题里裸的「小黑」「超哥」「鲷哥」「敌方1号位」补全成
`XXX-电竞队服` / `小黑-家居服` 等完整命名。

策略：
- 按 V 块切分，依据本块 **素材引用** 行包含的变体决定替换目标：
  - 小黑：若素材引用含 "小黑-家居服" → 小黑-家居服；否则 → 小黑-电竞队服
  - 超哥：→ 超哥-电竞队服
  - 鲷哥：→ 鲷哥-电竞队服
  - 敌方1号位：→ 敌方1号位-电竞队服
- 仅替换正文与标题中的"裸名"：
  - 前面不是 `-`（排除 拉比克-小黑 等）
  - 后面不是 `-` / `（` / `（画外` / `操作` / `面前`（避免重复合成）
- **跳过对白行**（含 `说：` 的 > 行）——对白里的台词按原意保留
"""
import re
import sys
from pathlib import Path

BARE_NAMES = ['小黑', '超哥', '鲷哥', '敌方1号位']

# 判定某行是否是对白行
DIALOG_LINE = re.compile(r'说：')

V_BLOCK_SPLIT = re.compile(r'(?=^### V\d+ \|)', re.MULTILINE)


def variant_for(block: str, name: str) -> str:
    """根据当前 V 块的素材引用判定变体；默认电竞队服。"""
    mat = re.search(r'\*\*素材引用\*\*：([^\n]+)', block)
    materials = mat.group(1) if mat else ''
    if name == '小黑':
        if '小黑-家居服' in materials:
            return '小黑-家居服'
        return '小黑-电竞队服'
    if name == '超哥':
        return '超哥-电竞队服'
    if name == '鲷哥':
        return '鲷哥-电竞队服'
    if name == '敌方1号位':
        return '敌方1号位-电竞队服'
    return name


def replace_bare(text: str, name: str, variant: str) -> str:
    # 排除 -小黑 (前缀)、小黑- (后缀)、小黑（ (已有括号说明)
    pat = re.compile(
        rf'(?<![-\u4e00-\u9fa5][-])'  # 前面不是直接 -
        rf'(?<!-){re.escape(name)}(?![-（])'
    )
    return pat.sub(variant, text)


def process_block(block: str) -> str:
    if not block.strip().startswith('### V'):
        return block
    out_lines = []
    for line in block.split('\n'):
        # 跳过对白行
        if DIALOG_LINE.search(line):
            out_lines.append(line)
            continue
        # 跳过元数据行"**对话**："（需要手动检查）
        # 跳过 "**素材引用**：" 行（已经是正确命名）
        if line.startswith('**素材引用**') or line.startswith('**对话**'):
            out_lines.append(line)
            continue
        new_line = line
        for name in BARE_NAMES:
            variant = variant_for(block, name)
            new_line = replace_bare(new_line, name, variant)
        out_lines.append(new_line)
    return '\n'.join(out_lines)


def process(path: Path) -> bool:
    text = path.read_text(encoding='utf-8')
    blocks = V_BLOCK_SPLIT.split(text)
    new_blocks = [process_block(b) for b in blocks]
    new_text = ''.join(new_blocks)
    if new_text == text:
        print(f'unchanged: {path}')
        return False
    path.write_text(new_text, encoding='utf-8')
    print(f'expanded: {path}')
    return True


def main() -> int:
    root = Path('视频提示词')
    for p in sorted(root.glob('EP*_提示词.md')):
        process(p)
    return 0


if __name__ == '__main__':
    sys.exit(main())
