#!/usr/bin/env python3
"""
全量历史数据 Bradley-Terry + Elo 排名
扫描 scores/*/match_data.json 中所有日期，合并后跑全局概率模型
"""
import json
import math
import glob
import os
from collections import defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__)) + '/..'
ROOT = os.path.normpath(ROOT)

# ============= 1. 加载所有历史 match_data =============
json_files = sorted(glob.glob(f'{ROOT}/scores/*/match_data.json'))
# 排除 history/ 子目录
json_files = [f for f in json_files if '/history/' not in f]
# 处理带空格的目录名（" 20260824"）
json_files = [f for f in json_files if os.path.isfile(f)]

print(f'加载到 {len(json_files)} 个历史 match_data.json:')
datasets = []
all_sets = []   # 全局：(date, team_a, team_b, a_win, sa, sb)
players = set()
date_players = defaultdict(set)  # 每个日期出场的选手
date_set_count = defaultdict(int)

for fp in json_files:
    try:
        data = json.load(open(fp))
    except Exception as e:
        print(f'  跳过 {fp}: {e}')
        continue
    date = data.get('match_date') or data.get('date') or '???'
    desc = data.get('description','')[:20]
    n_matches = len(data.get('matches', []))
    n_sets = 0
    for m in data.get('matches', []):
        a = m['team_a']; b = m['team_b']
        for p in a+b:
            players.add(p)
            date_players[date].add(p)
        for sk in (0, 1):
            s = [m['score_a'], m['score_b']][sk]
            try:
                sa, sb = map(int, s.split(':'))
            except:
                continue
            # 跳过双方都未达15且未赛完的？不，BT只看胜负，不管比分。
            if sa == sb:
                continue  # 平局跳过
            n_sets += 1
            date_set_count[date] += 1
            all_sets.append((date, a, b, sa > sb, sa, sb))
    datasets.append((date, desc, n_matches, n_sets, len(date_players[date])))
    print(f'  [{date}] {desc:20s} {n_matches:>2}场 {n_sets:>3}局 {len(date_players[date]):>2}人')

print(f'\n合计：{len(all_sets)} 局，{len(players)} 位选手\n')

players = sorted(players)
N = len(players)

# ============= 2. 纯胜率总榜 =============
w = defaultdict(int); l = defaultdict(int); net = defaultdict(int)
for date, ta, tb, aw, sa, sb in all_sets:
    d = sa - sb
    for p in ta:
        if aw: w[p]+=1
        else: l[p]+=1
        net[p] += d
    for p in tb:
        if not aw: w[p]+=1
        else: l[p]+=1
        net[p] -= d

pure_stats = {}
for p in players:
    t = w[p]+l[p]
    wr = w[p]/t if t else 0
    pure_stats[p] = (w[p], l[p], t, wr, net[p])
pure_sorted = sorted(players, key=lambda p: (-pure_stats[p][3], -pure_stats[p][4]))
pure_rank = {p:i+1 for i,p in enumerate(pure_sorted)}

# ============= 3. Bradley-Terry（全局 MLE，team=乘积，稳定版）=============
def bt_full(team_combine='prod', max_iter=20000, tol=1e-8):
    theta = {p: 1.0 for p in players}
    for it in range(max_iter):
        wins = defaultdict(float); denom = defaultdict(float)
        for date, ta, tb, aw, _, _ in all_sets:
            if team_combine == 'prod':
                Ta = math.prod(theta[p] for p in ta)
                Tb = math.prod(theta[p] for p in tb)
            else:  # mean
                Ta = sum(theta[p] for p in ta)/len(ta)
                Tb = sum(theta[p] for p in tb)/len(tb)
            D = Ta + Tb + 1e-20
            if aw:
                for p in ta: wins[p] += 1.0
            else:
                for p in tb: wins[p] += 1.0
            if team_combine == 'prod':
                for p in ta: denom[p] += Ta / D
                for p in tb: denom[p] += Tb / D
            else:
                for p in ta: denom[p] += 1.0 * Ta / D
                for p in tb: denom[p] += 1.0 * Tb / D
        new = {}
        for p in players:
            if denom[p] > 1e-15:
                new[p] = theta[p] * (wins[p] / denom[p])
            else:
                new[p] = theta[p]
        gmean = math.exp(sum(math.log(max(v, 1e-20)) for v in new.values()) / N)
        for p in new: new[p] = max(new[p] / gmean, 1e-20)
        # 收敛检测（几何差）
        diff = 0.0
        for p in theta:
            if theta[p] > 0:
                d = abs(math.log(new[p] / theta[p]))
                if d > diff: diff = d
        theta = new
        if diff < tol:
            #print(f'BT {team_combine} 收敛在迭代 {it+1}')
            break
    return {p: 400 * math.log10(theta[p]) + 1000 for p in players}

