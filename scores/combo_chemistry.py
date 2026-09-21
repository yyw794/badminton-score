#!/usr/bin/env python3
"""
组合化学效应分析：把组合当整体看，找出 1+1=3（黄金搭档）和 1+1=1（相克组合）
"""
import json, math, glob, os
from collections import defaultdict

ROOT = os.path.normpath(os.path.dirname(__file__) + '/..')
json_files = sorted([f for f in glob.glob(f'{ROOT}/scores/*/match_data.json') if '/history/' not in f and os.path.isfile(f)])

# ========== 1. 先训全局单人θ（和之前口径一致）==========
all_sets = []
players = set()
combo_raw = defaultdict(list)  # (sorted_pair) -> list of (date, opp_sorted, a_won_in_set, sa, sb)
# 注意：combo_raw 存的是「某两人组成的双打组合」在每一局的表现，不管对手是谁

for fp in json_files:
    data = json.load(open(fp))
    date = data.get('match_date') or '?'
    for m in data.get('matches', []):
        a, b = m['team_a'], m['team_b']
        if len(a) != 2 or len(b) != 2:
            continue  # 只看双打，去掉单打
        for p in a+b: players.add(p)
        for sk in (0,1):
            s = [m['score_a'], m['score_b']][sk]
            try: sa, sb = map(int, s.split(':'))
            except: continue
            if sa == sb: continue
            aw = sa > sb
            all_sets.append((a, b, aw, sa, sb))
            # 记录组合A的这一局
            key_a = tuple(sorted(a))
            combo_raw[key_a].append((date, tuple(sorted(b)), aw, sa, sb, True))  # True = 这个组合是作为A队
            # 记录组合B的这一局（B队赢 = 非aw）
            key_b = tuple(sorted(b))
            combo_raw[key_b].append((date, tuple(sorted(a)), not aw, sb, sa, False))

players = sorted(players)
N = len(players)

theta = {p: 1.0 for p in players}
for it in range(20000):
    wins_d = defaultdict(float); denom_d = defaultdict(float)
    for ta, tb, aw, _, _ in all_sets:
        Ta = math.prod(theta[p] for p in ta); Tb = math.prod(theta[p] for p in tb)
        D = Ta + Tb + 1e-20
        if aw:
            for p in ta: wins_d[p]+=1.0
        else:
            for p in tb: wins_d[p]+=1.0
        for p in ta: denom_d[p] += Ta/D
        for p in tb: denom_d[p] += Tb/D
    new = {}
    for p in players:
        new[p] = theta[p] * (wins_d[p]/denom_d[p]) if denom_d[p] > 1e-15 else theta[p]
    gm = math.exp(sum(math.log(max(v,1e-20)) for v in new.values())/N)
    for p in new: new[p] = max(new[p]/gm, 1e-20)
    if max(abs(math.log(new[p]/theta[p])) for p in theta if theta[p]>0) < 1e-8: break
    theta = new
rating = {p: 400*math.log10(max(theta[p],1e-20))+1000 for p in players}

# ========== 2. 分析每个组合：实际胜率 vs BT预测胜率 ==========
print('='*120)
print('🔬 【组合化学效应分析】把组合当整体看：哪些 1+1>2，哪些 1+1<2'.center(120))
print('='*120)
print(f'总双打局数：{len(all_sets)} 局，不同组合数：{len(combo_raw)} 组')
print()

combo_stats = []
for pair, records in combo_raw.items():
    n = len(records)
    if n < 2:  # 至少打2局才纳入统计，否则噪音太大
        continue
    wins = sum(1 for r in records if r[2])
    actual_wr = wins / n
    # 算这个组合的平均预测胜率（按每局对手单独算）
    pred_wrs = []
    for date, opp, aw, sa, sb, _ in records:
        T_pair = math.prod(theta[p] for p in pair)
        T_opp = math.prod(theta[p] for p in opp)
        pred = T_pair / (T_pair + T_opp)
        pred_wrs.append(pred)
    avg_pred = sum(pred_wrs) / len(pred_wrs)
    # 化学反应指数 = 实际胜率 - 预测胜率（正=超常发挥，负=相克）
    chemistry = actual_wr - avg_pred
    # 组合的平均单人战斗力
    pair_rating_avg = (rating[pair[0]] + rating[pair[1]]) / 2
    combo_stats.append({
        'pair': pair,
        'n': n,
        'wins': wins,
        'losses': n - wins,
        'actual_wr': actual_wr,
        'avg_pred': avg_pred,
        'chemistry': chemistry,
        'pair_rating_avg': pair_rating_avg,
    })

