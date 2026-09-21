#!/usr/bin/env python3
"""
Elo rating + Bradley-Terry model 对比实验
对 2026-08-31 match_data.json 跑4种排序并输出对比
"""
import json
import math
import sys
from collections import defaultdict

DATA = json.load(open(sys.argv[1])) if len(sys.argv) > 1 else json.load(open('scores/20260831/match_data.json'))

# ====== 工具：展开所有 48 局单局结果（双人组合 -> 团队 avg 实力）======
sets = []  # (team_a_list, team_b_list, a_win: bool, score_a, score_b)
players = set()
for m in DATA['matches']:
    a, b = m['team_a'], m['team_b']
    for p in a + b:
        players.add(p)
    # score_a: 局1 a:b；score_b: 局2 a:b
    for k in (0, 1):
        s = [m['score_a'], m['score_b']][k]
        sa, sb = map(int, s.split(':'))
        sets.append((a, b, sa > sb, sa, sb))

players = sorted(players)
N = len(players)
idx = {p: i for i, p in enumerate(players)}

# ====== 方法 1：纯胜率（基础对比）======
def pure_winrate_rank():
    w = defaultdict(int); l = defaultdict(int)
    for ta, tb, a_win, _, _ in sets:
        for p in ta:
            w[p] += 1 if a_win else 0; l[p] += 0 if a_win else 1
        for p in tb:
            w[p] += 1 if not a_win else 0; l[p] += 0 if not a_win else 1
    rank = []
    for p in players:
        t = w[p]+l[p]
        rank.append((p, w[p], l[p], t, w[p]/t if t else 0, net_of(p)))
    rank.sort(key=lambda x: (-x[4], -x[5]))
    return rank

def net_of(p):
    net = 0
    for ta, tb, _, sa, sb in sets:
        d = sa - sb
        if p in ta: net += d
        elif p in tb: net -= d
    return net

# ====== 方法 2：Bradley-Terry（最大似然，迭代求解）======
"""
双人组的胜概率 = (θ_a1*θ_a2) / (θ_a1*θ_a2 + θ_b1*θ_b2)
采用 MM (Minorization-Maximization) / 简单迭代缩放
"""
def bradley_terry(max_iter=5000, tol=1e-7, team_combine='prod'):
    theta = {p: 1.0 for p in players}
    for it in range(max_iter):
        new = {p: 0.0 for p in players}
        wins = defaultdict(float)
        match_sum = defaultdict(float)
        for ta, tb, a_win, _, _ in sets:
            # team strength
            if team_combine == 'prod':
                Ta = math.prod(theta[p] for p in ta)
                Tb = math.prod(theta[p] for p in tb)
            elif team_combine == 'mean':
                Ta = sum(theta[p] for p in ta)/len(ta)
                Tb = sum(theta[p] for p in tb)/len(tb)
            elif team_combine == 'sum':
                Ta = sum(theta[p] for p in ta)
                Tb = sum(theta[p] for p in tb)
            denom = Ta + Tb
            # expected contribution per player
            if a_win:
                for p in ta: wins[p] += 1.0
            else:
                for p in tb: wins[p] += 1.0
            # E[matches] per player for denominator
            # Using the BT update: θ_i^{new} ∝ W_i / Σ_{contests j involving i} (n_ij / (θ_i sum_team + θ_opp sum_team))
            # Simpler pairwise-like approach for doubles: for each set, distribute 'match counts' to each player
            if team_combine == 'prod':
                # for each A player, match_sum contribution = (|A| * Ta) / (Ta + Tb) ... but split by team
                for p in ta: match_sum[p] += len(ta) * Ta / denom / len(ta)  # just 1/denom per contest pair? Use simpler: 1 per player
                for p in tb: match_sum[p] += len(tb) * Tb / denom / len(tb)
            else:
                for p in ta: match_sum[p] += Ta / denom
                for p in tb: match_sum[p] += Tb / denom
        # 更新（同BT迭代缩放：θ_new ∝ wins / (match_sum / θ_old) ... simpler: Newton-like for pairwise, here for doubles approximate）
        # Using Zermelo/Bradley-Terry multiplicative update:
        # new_theta_i = theta_i * (W_i / N_i_expected)^(alpha)
        for p in players:
            if match_sum[p] > 0:
                # expected wins for player p = match_sum[p] (sum of P(team containing p wins) per contest)
                new[p] = theta[p] * (wins[p] / match_sum[p]) if match_sum[p] > 1e-12 else theta[p]
            else:
                new[p] = theta[p]
        # 归一化（几何平均为1）
        gmean = math.exp(sum(math.log(max(v,1e-9)) for v in new.values()) / N)
        for p in new: new[p] /= gmean
        # 检查收敛
        delta = max(abs(math.log(new[p]/theta[p])) for p in theta if theta[p]>0)
        theta = new
        if delta < tol:
            #print(f'BT team_combine={team_combine} converged at iter {it+1}')
            break
    # 转化成类似 Elo 的值（400*log10 scale）
    return {p: 400*math.log10(max(theta[p], 1e-9)) + 1000 for p in players}