bt_rating = bt_full('prod')
bt_sorted = sorted(players, key=lambda p: -bt_rating[p])
bt_rank = {p:i+1 for i,p in enumerate(bt_sorted)}

# ============= 4. Elo（全局，双打团队平均）=============
def elo_full(K=32, init=1000):
    r = {p: float(init) for p in players}
    for date, ta, tb, aw, sa, sb in all_sets:
        Ra = sum(r[p] for p in ta)/len(ta)
        Rb = sum(r[p] for p in tb)/len(tb)
        Ea = 1/(1 + 10**((Rb-Ra)/400))
        Sa = 1.0 if aw else 0.0
        d = abs(sa-sb)
        mscale = 1 + min((d-1)*0.03, 0.5) if d>=2 else 1
        dA = K * mscale * (Sa - Ea) / len(ta)
        dB = - K * mscale * (Sa - Ea) / len(tb)
        for p in ta: r[p] += dA
        for p in tb: r[p] += dB
    return r

elo_rating = elo_full()
elo_sorted = sorted(players, key=lambda p: -elo_rating[p])
elo_rank = {p:i+1 for i,p in enumerate(elo_sorted)}

# ============= 5. 仅 0831 的独立 BT/Elo 排名（和全局对比）=============
sets_0831 = [x for x in all_sets if x[0] == '2026-08-31']
players_0831 = sorted(set(p for s in sets_0831 for team in s[1:3] for p in team))

def bt_subset(subset_sets, subset_players, tc='prod'):
    theta = {p: 1.0 for p in subset_players}
    n = len(subset_players)
    for it in range(15000):
        wins = defaultdict(float); denom = defaultdict(float)
        for date, ta, tb, aw, _, _ in subset_sets:
            if tc == 'prod':
                Ta = math.prod(theta[p] for p in ta)
                Tb = math.prod(theta[p] for p in tb)
            else:
                Ta = sum(theta[p] for p in ta)/len(ta)
                Tb = sum(theta[p] for p in tb)/len(tb)
            D = Ta + Tb + 1e-20
            if aw:
                for p in ta: wins[p] += 1.0
            else:
                for p in tb: wins[p] += 1.0
            for p in ta: denom[p] += Ta / D
            for p in tb: denom[p] += Tb / D
        new = {}
        for p in subset_players:
            new[p] = theta[p] * (wins[p] / denom[p]) if denom[p] > 1e-15 else theta[p]
        gmean = math.exp(sum(math.log(max(v,1e-20)) for v in new.values()) / n)
        for p in new: new[p] = max(new[p]/gmean, 1e-20)
        diff = max(abs(math.log(new[p]/theta[p])) for p in theta if theta[p]>0)
        theta = new
        if diff < 1e-8: break
    return {p: 400*math.log10(theta[p]) + 1000 for p in subset_players}

bt0831 = bt_subset(sets_0831, players_0831)
bt0831_sorted = sorted(players_0831, key=lambda p: -bt0831[p])
bt0831_rank = {p:i+1 for i,p in enumerate(bt0831_sorted)}

# ============= 6. 逐日 BT rating 演化（仅跟踪经常出场的选手）=============
# 按时间顺序累积训练，每跑完一个日期记录一次 rating
sorted_dates = sorted(set(x[0] for x in all_sets))
# 按日期分组 sets
by_date = defaultdict(list)
for s in all_sets:
    by_date[s[0]].append(s)

# 初始化，然后按日期顺序跑
evo_theta = {p: 1.0 for p in players}
evo_history = defaultdict(list)  # player -> [(date, rating), ...]

