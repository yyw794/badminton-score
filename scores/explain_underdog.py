#!/usr/bin/env python3
"""
给团队解释用的「冤种选手」分析脚本：
对比王小波/陈小洪 vs 同级别的「胜率漂亮但水」的选手
重点拆：搭档质量、对手质量、比分惜败率
"""
import json, math, glob, os
from collections import defaultdict

ROOT = os.path.normpath(os.path.dirname(__file__) + '/..')
json_files = sorted([f for f in glob.glob(f'{ROOT}/scores/*/match_data.json') if '/history/' not in f and os.path.isfile(f)])

# ============ 1. 先算全局 BT rating（复用原逻辑）============
all_sets = []
players = set()
for fp in json_files:
    data = json.load(open(fp))
    date = data.get('match_date') or '?'
    for m in data.get('matches', []):
        a, b = m['team_a'], m['team_b']
        for p in a+b: players.add(p)
        for sk in (0,1):
            s = [m['score_a'], m['score_b']][sk]
            try: sa, sb = map(int, s.split(':'))
            except: continue
            if sa == sb: continue
            all_sets.append((date, a, b, sa>sb, sa, sb))
players = sorted(players)
N = len(players)

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
    pure_stats[p] = (w[p], l[p], t, (w[p]/t if t else 0), net[p])
pure_sorted = sorted(players, key=lambda p: (-pure_stats[p][3], -pure_stats[p][4]))
pure_rank = {p:i+1 for i,p in enumerate(pure_sorted)}

# 全局BT（乘积）
theta = {p: 1.0 for p in players}
for it in range(20000):
    wins_d = defaultdict(float); denom_d = defaultdict(float)
    for date, ta, tb, aw, _, _ in all_sets:
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
    diff = max(abs(math.log(new[p]/theta[p])) for p in theta if theta[p]>0)
    theta = new
    if diff < 1e-8: break
bt_rating = {p: 400*math.log10(theta[p])+1000 for p in players}
bt_sorted = sorted(players, key=lambda p: -bt_rating[p])
bt_rank = {p:i+1 for i,p in enumerate(bt_sorted)}

# ============ 2. 针对每位目标选手，做搭档/对手/比分三维度拆解 ============
team_rating = lambda team: sum(bt_rating[p] for p in team)/len(team)  # 团队平均实力

def player_breakdown(name):
    stats = {'sets': 0, 'wins': 0, 'losses': 0,
             'partners': defaultdict(int),  # 搭档 -> 一起打的局数
             'partners_win': defaultdict(int),
             'partners_rank_total': 0,  # 搭档全局BT排名累计（算平均）
             'opp_rank_total': 0,       # 对手平均BT排名累计（4个对手 per 双打局）
             'opp_count': 0,
             'scores_close_loss': 0,    # 输但分差 <=3 （惜败）
             'scores_beatdown_loss': 0, # 输分差 >=7 （惨败）
             'score_diffs': [],
             'upset_wins': 0,           # 对手BT排名比我方高很多还赢了
             }
    for date, ta, tb, aw, sa, sb in all_sets:
        if name not in ta and name not in tb:
            continue
        stats['sets'] += 1
        d = sa - sb
        my_team, opp_team = (ta, tb) if name in ta else (tb, ta)
        my_win = aw if name in ta else (not aw)
        if my_win: stats['wins'] += 1
        else: stats['losses'] += 1
        stats['score_diffs'].append(d if name in ta else -d)
        # 搭档数据
        for p in my_team:
            if p == name: continue
            stats['partners'][p] += 1
            if my_win: stats['partners_win'][p] += 1
            stats['partners_rank_total'] += bt_rank[p]
            stats['opp_count'] += 1  # 每局搭档数
        # 对手数据
        for p in opp_team:
            stats['opp_rank_total'] += bt_rank[p]
            stats['opp_count'] += 1
        # 比分分析
        diff = abs(sa - sb)
        if not my_win:
            if diff <= 3: stats['scores_close_loss'] += 1
            elif diff >= 7: stats['scores_beatdown_loss'] += 1
        # 逆袭胜：我方团队平均rating < 对手，但赢了
        my_t_avg = team_rating(my_team)
        op_t_avg = team_rating(opp_team)
        if my_win and my_t_avg + 30 < op_t_avg:  # rating 差30 = 对手高一个档次
            stats['upset_wins'] += 1
    return stats

# ============ 3. 找「反例选手」: 纯胜率高但BT排名差（虐菜型），用于对比 ============
deltas = [(bt_rank[p] - pure_rank[p], p) for p in players if pure_stats[p][2] >= 30]
deltas.sort()
overrated = [x for x in reversed(deltas) if x[0] < 0][:3]  # BT排名比纯胜率低的（虐菜型）
underrated = [x for x in deltas if x[0] > 0][:5]          # BT排名高的（被冤枉的）

