#!/usr/bin/env python3
"""将 视频提示词/EP*_提示词.md 规整为 提示词参考/世子妃逃婚_第2集 的格式。

变换点：
1. `### EP\\d+-V(\\d+) | 标题 | N 秒` → `### V(\\d+) | 标题 | N秒`
2. 删除提示词体内的 `> **EP\\d+-V\\d+**\\n> ` 标识（保留其后的素材引用行）
3. 镜头编号: `镜头 N：` → `镜头N：`
4. 素材引用行空格: `xxx作为角色外貌参考` → `xxx 作为角色外貌参考`
5. 结尾字幕串: `任何分镜和画面都不要出现字幕。` → `如何画面和分镜都不要出现字幕 如果出现字幕将字幕不透明度设置为0`
6. 新增 **场景**/**景别**/**运镜**/**对话** 元数据（从素材引用 + 镜头 + 对白自动抽取）
"""
import re
import sys
from pathlib import Path

SCENE_NAMES = {
    '深夜电竞房', '比赛选手席', '训练室复盘区', '冠军采访台', '小黑现实中的家',
    '不朽杯现场观众区', '时空系统局', '系统冻结异常场', '团队共担觉醒场',
    '半决赛舞台·中路二塔攻防区', '决赛现场·肉山坑', '决赛现场·比赛推进区',
    '决赛现场·野区与肉山坑推进区', '决赛现场·野区交叉画面', '决赛现场·高地推进区',
    '失败轮回蒙太奇场', '对局空间', '对面选手席', '赛事直播间',
    '小黑现实中的家', '采访台', '不朽杯现场', '观众席',
}


def pick_scene(material_line: str) -> str:
    """从素材引用行选出场景名（用第一个命中 SCENE_NAMES 或含"场"/"席"/"区"/"台"/"间"/"房"关键字的项）。"""
    items = [x.strip() for x in material_line.split('、')]
    for it in items:
        base = it.split('（')[0].strip()
        if base in SCENE_NAMES:
            return base
    for it in items:
        base = it.split('（')[0].strip()
        if any(k in base for k in ['场', '席', '区', '台', '间', '房']):
            return base
    return items[-1] if items else ''


SHOT_HEAD_PAT = re.compile(r'镜头\s*(\d+)：([^。\n]+)。')


def extract_shots(prompt_body: str):
    """返回 [(景别, 运镜)] 列表；景别=首逗号前，运镜=首逗号后（无则空）。"""
    shots = []
    for m in SHOT_HEAD_PAT.finditer(prompt_body):
        head = m.group(2)
        parts = [p.strip() for p in head.split('，', 1)]
        jing = parts[0]
        yun = parts[1] if len(parts) > 1 else ''
        shots.append((jing, yun))
    return shots


DIALOG_PAT = re.compile(r'>\s*([^（\n]+?)(?:（[^）]*）)?\s*说：')


def extract_speakers(prompt_body: str):
    """提取所有对白角色名（去重、保序）。"""
    seen = []
    for m in DIALOG_PAT.finditer(prompt_body):
        name = m.group(1).strip()
        if name and name not in seen:
            seen.append(name)
    return seen


V_BLOCK_PAT = re.compile(
    r'### EP(\d+)-V(\d+) \| ([^|\n]+?) \| (\d+)\s*秒\n\n'
    r'\*\*素材引用\*\*：([^\n]+)\n\n'
    r'\*\*提示词\*\*：\n\n'
    r'(> [\s\S]*?)(?=\n---|\n\n---|\Z)',
    re.MULTILINE,
)


def convert_block(match: re.Match) -> str:
    _ep = match.group(1)
    v_num = match.group(2)
    title = match.group(3).strip()
    secs = match.group(4)
    materials = match.group(5).strip()
    body = match.group(6)

    # 1) 删除提示词体内的 V 标识行
    body = re.sub(r'^>\s*\*\*EP\d+-V\d+\*\*\n', '', body, count=1, flags=re.MULTILINE)

    # 2) 镜头号去空格
    body = re.sub(r'镜头\s+(\d+)：', r'镜头\1：', body)

    # 3) 素材引用第一行加空格: `xxx作为` → `xxx 作为`
    body = re.sub(r'([\u4e00-\u9fa5\w\-/]+)作为(角色外貌参考|背景参考|游戏内英雄参考|游戏内英雄/单位参考|非人实体参考|真人角色参考|真人角色外貌参考|HUD 元素参考|对手方参考|解说席角色与背景参考|场景主体参考|角色与背景参考)', r'\1 作为\2', body)

    # 4) 结尾字幕串
    body = body.replace(
        '任何分镜和画面都不要出现字幕。',
        '如何画面和分镜都不要出现字幕 如果出现字幕将字幕不透明度设置为0',
    )

    # 5) 抽取场景 / 景别 / 运镜 / 对白
    scene = pick_scene(materials)
    shots = extract_shots(body)
    jingbie = '→'.join(s[0] for s in shots) if shots else ''
    yunjing = '→'.join(s[1] for s in shots) if shots else ''
    speakers = extract_speakers(body)
    dialog_field = '、'.join(speakers) if speakers else '（无）'

    # 6) 组装新 block
    new = (
        f'### V{v_num} | {title} | {secs}秒\n\n'
        f'**场景**：{scene}\n'
        f'**景别**：{jingbie} | **运镜**：{yunjing}\n'
        f'**素材引用**：{materials}\n'
        f'**对话**：{dialog_field}\n\n'
        f'**提示词**：\n\n'
        f'{body.rstrip()}\n'
    )
    return new


def process_file(path: Path) -> bool:
    original = path.read_text(encoding='utf-8')
    updated = V_BLOCK_PAT.sub(convert_block, original)
    if updated == original:
        print(f'unchanged: {path}')
        return False
    path.write_text(updated, encoding='utf-8')
    print(f'normalized: {path}')
    return True


def main() -> int:
    root = Path('视频提示词')
    files = sorted(root.glob('EP*_提示词.md'))
    if not files:
        print('no EP prompt files found', file=sys.stderr)
        return 1
    for p in files:
        process_file(p)
    return 0


if __name__ == '__main__':
    sys.exit(main())