for d in sorted_dates:
    # 用该日期的 sets 迭代几轮 bt 更新（增量）
    local_sets = by_date[d]
    # 只对出场选手做迭代
    local_players = sorted(set(p for s in local_sets for team in s[1:3] for p in team))
    for it in range(800):
        wins = defaultdict(float); denom = defaultdict(float)
        for date, ta, tb, aw, _, _ in local_sets:
            Ta = math.prod(evo_theta[p] for p in ta)
            Tb = math.prod(evo_theta[p] for p in tb)
            D = Ta + Tb + 1e-20
            if aw:
                for p in ta: wins[p] += 1.0
            else:
                for p in tb: wins[p] += 1.0
            for p in ta: denom[p] += Ta / D
            for p in tb: denom[p] += Tb / D
        maxdiff = 0.0
        for p in local_players:
            if denom[p] > 1e-15 and evo_theta[p] > 1e-30:
                new_v = max(evo_theta[p] * (wins[p] / denom[p]), 1e-30)
                dlog = abs(math.log(new_v / evo_theta[p]))
                if dlog > maxdiff: maxdiff = dlog
            else:
                new_v = max(evo_theta[p], 1e-30)
            evo_theta[p] = new_v
        if maxdiff < 1e-6:
            break
    # 归一化（保持几何均值为1，全局归一化）
    gm = math.exp(sum(math.log(max(evo_theta[p], 1e-30)) for p in evo_theta)/N)
    for p in evo_theta: evo_theta[p] = max(evo_theta[p]/gm, 1e-30)
    for p in local_players:
        rt = 400 * math.log10(evo_theta[p]) + 1000
        evo_history[p].append((d, rt))

# ============= 7. 输出总排名 =============
print('=' * 160)
print(f'全量历史数据 BT/Elo 总排名  ({len(all_sets)}局 / {len(sorted_dates)}个训练日 / {len(players)}位选手)'.center(160))
print('=' * 160)
hdr = f'{"全局BT":>6}{"全局Elo":>8}{"纯胜率":>8}{"BT0831":>8}{"差值BT":>8}{"总局":>6}{"胜":>5}{"负":>5}{"WR%":>7}{"纯净胜":>9}  {"选手":<8}'
print(hdr)
print('-'*160)
# 按全局BT排序输出（总局数>=cutoff的才纳入排名）
import sys
cutoff = int(sys.argv[1]) if len(sys.argv) > 1 else 30
shown = [p for p in bt_sorted if pure_stats[p][2] >= cutoff]
skipped = [p for p in bt_sorted if pure_stats[p][2] < cutoff]
for p in shown:
    W,L,T,WR,NT = pure_stats[p]
    bt08 = bt0831_rank.get(p, '-')
    diff = f'{bt_rank[p]-bt0831_rank[p]:+d}' if p in bt0831_rank else '-'
    print(f'{bt_rank[p]:>5}{elo_rank[p]:>8}{pure_rank[p]:>8}{bt08:>8}{diff:>8}{T:>6}{W:>5}{L:>5}{WR*100:>6.1f}%{NT:>+9}  {p:<8}')

if skipped:
    print()
    print(f'（以下选手出场<{cutoff}局，样本不足不参与排名）：', end='')
    print('、'.join(f'{p}({pure_stats[p][2]}局)' for p in skipped))

# ============= 8. 用户关注选手详细分析 =============
print()
print('='*160)
print('【重点选手】罗琴荩 / 董广博 全局数据 vs 仅0831数据')
print('='*160)
for name in ['罗琴荩', '董广博']:
    W,L,T,WR,NT = pure_stats[name]
    print(f'\n=== {name} 全局（{T}局，{len(sorted_dates)}个训练日累计）===')
    print(f'  全局战绩：{W}胜 {L}负  WR {WR*100:.1f}%  净胜分 {NT:+d}')
    print(f'  全局BT排名：#{bt_rank[name]}  rating {bt_rating[name]:.0f}')
    print(f'  全局Elo排名：#{elo_rank[name]}  rating {elo_rating[name]:.0f}')
    print(f'  全局纯胜率排名：#{pure_rank[name]}')
    if name in bt0831_rank:
        W08 = sum(1 for s in sets_0831 if name in s[1] and s[3] or name in s[2] and not s[3])
        T08 = sum(1 for s in sets_0831 if name in s[1] or name in s[2])
        L08 = T08 - W08
        NT08 = 0
        for s in sets_0831:
            d = s[4] - s[5]
            if name in s[1]: NT08 += d
            elif name in s[2]: NT08 -= d
        print(f'  --- 仅 0831 当日（{T08}局）---')
        print(f'    0831战绩：{W08}胜 {L08}负  WR {W08/T08*100:.1f}%  净胜分 {NT08:+d}')
        print(f'    0831当日BT排名：#{bt0831_rank[name]}（全局BT#%d → 当日差 %+d 名）' % (bt_rank[name], bt_rank[name]-bt0831_rank[name]))
    # 逐日 rating 走势
    print(f'  逐训练日 rating 走势（BT rating，时间由旧→新）：')
    hist = evo_history[name]
    if hist:
        for i, (d, rt) in enumerate(hist):
            delta = ''
            if i > 0:
                dlt = rt - hist[i-1][1]
                delta = f' ({dlt:+.0f})'
            print(f'    {d}: {rt:.0f}{delta}')
    else:
        print(f'    (无历史数据)')