print('='*100)
print('🎯 对比对象：')
print('='*100)
print(f'被冤枉的：王小波(纯#30→BT#15 +15)、陈小洪(纯#23→BT#13 +10)')
print(f'对比用的「运气好/虐菜型」：{ "、".join(f"{p}(纯#{pure_rank[p]}→BT#{bt_rank[p]} {d:+d})" for d,p in overrated if pure_stats[p][2]>=30) }')
print()

# ============ 4. 王小波、陈小洪、以及同级虐菜选手的三维度对比 ============
# 选一位纯胜率接近但BT排名低的（虐菜型）作为对照组
# 王小波纯胜率35%排名30，找纯胜率接近但BT排名差的：比如滕菲纯34.7%排29 vs BT#22；或者陈顺星纯36.5%排28 vs BT#20都不如他BT高
# 更明显的对照组：徐越纯50% WR 17 → BT #25 (排名掉8名) 这个是虐菜+当天超常的典型

compare_targets = ['王小波', '陈小洪', '徐越', '林小连']
# 再加一个BT排名接近的「正常型」作为基准 严勇文纯#19 BT#12（提升7名，属于合理提升水平，可以对比王小波是不是超正常）
compare_targets += ['严勇文']

def print_header():
    hdr = f'{"指标":<22}' + ''.join(f'{p:>12}' for p in compare_targets)
    print(hdr)
    print('-' * (22 + 12*len(compare_targets)))

print_header()

data = {p: player_breakdown(p) for p in compare_targets}

def line(label, getter, fmt='{:>12}'):
    print(f'{label:<22}' + ''.join(fmt.format(getter(data[p])) for p in compare_targets))

line('总局数',        lambda d: d['sets'])
line('胜 / 负',       lambda d: f"{d['wins']}-{d['losses']}")
line('纯胜率%',       lambda d: f"{d['wins']/max(d['sets'],1)*100:.0f}%")
line('纯胜率排名',     lambda p: pure_rank[[q for q in compare_targets if data[q]==p][0]] if False else '-', fmt='{:>12}') # 占位
# 上面的写法太绕，直接手动写
print(f'{"纯胜率排名":<22}', end='')
for p in compare_targets: print(f'{pure_rank[p]:>12}', end='')
print()
print(f'{"全局BT排名":<22}', end='')
for p in compare_targets: print(f'{bt_rank[p]:>12}', end='')
print()
print(f'{"🔼 排名提升名":<22}', end='')
for p in compare_targets: print(f'{pure_rank[p]-bt_rank[p]:>+12}', end='')
print()
print()