# ====== 方法 3：Elo（双打：团队 Elo = 平均；每局更新）======
def elo_doubles(K=32, init=1000, team_combine='avg'):
    r = {p: float(init) for p in players}
    for ta, tb, a_win, sa, sb in sets:
        if team_combine == 'avg':
            Ra = sum(r[p] for p in ta)/len(ta)
            Rb = sum(r[p] for p in tb)/len(tb)
        elif team_combine == 'sum':
            Ra = sum(r[p] for p in ta)
            Rb = sum(r[p] for p in tb)
        Ea = 1/(1 + 10**((Rb - Ra)/400))
        Eb = 1 - Ea
        Sa = 1.0 if a_win else 0.0
        Sb = 1 - Sa
        # 每队每人更新：K*(S-E)/n_teammates（或直接分摊）
        dA = K*(Sa - Ea); dB = K*(Sb - Eb)
        # 按净胜分轻微缩放（让大胜多更新一点点）
        margin = abs(sa - sb)
        mscale = 1 + (margin-1)*0.03 if margin >= 2 else 1
        mscale = min(mscale, 1.5)
        dA *= mscale; dB *= mscale
        for p in ta: r[p] += dA/len(ta)
        for p in tb: r[p] += dB/len(tb)
    return r

# ====== 运行所有模型 ======
pure = pure_winrate_rank()
pure_rank = {p:i+1 for i,(p,*_) in enumerate(pure)}
pure_wr = {p: (w,l,t,wr,nt) for p,w,l,t,wr,nt in pure}

bt_prod = bradley_terry(team_combine='prod')
bt_mean = bradley_terry(team_combine='mean')
bt_sum = bradley_terry(team_combine='sum')

elo_avg = elo_doubles(K=32, team_combine='avg')
elo_sum = elo_doubles(K=32, team_combine='sum')

# ====== 输出对比表 ======
def sort_rank(ratings):
    s = sorted(ratings.items(), key=lambda x: -x[1])
    return {p:i+1 for i,(p,_) in enumerate(s)}

bt_prod_r = sort_rank(bt_prod)
bt_mean_r = sort_rank(bt_mean)
bt_sum_r = sort_rank(bt_sum)
elo_avg_r = sort_rank(elo_avg)
elo_sum_r = sort_rank(elo_sum)

# 加载加权排名（来自 weighted_rank 输出）
# 这里重新简单跑一下v3公式结果作为对照
# 不过直接用脚本 import 麻烦，就手动列出之前的加权排名顺序（来自加权输出）
# 加权排名顺序：1刘海锐 2陈财贵 3范智强 4李佳琳 5刘继宇 6陈顺星 7苏大哲 8唐英武 9徐越 10严勇文 11林小连 12王小波 13罗琴荩 14卢志辉 15王苏丹 16陈小洪 17董广博
weighted = ["刘海锐","陈财贵","范智强","李佳琳","刘继宇","陈顺星","苏大哲","唐英武","徐越","严勇文","林小连","王小波","罗琴荩","卢志辉","王苏丹","陈小洪","董广博"]
weighted_r = {p:i+1 for i,p in enumerate(weighted)}

