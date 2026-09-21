#!/usr/bin/env python3
"""
输出每人的 θ 原值 + BT rating（推荐战斗力分）对照表
附：对基准选手(θ=1, rating=1000)的1v1预期胜率
"""
import json, math, glob, os
from collections import defaultdict

ROOT = os.path.normpath(os.path.dirname(__file__) + '/..')
json_files = sorted([f for f in glob.glob(f'{ROOT}/scores/*/match_data.json') if '/history/' not in f and os.path.isfile(f)])

all_sets = []
players = set()
for fp in json_files:
    data = json.load(open(fp))
    for m in data.get('matches', []):
        a, b = m['team_a'], m['team_b']
        for p in a+b: players.add(p)
        for sk in (0,1):
            s = [m['score_a'], m['score_b']][sk]
            try: sa, sb = map(int, s.split(':'))
            except: continue
            if sa == sb: continue
            all_sets.append((a, b, sa>sb, sa, sb))
players = sorted(players)
N = len(players)

# 纯胜率统计
w = defaultdict(int); l = defaultdict(int)
for ta, tb, aw, sa, sb in all_sets:
    for p in ta:
        if aw: w[p]+=1
        else: l[p]+=1
    for p in tb:
        if not aw: w[p]+=1
        else: l[p]+=1
pure_stats = {}
for p in players:
    t = w[p]+l[p]
    pure_stats[p] = (w[p], l[p], t, (w[p]/t if t else 0))
pure_sorted = sorted(players, key=lambda p: -pure_stats[p][3])
pure_rank_all = {p:i+1 for i,p in enumerate(pure_sorted)}  # 全局31人一起排的纯胜率rank（参考用）

# ============= Bradley-Terry 训练 θ（全局，乘积）=============
theta = {p: 1.0 for p in players}
for it in range(20000):
    wins_d = defaultdict(float); denom_d = defaultdict(float)
    for ta, tb, aw, _, _ in all_sets:
        Ta = math.prod(theta[p] for p in ta)
        Tb = math.prod(theta[p] for p in tb)
        D = Ta + Tb + 1e-20
        if aw:
            for p in ta: wins_d[p] += 1.0
        else:
            for p in tb: wins_d[p] += 1.0
        for p in ta: denom_d[p] += Ta / D
        for p in tb: denom_d[p] += Tb / D
    new = {}
    for p in players:
        new[p] = theta[p] * (wins_d[p]/denom_d[p]) if denom_d[p] > 1e-15 else theta[p]
    gm = math.exp(sum(math.log(max(v,1e-20)) for v in new.values())/N)
    for p in new: new[p] = max(new[p]/gm, 1e-20)
    diff = max(abs(math.log(new[p]/theta[p])) for p in theta if theta[p]>0)
    theta = new
    if diff < 1e-8: break

# 换算出战斗力分（rating）
rating = {p: 400 * math.log10(max(theta[p], 1e-20)) + 1000 for p in players}
bt_sorted_all = sorted(players, key=lambda p: -rating[p])
bt_rank_all = {p:i+1 for i,p in enumerate(bt_sorted_all)}  # 全局31人一起排的rank（参考用）

# ============== 关键修正：过滤<30局后重新编号排名（BT & 纯胜率 同步重编）==============
cutoff = 30
# 先按rating排好，再过滤≥cutoff局的，得到"正式排名榜"
shown_sorted = [p for p in bt_sorted_all if pure_stats[p][2] >= cutoff]  # 按rating降序
bt_rank_official = {p:i+1 for i,p in enumerate(shown_sorted)}  # BT正式排名：1,2,3...24

# 纯胜率也同步：先过滤，再对剩下的人按纯胜率重新编号
pure_qualified_sorted = sorted([p for p in players if pure_stats[p][2] >= cutoff],
                               key=lambda p: -pure_stats[p][3])
pure_rank_official = {p:i+1 for i,p in enumerate(pure_qualified_sorted)}  # 纯胜率正式排名

skipped = [p for p in bt_sorted_all if pure_stats[p][2] < cutoff]

# θ=1 对应基准分 1000，算 1v1 对基准选手的预期胜率
def win_vs_benchmark(theta_p):
    return theta_p / (theta_p + 1.0)

# ============= 输出 ============
print('='*150)
print(f'全局 Bradley-Terry θ 原值 + 战斗力分(rating) 对照表（{len(shown_sorted)}人出场≥{cutoff}局 / {len(all_sets)}局 / 13训练日）'.center(150))
print('='*150)
hdr = f'{"BT排名":>6}{"纯WR":>6}{"θ原值(乘子)":>15}{"BT战斗力分":>12}{"vs基准胜率":>14}{"比基准强倍":>11}  {"选手":<8}{"局数(W-L)":>12}'
print(hdr)
print('-'*150)
for rank, p in enumerate(shown_sorted, 1):
    W, L, T, WR = pure_stats[p]
    θ = theta[p]
    rt = rating[p]
    vs_bench = win_vs_benchmark(θ)
    strength_ratio = θ
    print(f'{rank:>6}{pure_rank_official[p]:>6}{θ:>15.4f}{rt:>12.0f}{vs_bench*100:>13.1f}%{strength_ratio:>11.2f}x  {p:<8}{f"{T}({W}-{L})":>12}')