# ============= 9. 最大发现：前后排名落差 Top10 =============
print()
print('='*160)
print('【全局BT vs 纯胜率】落差最大的选手（说明纯胜率严重低估/高估）')
print('='*160)
diffs = sorted((bt_rank[p]-pure_rank[p], p) for p in shown)
print(f'低估最多（全局BT排名远优于纯胜率，负值越大 = 越被纯胜率冤枉）Top 8：')
for d,p in diffs[:8]:
    W,L,T,WR,NT = pure_stats[p]
    print(f'   {p:<8}  纯胜率#{pure_rank[p]}  全局BT#{bt_rank[p]}  提升 {-d:>2}名  | {W}-{L}={T}局 WR {WR*100:.0f}%  净胜 {NT:+d}')
print(f'高估最多（全局BT排名远低于纯胜率，正值越大 = 纯胜率水）Top 8：')
for d,p in reversed(diffs[-8:]):
    W,L,T,WR,NT = pure_stats[p]
    print(f'   {p:<8}  纯胜率#{pure_rank[p]}  全局BT#{bt_rank[p]}  下滑 {d:>2}名  | {W}-{L}={T}局 WR {WR*100:.0f}%  净胜 {NT:+d}')

# ============= 10. 和 v3加权 最近一次(0831) 对比 =============
v3_0831 = ["刘海锐","陈财贵","范智强","李佳琳","刘继宇","陈顺星","苏大哲","唐英武","徐越","严勇文","林小连","王小波","罗琴荩","卢志辉","王苏丹","陈小洪","董广博"]
print()
print('='*160)
print(f'【仅看 0831当日常出场】 纯胜率 vs 全局BT(含历史) vs 当日BT(仅0831) vs v3加权')
print('='*160)
hdr = f'{"v3加权":>6}{"纯胜率0831":>11}{"全局BT历史":>11}{"当日BT0831":>13}{"全局Elo":>9}  {"选手":<8}'
print(hdr)
print('-'*160)
for i,p in enumerate(v3_0831):
    # 纯胜率只看0831
    w08=l08=n08=0
    for s in sets_0831:
        d = s[4]-s[5]
        if p in s[1]:
            aw=s[3]; w08+=1 if aw else 0; l08 += 0 if aw else 1; n08 += d
        elif p in s[2]:
            aw=s[3]; w08+=0 if aw else 1; l08 += 1 if aw else 0; n08 -= d
    t08 = w08+l08
    wr08 = (w08/t08*100) if t08 else 0
    def sort_by_rank_for0831(rankings):
        # 用全局BT对0831当日出场选手排一个0831内的名次
        items = [(rankings.get(x,999),x) for x in players_0831]
        items.sort()
        return {x:i+1 for i,(r,x) in enumerate(items)}
    gbt_rank_in0831 = sort_by_rank_for0831({x: bt_rating[x] for x in players_0831})
    gelo_rank_in0831 = sort_by_rank_for0831({x: elo_rating[x] for x in players_0831})
    pure0831_sorted = sorted(players_0831, key=lambda x: -(pure_stats[x][3] if pure_stats[x][2]>0 else -1))
    pure0831_rank = {x:i+1 for i,x in enumerate(pure0831_sorted)}
    print(f'{i+1:>5}{pure0831_rank.get(p,99):>11}{gbt_rank_in0831.get(p,99):>11}{bt0831_rank.get(p,99):>13}{gelo_rank_in0831.get(p,99):>9}  {p:<8}')
