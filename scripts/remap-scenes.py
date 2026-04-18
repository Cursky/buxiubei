#!/usr/bin/env python3
"""按最新场景图批量替换场景/角色引用。

规则：
- 时空系统局 → 时空管理局
- 对局空间（游戏内基地遗迹） → 基地场景
- 对局空间（装备栏 HUD） → 对战河道
- 对局空间（决赛现场 + 对面野区） → 对战河道
- 对局空间（肉山坑） → 对战河道、肉山
- 裸 "对局空间" → 对战河道
- 对面选手席、比赛选手席 → 比赛选手席（去重）
- 对面选手席 → 比赛选手席
- 冠军披风三变体 → 电竞队服本体
- 小黑-休闲装 → 小黑-家居服
- 采访台 → 不朽杯采访台
- 小黑现实中的家 → 深夜电竞房（复用）
- 观众席（独立出现）→ 不朽杯现场
- 不朽杯现场、观众席 → 不朽杯现场
"""
import re
from pathlib import Path


SUBSTITUTIONS = [
    ('对局空间（游戏内基地遗迹）', '基地场景'),
    ('对局空间（装备栏 HUD）', '对战河道'),
    ('对局空间（决赛现场 + 对面野区）', '对战河道'),
    ('对局空间（肉山坑）', '对战河道、肉山'),
    ('时空系统局', '时空管理局'),
    ('对面选手席、比赛选手席', '比赛选手席'),
    ('比赛选手席、对面选手席', '比赛选手席'),
    ('对面选手席', '比赛选手席'),
    ('小黑-电竞队服-冠军披风', '小黑-电竞队服'),
    ('超哥-电竞队服-冠军披风', '超哥-电竞队服'),
    ('鲷哥-电竞队服-冠军披风', '鲷哥-电竞队服'),
    ('小黑-休闲装', '小黑-家居服'),
    ('不朽杯现场、观众席', '不朽杯现场'),
    ('小黑现实中的家', '深夜电竞房'),
    ('采访台', '不朽杯采访台'),
]

# 裸 "对局空间" → "对战河道"（不匹配已被上面前缀精确替换掉的）
BARE_OBJ_PAT = re.compile(r'对局空间(?!）)')


def transform(text: str) -> str:
    for old, new in SUBSTITUTIONS:
        text = text.replace(old, new)
    text = BARE_OBJ_PAT.sub('对战河道', text)
    # 不朽杯采访台 可能因多轮替换变成 不朽杯不朽杯采访台，去重
    text = text.replace('不朽杯不朽杯采访台', '不朽杯采访台')
    # 同一行出现多次对战河道（由不同源合并来）
    text = re.sub(r'对战河道、对战河道', '对战河道', text)
    return text


def main():
    root = Path('视频提示词')
    for p in sorted(root.glob('EP*_提示词.md')):
        orig = p.read_text(encoding='utf-8')
        new = transform(orig)
        if new == orig:
            print(f'unchanged: {p}')
            continue
        p.write_text(new, encoding='utf-8')
        print(f'remapped: {p}')


if __name__ == '__main__':
    main()