print(f'有效组合（≥2局）：{len(combo_stats)} 组')
print()

# ========== 3. Top榜：化学反应最强（1+1=3）==========
print('='*120)
print('💎 【TOP 20 黄金搭档：化学反应最猛】（实际胜率 >> 单人实力预测）'.center(120))
print('='*120)
print(f'{"排名":>3} {"组合":<22} {"局数":>4} {"战绩":>8} {"实际胜率":>8} {"预测胜率":>8} {"化学反应":>10} {"平均战力":>8}')
print('-'*105)
# 筛选至少4局的，不然2局100%的噪音太大
top_chem = sorted([c for c in combo_stats if c['n'] >= 4], key=lambda x: -x['chemistry'])
for i, c in enumerate(top_chem[:20], 1):
    pair_str = '/'.join(c['pair'])
    chem_str = f'{c["chemistry"]*100:+.1f}%'
    print(f'{i:>3} {pair_str:<22} {c["n"]:>4} {c["wins"]:>3}胜{c["losses"]:>2}负 {c["actual_wr"]*100:>7.1f}% {c["avg_pred"]*100:>7.1f}% {chem_str:>10} {c["pair_rating_avg"]:>8.0f}')

print()
print('='*120)
print('🧪 【TOP 20 相克组合：化学反应最差】（实际胜率 << 单人实力预测）'.center(120))
print('='*120)
print(f'{"排名":>3} {"组合":<22} {"局数":>4} {"战绩":>8} {"实际胜率":>8} {"预测胜率":>8} {"化学反应":>10} {"平均战力":>8}')
print('-'*105)
bottom_chem = sorted([c for c in combo_stats if c['n'] >= 4], key=lambda x: x['chemistry'])
for i, c in enumerate(bottom_chem[:20], 1):
    pair_str = '/'.join(c['pair'])
    chem_str = f'{c["chemistry"]*100:+.1f}%'
    print(f'{i:>3} {pair_str:<22} {c["n"]:>4} {c["wins"]:>3}胜{c["losses"]:>2}负 {c["actual_wr"]*100:>7.1f}% {c["avg_pred"]*100:>7.1f}% {chem_str:>10} {c["pair_rating_avg"]:>8.0f}')

# ========== 4. 你之前讨论过的冤案组合 ==========
print()
print('='*120)
print('🔍 【重点关注组合】之前讨论过的冤案/热门组合'.center(120))
print('='*120)
focus_pairs = [
    ('王小波', '董广博'),
    ('董广博', '陈顺星'),
    ('苏大哲', '陈财贵'),
    ('罗琴荩', '徐越'),
    ('黄冬青', '林锋'),
    ('林锋', '陈小洪'),
    ('苏大哲', '陈小洪'),
    ('刘继宇', '苏大哲'),
    ('严勇文', '苏大哲'),
    ('唐英武', '林锋'),
    ('罗琴荩', '陈财贵'),
]
for p1, p2 in focus_pairs:
    key = tuple(sorted([p1, p2]))
    # 找这个组合
    found = None
    for c in combo_stats:
        if c['pair'] == key:
            found = c
            break
    if found:
        pair_str = '/'.join(found['pair'])
        chem_str = f'{found["chemistry"]*100:+.1f}%'
        tag = '🔥黄金' if found['chemistry'] > 0.15 else ('⚠️相克' if found['chemistry'] < -0.15 else '➖正常')
        print(f'  {pair_str:<22} | {found["n"]:>3}局 {found["wins"]:>2}胜{found["losses"]:>2}负 | 实际{found["actual_wr"]*100:>5.1f}% vs 预测{found["avg_pred"]*100:>5.1f}% | 化学{chem_str:>8} | {tag}')
    else:
        # 看看有没有记录
        recs = combo_raw.get(key, [])
        if recs:
            wins = sum(1 for r in recs if r[2])
            print(f'  {p1}/{p2:<22} | {len(recs):>3}局（不足2局，暂不统计）| {wins}胜{len(recs)-wins}负')
        else:
            print(f'  {p1}/{p2:<22} | 历史上还没组过双打')