print()
# 经验教训要求的"口径说明"（避免排行榜/战斗力显示不一致）
print('='*150)
print('📖 【口径说明 · 重要】'.center(150))
print('='*150)
print('  ① θ 原值：BT模型的内部"实力乘子"，几何均值归一化为1。只有比值有意义，绝对值无意义。')
print('     · 1v1真实胜率公式：P(A胜B) = θA / (θA + θB)')
print('     · 双打团队实力合成：Team_strength = θ队友1 × θ队友2   （⚠️ 是乘积！不是加法！）')
print()
print('  ② BT战斗力分(rating) = 400·log₁₀(θ) + 1000，与Elo分完全同口径。**推荐对外展示/排行榜用这个分**。')
print('     · rating 1000 = 基准水平（中等选手参考线）')
print('     · 分差→胜率对照：差 50分 ≈ 57:43 ；差 100分 ≈ 64:36 ；差 200分 ≈ 76:24 ；差 400分 ≈ 91:9')
print('     · ⚠️ rating 不能直接加！双打组队时必须先还原 θ=10^((rating-1000)/400) 再相乘。')
print()
print('  ③ "比基准强倍" = θ / θ基准(=1.0)，表示两人随机组队后1v1时，他能赢基准选手多少倍概率')
print('     · 例：黄冬青4.02x → 对基准选手胜率约 80%（4.02/(1+4.02)≈80%）')
print('     · 例：董广博1.02x → 对基准选手刚过50%（1.02/2.02≈50.5%）')
print()

# 用具体例子演示怎么算胜率（让团队会看θ/rating）
print('='*150)
print('🧮 【实战例子】怎么用 θ / rating 算任意两人的1v1预期胜率 & 双打组合团队实力'.center(150))
print('='*150)

examples_1v1 = [
    ('黄冬青', '董广博'),
    ('黄冬青', '王小波'),
    ('陈小洪', '徐越'),
    ('林锋', '程建兴'),
]
print(f'\n  1v1 预期胜率（单打开球视角，双打只是参考，因为双打还看搭档/适配）：')
print(f'  {"选手A":<8}  θA   vs  {"选手B":<8}  θB     → P(A胜) : P(B胜)')
print(f'  ' + '-'*80)
for a, b in examples_1v1:
    pa = theta[a]/(theta[a]+theta[b])
    pb = 1-pa
    print(f'  {a:<8}{theta[a]:>6.2f}  vs  {b:<8}{theta[b]:>6.2f}   → {pa*100:>5.1f}% : {pb*100:>5.1f}%')

# 双打组合对比（乘积合成）
examples_doubles = [
    (['黄冬青','董广博'], ['苏大哲','陈财贵']),
    (['陈小洪','罗琴荩'], ['林锋','谢卓珊']),
]
print(f'\n  双打组合团队实力对比（θ乘积合成，比值越大=胜率越高）：')
print(f'  {"组合A":<22} θ乘积   vs  {"组合B":<22} θ乘积   → TeamA胜率')
print(f'  ' + '-'*95)
for ta, tb in examples_doubles:
    Ta = math.prod(theta[p] for p in ta)
    Tb = math.prod(theta[p] for p in tb)
    pa = Ta/(Ta+Tb)
    print(f'  {"/".join(ta):<22}{Ta:>6.2f}   vs  {"/".join(tb):<22}{Tb:>6.2f}   → {pa*100:>5.1f}%')

print()
if skipped:
    print(f'（出场<{cutoff}局样本不足，θ不稳定不列，但内部θ值已用于全局排名）：')
    print('  ' + '、'.join(f'{p}(T={pure_stats[p][2]}, θ={theta[p]:.3f}, rating={rating[p]:.0f})' for p in skipped))

print()
# ============ 保存 JSON 方便脚本读取 ============
out_path = f'{ROOT}/scores/20260831/bt_theta_ratings.json'
result = {
    'meta': {
        'total_sets': len(all_sets),
        'total_players': N,
        'cutoff_sets': cutoff,
        'theta_normalization': '几何平均=1',
        'rating_formula': '400*log10(theta)+1000',
        '1v1_win_prob': 'thetaA/(thetaA+thetaB)',
        'doubles_team_strength': 'theta1 * theta2 (乘积)',
    },
    'players': {}
}
for p in players:
    W, L, T, WR = pure_stats[p]
    # 正式排名：如果qualified用official（过滤后重编），否则None
    bt_official = bt_rank_official[p] if p in bt_rank_official else None
    pure_official = pure_rank_official[p] if p in pure_rank_official else None
    result['players'][p] = {
        'theta': round(theta[p], 6),
        'bt_rating': round(rating[p], 1),
        'bt_rank': bt_official,                       # 过滤<30局后的BT正式排名，样本不足为None
        'winrate_rank': pure_official,                # 过滤<30局后的纯胜率正式排名，样本不足为None
        'bt_rank_global_all31': bt_rank_all[p],       # 全局31人一起排的BT原始排名（仅供参考）
        'winrate_rank_global_all31': pure_rank_all[p],# 全局31人一起排的纯胜率原始排名（仅供参考）
        'total_sets': T,
        'wins': W,
        'losses': L,
        'winrate': round(WR*100, 2),
        'vs_benchmark_win_pct': round(win_vs_benchmark(theta[p])*100, 2),
        'strength_ratio_vs_benchmark': round(theta[p], 4),
        'qualified': T >= cutoff,
    }
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(f'✅ JSON数据已保存：{out_path}')
