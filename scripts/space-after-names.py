#!/usr/bin/env python3
"""在角色/场景/道具名字后紧跟中文字符时补一个空格。

规则：
- 名字后紧接中文字符（CJK），插入空格；
- 名字后已是标点 / 空格 / 括号等自然边界 → 不动；
- **跳过对白内容** 「...」 —— 台词原文保持紧凑不改；
- **跳过代码块 / YAML frontmatter-like 元数据**（本项目不涉及）；
- 长名字优先，避免 `小黑-家居服` 被 `小黑` 误切。
"""
import re
from pathlib import Path

NAMES = [
    # 真人现实层
    '小黑-家居服', '小黑-电竞队服',
    '超哥-电竞队服', '鲷哥-电竞队服',
    '敌方1号位-电竞队服', '敌方2号位-电竞队服',
    '敌方辅助-电竞队服', '敌方中单-电竞队服', '敌方射手-电竞队服',
    '我方路人', '我方路人2', '我方路人3',
    '解说员-赛事直播间',
    # 游戏内英雄 / 单位
    '拉比克-小黑', '撼地者-小黑', '影魔-小黑', '龙骑-小黑', '水人-小黑',
    '敌法师-超哥', '斯温-超哥',
    '潮汐猎人-鲷哥', '兽王-鲷哥',
    '神谕者-敌方中单', '莱恩-敌方中单',
    '隐刺-敌方2号位', '月神白虎-敌方辅助', '小牛-敌方辅助',
    '火枪手-敌方射手', '沙王-敌方1号位',
    # 场景
    '深夜电竞房', '比赛选手席', '训练室复盘区', '时空管理局',
    '对战河道', '基地场景', '肉山', '鸟',
    '不朽杯采访台', '不朽杯现场',
    # 道具
    'BKB-装备图标', '不朽盾', '推推棒', '真视宝石',
]

NAMES.sort(key=len, reverse=True)

CJK = r'[\u4e00-\u9fa5]'


def inject_space_in_segment(seg: str) -> str:
    for name in NAMES:
        pat = re.compile(rf'({re.escape(name)})({CJK})')
        seg = pat.sub(r'\1 \2', seg)
    return seg


DIALOG_SEG = re.compile(r'(「[^」]*」)')


def process_line(line: str) -> str:
    # split by 「...」, only process non-dialog parts
    parts = DIALOG_SEG.split(line)
    out = []
    for p in parts:
        if p.startswith('「') and p.endswith('」'):
            out.append(p)
        else:
            out.append(inject_space_in_segment(p))
    return ''.join(out)


def process(path: Path) -> bool:
    text = path.read_text(encoding='utf-8')
    new_lines = [process_line(ln) for ln in text.split('\n')]
    new_text = '\n'.join(new_lines)
    if new_text == text:
        print(f'unchanged: {path}')
        return False
    path.write_text(new_text, encoding='utf-8')
    print(f'spaced: {path}')
    return True


def main():
    root = Path('视频提示词')
    for p in sorted(root.glob('EP*_提示词.md')):
        process(p)


if __name__ == '__main__':
    main()
