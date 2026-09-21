#!/usr/bin/env python3
"""
将BT排名总表导出为Excel（.xlsx），格式精美
"""
import json, os
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

ROOT = os.path.normpath(os.path.dirname(__file__) + '/..')
data_path = f'{ROOT}/scores/20260831/bt_theta_ratings.json'
out_path = f'{ROOT}/scores/20260831/BT排名总表.xlsx'

with open(data_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

meta = data['meta']
players = data['players']

# ========== 整理两个sheet的数据 ==========
# Sheet1：正式排名（出场≥30局）
cutoff = meta['cutoff_sets']
qualified = []
unqualified = []
for name, p in players.items():
    # 正式rank（过滤<30局重编的），没有就用全局rank+参考标注
    bt_display = p['bt_rank'] if p['bt_rank'] is not None else None
    pure_display = p['winrate_rank'] if p['winrate_rank'] is not None else None
    row = {
        'name': name,
        'bt_rank': bt_display,
        'bt_rank_is_official': p['bt_rank'] is not None,
        'bt_rank_global': p['bt_rank_global_all31'],
        'winrate_rank': pure_display,
        'winrate_rank_global': p['winrate_rank_global_all31'],
        'theta': p['theta'],
        'bt_rating': p['bt_rating'],
        'vs_benchmark_win_pct': p['vs_benchmark_win_pct'],
        'strength_ratio_vs_benchmark': p['strength_ratio_vs_benchmark'],
        'total_sets': p['total_sets'],
        'wins': p['wins'],
        'losses': p['losses'],
        'winrate': p['winrate'],
        'qualified': p['qualified'],
    }
    if p['qualified']:
        qualified.append(row)
    else:
        unqualified.append(row)

qualified.sort(key=lambda x: x['bt_rank'])  # 按正式BT rank 1-24排
# 样本不足：按rating从高到低排
unqualified.sort(key=lambda x: x['bt_rating'], reverse=True)

# ========== 创建Workbook ==========
wb = Workbook()

# 颜色定义
gold_fill = PatternFill(start_color='FFF2CC', end_color='FFF2CC', fill_type='solid')   # 金/浅黄
silver_fill = PatternFill(start_color='E8E8E8', end_color='E8E8E8', fill_type='solid') # 银
bronze_fill = PatternFill(start_color='F4D7C0', end_color='F4D7C0', fill_type='solid') # 铜
header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid') # 深蓝表头
alt_fill = PatternFill(start_color='F2F2F2', end_color='F2F2F2', fill_type='solid')    # 隔行浅灰
warn_fill = PatternFill(start_color='FFF2CC', end_color='FFF2CC', fill_type='solid')    # 样本不足提示黄

header_font = Font(name='微软雅黑', size=11, bold=True, color='FFFFFF')
title_font = Font(name='微软雅黑', size=14, bold=True, color='1F4E78')
meta_font = Font(name='微软雅黑', size=10, italic=True, color='666666')
body_font = Font(name='微软雅黑', size=10)
rank_font_gold = Font(name='微软雅黑', size=11, bold=True, color='B8860B')
rank_font_top = Font(name='微软雅黑', size=10, bold=True)

thin = Side(border_style='thin', color='B4B4B4')
border = Border(left=thin, right=thin, top=thin, bottom=thin)
center_align = Alignment(horizontal='center', vertical='center', wrap_text=False)
left_align = Alignment(horizontal='left', vertical='center')

def apply_row_style(ws, row_cells, fill=None, font=None, align=center_align, bd=border):
    for c in row_cells:
        if fill: c.fill = fill
        if font: c.font = font
        c.alignment = align
        c.border = bd

def write_sheet(ws, title_str, row_list, is_qualified=True):
    # === 标题 & 元信息 ===
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=10)
    ws.cell(row=1, column=1, value=title_str).font = title_font
    ws.cell(row=1, column=1).alignment = left_align

    meta_lines = [
        f'数据范围：{meta["total_sets"]}局 / 13个训练日 / {meta["total_players"]}位选手',
        f'模型：Bradley-Terry 全局训练    合成方式：双打团队实力 = θ₁ × θ₂（乘积）',
        f'rating公式：400×log₁₀(θ) + 1000    （rating 1000 = 基准线，θ=1）',
    ]
    for i, line in enumerate(meta_lines):
        ws.merge_cells(start_row=2+i, start_column=1, end_row=2+i, end_column=10)
        ws.cell(row=2+i, column=1, value=line).font = meta_font
        ws.cell(row=2+i, column=1).alignment = left_align

    # === 表头 ===
    header_row = 6
    if is_qualified:
        headers = [
            ('全局BT排名', 12), ('纯胜率排名', 10), ('选手', 10),
            ('θ原值（实力乘子）', 16), ('BT战斗力 rating', 15),
            ('vs基准胜率', 12), ('比基准强倍', 12),
            ('总局', 8), ('胜-负', 12), ('纯胜率', 10)
        ]
    else:
        headers = [
            ('BT排名', 10), ('纯胜率排名', 10), ('选手', 10),
            ('θ原值', 14), ('BT战斗力', 13),
            ('vs基准胜率', 12), ('比基准强倍', 12),
            ('总局', 8), ('胜-负', 12), ('纯胜率', 10),
            ('样本提示', 20)
        ]

    for col, (h, width) in enumerate(headers, 1):
        cell = ws.cell(row=header_row, column=col, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = center_align
        cell.border = border
        ws.column_dimensions[get_column_letter(col)].width = width

    # === 数据行 ===
    for i, r in enumerate(row_list):
        row_idx = header_row + 1 + i
        # 奖牌色
        if is_qualified and i == 0:
            row_fill = gold_fill
            rf = rank_font_gold
        elif is_qualified and i == 1:
            row_fill = silver_fill
            rf = rank_font_top
        elif is_qualified and i == 2:
            row_fill = bronze_fill
            rf = rank_font_top
        elif i % 2 == 1:
            row_fill = alt_fill
            rf = body_font
        else:
            row_fill = None
            rf = body_font

        rank_val = f'🥇 {r["bt_rank"]}' if (is_qualified and i==0) else \
                   f'🥈 {r["bt_rank"]}' if (is_qualified and i==1) else \
                   f'🥉 {r["bt_rank"]}' if (is_qualified and i==2) else r['bt_rank']
        wl = f'{r["wins"]}-{r["losses"]}'
        ratio = f'{r["strength_ratio_vs_benchmark"]:.2f}×'

        if is_qualified:
            vals = [
                rank_val, r['winrate_rank'], r['name'],
                round(r['theta'], 4), round(r['bt_rating'], 1),
                f'{r["vs_benchmark_win_pct"]:.1f}%', ratio,
                r['total_sets'], wl, f'{r["winrate"]:.2f}%'
            ]
        else:
            vals = [
                r['bt_rank'], r['winrate_rank'], r['name'],
                round(r['theta'], 4), round(r['bt_rating'], 1),
                f'{r["vs_benchmark_win_pct"]:.1f}%', ratio,
                r['total_sets'], wl, f'{r["winrate"]:.2f}%',
                f'出场{r["total_sets"]}局<{cutoff}局，θ不稳'
            ]

        cells = []
        for col, v in enumerate(vals, 1):
            c = ws.cell(row=row_idx, column=col, value=v)
            cells.append(c)

        # 选手名列左对齐
        cells[2].alignment = left_align
        apply_row_style(ws, cells, fill=row_fill, font=rf)
        cells[2].font = Font(name='微软雅黑', size=10, bold=(i<3 and is_qualified))
        cells[2].alignment = left_align

    # 样本不足底部提示
    if is_qualified and unqualified:
        tip_row = header_row + 1 + len(row_list) + 1
        ws.merge_cells(start_row=tip_row, start_column=1, end_row=tip_row, end_column=10)
        names = '、'.join(f'{p["name"]}({p["total_sets"]}局)' for p in unqualified)
        cell = ws.cell(row=tip_row, column=1, value=f'⚠️  样本不足不参与排名（<{cutoff}局）：{names}')
        cell.fill = warn_fill
        cell.font = meta_font
        cell.alignment = left_align
        cell.border = border

# Sheet1：正式排名（≥30局）
ws1 = wb.active
ws1.title = 'BT排名（出场≥30局）'
write_sheet(ws1,
            f'全局 Bradley-Terry 排名总表（出场≥{cutoff}局 ｜ {len(qualified)}人）',
            qualified, is_qualified=True)

# Sheet2：全部31人（含样本不足）
ws2 = wb.create_sheet('全部选手（含样本不足）')
all_rows = []
for name, p in players.items():
    # 正式排名优先，否则全局参考
    if p['bt_rank'] is not None:
        bt_display = p['bt_rank']
    else:
        bt_display = f'全{p["bt_rank_global_all31"]}(参考)'
    if p['winrate_rank'] is not None:
        pure_display = p['winrate_rank']
    else:
        pure_display = f'全{p["winrate_rank_global_all31"]}(参考)'
    all_rows.append({
        'name': name,
        'bt_rank': bt_display,
        'winrate_rank': pure_display,
        'theta': p['theta'],
        'bt_rating': p['bt_rating'],
        'vs_benchmark_win_pct': p['vs_benchmark_win_pct'],
        'strength_ratio_vs_benchmark': p['strength_ratio_vs_benchmark'],
        'total_sets': p['total_sets'],
        'wins': p['wins'],
        'losses': p['losses'],
        'winrate': p['winrate'],
        '_qualified': p['qualified'],
        '_rating_sort': p['bt_rating'],
        '_rank_sort': (p['bt_rank'] if p['bt_rank'] is not None else 9999),
    })
# 排序：qualified在前按正式rank；unqualified在后按rating从高到低
all_rows.sort(key=lambda x: (not x['_qualified'],
                              x['_rank_sort'] if x['_qualified'] else -x['_rating_sort']))

# 第二个sheet用is_qualified=False会有11列，我们用同一格式写但给提示
# 简化：直接在写的时候根据总局判断要不要加颜色标
write_sheet(ws2,
            f'全局全部 {len(all_rows)} 位选手 BT 排名（含出场<{cutoff}局样本不足）',
            all_rows, is_qualified=False)

# 标红/标黄样本不足的行
header_row = 6
for i, r in enumerate(all_rows):
    row_idx = header_row + 1 + i
    if not r['_qualified']:
        for col in range(1, 12):
            ws2.cell(row=row_idx, column=col).fill = warn_fill

# Sheet3：口径&公式说明
ws3 = wb.create_sheet('口径说明 & 计算示例')
ws3.column_dimensions['A'].width = 120
info_rows = [
    ('📖 口径说明', title_font),
    ('', None),
    ('① θ原值：BT模型内部"实力乘子"，几何均值归一化为1。只有比值有意义，绝对值无意义。', meta_font),
    ('    · 1v1胜率公式：P(A胜B) = θA / (θA + θB)', body_font),
    ('    · 双打团队实力合成：Team_strength = θ队友1 × θ队友2  （⚠️ 是乘积！不是加法！）', body_font),
    ('', None),
    ('② BT战斗力分（rating）= 400×log₁₀(θ) + 1000，与Elo分完全同口径，推荐对外展示/排行榜用这个分。', meta_font),
    ('    · rating 1000 = 基准水平（中等选手参考线，θ=1对应1000分）', body_font),
    ('    · rating分差 → 预期胜率对照：', body_font),
    ('      差 50分 ≈ 57:43  ｜  差100分 ≈ 64:36  ｜  差200分 ≈ 76:24  ｜  差400分 ≈ 91:9', body_font),
    ('    · ⚠️ rating 不能直接加！双打组队时必须先还原 θ = 10^((rating-1000)/400) 再相乘。', body_font),
    ('', None),
    ('③ 「比基准强倍」= θ / θ基准(=1.0)，表示对基准选手(θ=1)的1v1胜率倍数', meta_font),
    ('    · 例：黄冬青 3.91× → 对基准选手胜率 ≈ 80%（3.91/(1+3.91)≈80%）', body_font),
    ('', None),
    ('🧮 实战计算示例', title_font),
    ('', None),
    ('▎1v1预期胜率（单打开球视角，双打只是参考，因为双打还看搭档/适配）', meta_font),
    ('  黄冬青(θ=3.91) vs 董广博(θ=1.02) → P(黄胜) = 3.91/(3.91+1.02) = 79.3%', body_font),
    ('  黄冬青(θ=3.91) vs 王小波(θ=0.75) → P(黄胜) = 3.91/(3.91+0.75) = 83.9%', body_font),
    ('  陈小洪(θ=0.83) vs 徐越(θ=0.60)   → P(陈胜) = 0.83/(0.83+0.60) = 57.8%', body_font),
    ('  林锋(θ=3.63)  vs 程建兴(θ=2.19) → P(林胜) = 3.63/(3.63+2.19) = 62.4%', body_font),
    ('', None),
    ('▎双打组合团队实力对比（θ乘积合成，比值越大=胜率越高）', meta_font),
    ('  黄冬青/董广博  θ乘积=3.91×1.02=3.99  vs  苏大哲/陈财贵  θ乘积=2.23×2.18=4.87', body_font),
    ('    → P(黄/董胜) = 3.99 / (3.99+4.87) = 45.0%', body_font),
    ('', None),
    ('  苏大哲/陈财贵  θ乘积=2.23×2.18=4.87  vs  刘继宇/陈顺星  θ乘积=1.46×0.73=1.07', body_font),
    ('    → P(苏/财胜) = 4.87 / (4.87+1.07) = 82.0%   ←（就是你最开始问的那组预测）', body_font),
    ('', None),
    ('_本报告生成：BT θ战斗力系统 ｜ 13个训练日全局训练_', meta_font),
]
for i, (text, font) in enumerate(info_rows, 1):
    ws3.merge_cells(start_row=i, start_column=1, end_row=i, end_column=12)
    c = ws3.cell(row=i, column=1, value=text)
    c.alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)
    if font: c.font = font
    ws3.row_dimensions[i].height = 20 if not text.startswith('📖') and not text.startswith('🧮') else 30

wb.save(out_path)
print(f'✅ Excel 导出成功：{out_path}')
print(f'   Sheet1：BT排名（出场≥{cutoff}局，{len(qualified)}人）')
print(f'   Sheet2：全部{len(all_rows)}位选手（含样本不足，有⚠️标黄提示）')
print(f'   Sheet3：口径说明 & 计算示例')