print('='*160)
print(f'{"排名对比（17人，48局双打）":^160}')
print('='*160)
header = f'{"纯胜率":>6}{"v3加权":>8}{"BT乘积":>8}{"BT均值":>8}{"BT求和":>8}{"Elo均值":>8}{"Elo求和":>8}  {"选手":<8}'
print(header)
print('-'*160)

# 按 v3加权 顺序打印
for p in weighted:
    print(f'{pure_rank[p]:>4}{weighted_r[p]:>8}{bt_prod_r[p]:>8}{bt_mean_r[p]:>8}{bt_sum_r[p]:>8}{elo_avg_r[p]:>8}{elo_sum_r[p]:>8}  {p:<8}')

print()
print('='*160)
print('详细分数字段（rating/胜率）：')
print('='*160)
print(f'{"选手":<8}{"纯WR%":>8}{"纯净胜":>8}{"BT乘积":>9}{"BT均值":>9}{"BT求和":>9}{"Elo均值":>9}{"Elo求和":>9}{"加权排名":>8}')
print('-'*160)
for p in weighted:
    w,l,t,wr,nt = pure_wr[p]
    print(f'{p:<8}{wr*100:>7.1f}%{nt:>+8}{bt_prod[p]:>9.0f}{bt_mean[p]:>9.0f}{bt_sum[p]:>9.0f}{elo_avg[p]:>9.0f}{elo_sum[p]:>9.0f}{weighted_r[p]:>8}')

# ====== 关键洞察 1：被低估最多的（纯胜率 vs Elo均值）======
print()
print('='*160)
print('【模型差异分析】纯胜率 vs Elo均值 — 谁被纯胜率严重低估/高估？')
print('='*160)
diff_elo_pure = sorted([(elo_avg_r[p] - pure_rank[p], p, pure_rank[p], elo_avg_r[p]) for p in players])
print('低估最多（Elo排名 远超 纯胜率排名，负数越大越被低估）：')
for d,p,pr,er in diff_elo_pure[:6]:
    print(f'   {p:<8}  纯胜率#{pr}  Elo#{er}  差 {d:+d}')
print('高估最多（Elo排名 远低于 纯胜率排名，正数越大越被高估）：')
for d,p,pr,er in reversed(diff_elo_pure[-6:]):
    print(f'   {p:<8}  纯胜率#{pr}  Elo#{er}  差 {d:+d}')

# ====== 关键洞察 2：Bradley-Terry 与 Elo 的一致性 ======
from scipy.stats import spearmanr  # 简单算相关性，如果可用
print()
print('='*160)
print('【Spearman 秩相关矩阵】（1=完全一致，0=完全无关）')
print('='*160)
labels = ['纯胜率', 'v3加权', 'BT乘积', 'BT均值', 'Elo均值']
lists = [
    [pure_rank[p] for p in players],
    [weighted_r[p] for p in players],
    [bt_prod_r[p] for p in players],
    [bt_mean_r[p] for p in players],
    [elo_avg_r[p] for p in players],
]
try:
    import numpy as np
    corrs = [[spearmanr(lists[i], lists[j])[0] for j in range(len(lists))] for i in range(len(lists))]
    hdr = ' '*10 + ''.join(f'{l:>9}' for l in labels)
    print(hdr)
    for i,l in enumerate(labels):
        row = f'{l:<10}' + ''.join(f'{corrs[i][j]:>9.3f}' for j in range(len(labels)))
        print(row)
except ImportError:
    print('(scipy/numpy未安装，跳过相关矩阵)')

# ====== 关键洞察 3：董广博 / 罗琴荩 的排名变化（用户关心） ======
print()
print('='*160)
print('【用户关注选手】罗琴荩、董广博在各模型中的排名')
print('='*160)
for name in ['罗琴荩','董广博']:
    print(f'  {name}: 纯胜率#{pure_rank[name]}  v3加权#{weighted_r[name]}  BT#{bt_mean_r[name]}  Elo#{elo_avg_r[name]}')