# ========== 5. 组合级数据到底够不够？==========
print()
print('='*120)
print('📊 【样本充足性分析】到底要不要做「组合级建模」？'.center(120))
print('='*120)
ns = [2, 4, 6, 8, 10, 15, 20, 30]
for threshold in ns:
    cnt = sum(1 for c in combo_stats if c['n'] >= threshold)
    print(f'  出场≥{threshold:>2}局的组合数：{cnt:>4} 组')
print()
print('结论：目前数据下，≥4局的组合才', sum(1 for c in combo_stats if c['n'] >= 4), '组，')
print('      ≥10局的组合才', sum(1 for c in combo_stats if c['n'] >= 10), '组，')
print('      纯组合级建模样本太稀疏，容易过拟合（2局100%胜率不代表真强）。')
print()
print('👉 推荐策略：')
print('   方案A：继续用单人θ乘积做基础预测 + 「化学修正项」（当某组合有≥6局数据时，用化学指数加权修正）')
print('   方案B：等数据积累到≥50组组合有≥10局，再考虑纯组合级模型（比如组合级BT或Logistic Regression带组合特征）')

# ========== 6. 推荐：用化学指数修正你问的那组预测 ==========
print()
print('='*120)
print('🧮 【用化学指数修正】你问的：苏大哲+陈财贵 VS 刘继宇+陈顺星'.center(120))
print('='*120)
pair_a = tuple(sorted(['苏大哲', '陈财贵']))
pair_b = tuple(sorted(['刘继宇', '陈顺星']))

# 查两个组合各自的化学指数
chem_a = 0
chem_b = 0
for c in combo_stats:
    if c['pair'] == pair_a:
        chem_a = c['chemistry']
        print(f'  组合A 苏大哲/陈财贵：历史{c["n"]}局，化学指数 = {chem_a*100:+.1f}%（{c["wins"]}胜{c["losses"]}负）')
    if c['pair'] == pair_b:
        chem_b = c['chemistry']
        print(f'  组合B 刘继宇/陈顺星：历史{c["n"]}局，化学指数 = {chem_b*100:+.1f}%（{c["wins"]}胜{c["losses"]}负）')

# 原始预测
Ta = math.prod(theta[p] for p in pair_a)
Tb = math.prod(theta[p] for p in pair_b)
p_raw = Ta / (Ta + Tb)

# 化学修正（简单版：A的化学加成 - B的化学加成，权重按样本数衰减）
# 化学修正的可信度：n局越多越可信，用w = 1 - exp(-n/6) 做S型加权
def chem_weight(n): return 1 - math.exp(-n/6)
wa = chem_weight(next((c['n'] for c in combo_stats if c['pair'] == pair_a), 0))
wb = chem_weight(next((c['n'] for c in combo_stats if c['pair'] == pair_b), 0))
adjust = chem_a * wa - chem_b * wb
p_adj = max(0.01, min(0.99, p_raw + adjust))

print()
print(f'  原始BT预测：      苏大哲/陈财贵 胜率 = {p_raw*100:.1f}%')
print(f'  化学修正（±{adjust*100:+.1f}%）：修正后胜率 = {p_adj*100:.1f}%')
if abs(adjust) < 0.02:
    print('  修正幅度很小，这两组的化学效应和普通组合差不多～')
elif adjust > 0:
    print('  🔥 修正后胜率更高，苏大哲+陈财贵是黄金搭档！')
else:
    print('  ⚠️ 修正后胜率下降，组合有相克迹象')