# === 搭档质量 ===
print('—— 【维度1】搭档强弱：是不是总被塞弱队友？ ——')
print_header()
line('搭档组合数',       lambda d: len(d['partners']))
line('搭档平均全局BT排名', lambda d: f"#{d['partners_rank_total']/max(d['opp_count']//2,1):.0f}" if d['partners'] else '-')
# 搭档水平评级：<8=Top档 / 8-16=中 / >16=弱
def partner_tier(d):
    if not d['partners']: return '-'
    avg = d['partners_rank_total']/max(d['opp_count']//2,1)
    if avg <= 8: return '🟢 Top队友'
    elif avg <= 16: return '🟡 中等队友'
    else: return '🔴 弱队友'
line('搭档评级',        partner_tier, fmt='{:>12}')
# 和最弱队友一起的胜率 vs 和最强队友一起的胜率
def best_worst_partner(d):
    if not d['partners']: return '-'
    partners_sorted = sorted(d['partners'].items(), key=lambda x: -bt_rank[x[0]])  # BT排名数字越大越弱
    worst_p, worst_n = partners_sorted[0]  # 最差搭档
    best_p, best_n = partners_sorted[-1]  # 最好搭档
    w_with_worst = d['partners_win'].get(worst_p, 0) / max(worst_n,1) * 100
    w_with_best = d['partners_win'].get(best_p, 0) / max(best_n,1) * 100
    return f'好+{w_with_best:.0f}%/差{w_with_worst:.0f}%'
line('强搭档/弱搭档胜率', best_worst_partner, fmt='{:>12}')
print()

# === 对手质量 ===
print('—— 【维度2】对手强弱：是不是总是被分到打强敌？ ——')
print_header()
line('对手平均全局BT排名', lambda d: f"#{d['opp_rank_total']/max(d['opp_count'],1):.0f}" if d['opp_count'] else '-')
def opp_tier(d):
    if not d['opp_count']: return '-'
    avg = d['opp_rank_total']/d['opp_count']
    if avg <= 10: return '🔴 Top对手(硬仗多)'
    elif avg <= 18: return '🟡 中等对手'
    else: return '🟢 弱对手(虐菜)'
line('对手难度评级', opp_tier, fmt='{:>12}')
line('逆袭胜场（以弱胜强）', lambda d: d['upset_wins'])
print()

# === 比分质量 ===
print('—— 【维度3】比分质量：输球是惜败还是被吊打？赢球是险胜还是狂胜？ ——')
print_header()
line('总输局数',         lambda d: d['losses'])
line('惜败(分差≤3)',    lambda d: d['scores_close_loss'])
line('惨败(分差≥7)',    lambda d: d['scores_beatdown_loss'])
def loss_quality(d):
    # 惜败/(惜败+惨败)，越高说明输球都是差一点
    return f"{d['scores_close_loss']/max(d['scores_close_loss']+d['scores_beatdown_loss'],1)*100:.0f}%"
line('惜败占输球比例',  loss_quality)
line('分差中位数',      lambda d: f"{sorted(d['score_diffs'])[len(d['score_diffs'])//2]:+d}")
print()

# ============ 5. 王小波具体例子：挑几场典型的「带不动」比赛 ============
print()
print('='*100)
print('💥 王小波 典型冤案 Top 5（挑搭档最弱 + 输球分差≤5 的硬证据）：')
print('='*100)
cases = []
for date, ta, tb, aw, sa, sb in all_sets:
    if '王小波' not in ta and '王小波' not in tb: continue
    my_team, opp_team = (ta, tb) if '王小波' in ta else (tb, ta)
    my_win = aw if '王小波' in ta else (not aw)
    if my_win: continue  # 只看输的
    partner_rank = min(bt_rank[p] for p in my_team if p!='王小波')
    diff = abs(sa-sb)
    # 搭档比王小波弱很多 + 输分少
    partner_avg_rank = sum(bt_rank[p] for p in my_team if p!='王小波') / max(len(my_team)-1, 1)
    opp_avg_rank = sum(bt_rank[p] for p in opp_team) / len(opp_team)
    if diff <= 5 or partner_avg_rank > bt_rank['王小波'] + 5:
        cases.append((partner_avg_rank - opp_avg_rank, date, my_team, opp_team, sa, sb, diff, aw))
cases.sort()  # 纸面实力差距最大的在前（最冤的）
for i, c in enumerate(cases[:5]):
    _, date, mt, ot, sa, sb, diff, _ = c
    team_b = '王小波' in ot
    my_w = aw if not team_b else (not aw)
    pnames = '/'.join(mt)
    onames = '/'.join(ot)
    prt = ', '.join(f'{p}(BT#{bt_rank[p]})' for p in mt)
    oprt = ', '.join(f'{p}(BT#{bt_rank[p]})' for p in ot)
    print(f'  {i+1}. [{date}] 我方 {prt}')
    print(f'        vs  {oprt}')
    print(f'        比分: {sa}:{sb}  (输{diff}分，惜败💔)')
    print()

print()
print('='*100)
print('💥 陈小洪 典型冤案 Top 5：')
print('='*100)
cases2 = []
for date, ta, tb, aw, sa, sb in all_sets:
    if '陈小洪' not in ta and '陈小洪' not in tb: continue
    my_team, opp_team = (ta, tb) if '陈小洪' in ta else (tb, ta)
    my_win = aw if '陈小洪' in ta else (not aw)
    if my_win: continue
    partner_avg_rank = sum(bt_rank[p] for p in my_team if p!='陈小洪') / max(len(my_team)-1, 1)
    opp_avg_rank = sum(bt_rank[p] for p in opp_team) / len(opp_team)
    diff = abs(sa-sb)
    if diff <= 5 or partner_avg_rank > bt_rank['陈小洪'] + 5:
        cases2.append((partner_avg_rank - opp_avg_rank, date, my_team, opp_team, sa, sb, diff))
cases2.sort()
for i, c in enumerate(cases2[:5]):
    _, date, mt, ot, sa, sb, diff = c
    prt = ', '.join(f'{p}(BT#{bt_rank[p]})' for p in mt)
    oprt = ', '.join(f'{p}(BT#{bt_rank[p]})' for p in ot)
    print(f'  {i+1}. [{date}] 我方 {prt}')
    print(f'        vs  {oprt}')
    print(f'        比分: {sa}:{sb}  (输{diff}分{" 💔惜败" if diff<=3 else ""})')
    print()
