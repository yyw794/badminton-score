#!/usr/bin/env python3
"""
全量重训(A) vs 增量更新(B) 对比验证
前12周 = 历史；第13周(0831) = 新一周
"""
import json, math, glob, os
from collections import defaultdict

ROOT = os.path.normpath(os.path.dirname(__file__) + '/..')
json_files = sorted([f for f in glob.glob(f'{ROOT}/scores/*/match_data.json') if '/history/' not in f and os.path.isfile(f)])

def load_sets(fps):
    sets = []; players = set()
    for fp in fps:
        data = json.load(open(fp))
        for m in data.get('matches', []):
            a, b = m['team_a'], m['team_b']
            for p in a+b: players.add(p)
            for sk in (0,1):
                s = [m['score_a'], m['score_b']][sk]
                try: sa, sb = map(int, s.split(':'))
                except: continue
                if sa == sb: continue
                sets.append((a, b, sa>sb, sa, sb))
    return sorted(players), sets

# 拆成 历史12周（除0831外所有）+ 新1周（0831）
new_fp = [f for f in json_files if '20260831' in f]
hist_fps = [f for f in json_files if '20260831' not in f]
print(f'历史 match_data: {len(hist_fps)} 个, 新周 match_data: {len(new_fp)} 个')
hist_players, hist_sets = load_sets(hist_fps)
all_players,  new_sets  = load_sets([*hist_fps, *new_fp])
only_new_players, _ = load_sets(new_fp)
print(f'历史选手: {len(hist_players)}, 全局选手: {len(all_players)}, 新周出场选手: {len(only_new_players)}')
print(f'历史局数: {len(hist_sets)}, 新周局数: {len(new_sets)-len(hist_sets)}')

N = len(all_players)

def bt_train(players, init_sets, warm_theta=None, extra_sets=None, extra_iters=0, max_iter=20000, tol=1e-8):
    """warm_theta: dict 初值（可以只含历史选手，其余默认1.0）
       init_sets: 用于MLE主训练的对局（可以是历史+新，也可以是只有历史然后extra_sets增量）
       extra_sets: 如果非空，则在init_sets收敛后，再用extra_sets跑extra_iters轮增量更新（不动init_sets）
    """
    theta = {}
    for p in players:
        if warm_theta and p in warm_theta:
            theta[p] = warm_theta[p]
        else:
            theta[p] = 1.0  # 新选手默认1.0（中等级别）
    n = len(players)

    def one_iter(train_sets, t):
        wins_d = defaultdict(float); denom_d = defaultdict(float)
        for ta, tb, aw, _, _ in train_sets:
            Ta = math.prod(t[q] for q in ta)
            Tb = math.prod(t[q] for q in tb)
            D = Ta + Tb + 1e-20
            if aw:
                for q in ta: wins_d[q] += 1.0
            else:
                for q in tb: wins_d[q] += 1.0
            for q in ta: denom_d[q] += Ta/D
            for q in tb: denom_d[q] += Tb/D
        new_t = {}
        for q in players:
            new_t[q] = t[q] * (wins_d[q]/denom_d[q]) if denom_d[q] > 1e-15 else t[q]
        gm = math.exp(sum(math.log(max(v,1e-20)) for v in new_t.values())/n)
        for q in new_t: new_t[q] = max(new_t[q]/gm, 1e-20)
        # 返回变化量
        diff = max(abs(math.log(new_t[q]/t[q])) for q in t if t[q]>0)
        return new_t, diff

    # 阶段1：用init_sets收敛
    for it in range(max_iter):
        theta, diff = one_iter(init_sets, theta)
        if diff < tol: break

    # 阶段2（可选增量）：用extra_sets再跑extra_iters轮，不再归一化防止漂移？其实归一化没问题
    if extra_sets:
        for ei in range(max(extra_iters, 800)):
            theta, diff = one_iter(extra_sets, theta)
            if diff < tol and ei >= 200:
                break
    return {p: 400*math.log10(max(theta[p],1e-20)) + 1000 for p in players}

# ============ 方式 A：全量重训（从1.0冷启动，历史+新周 一起训练）============
print('\n========== 方式A：全量重训 冷启动 ==========')
rating_A = bt_train(all_players, new_sets)  # new_sets = 历史+新周全部533局
rank_A = {p:i+1 for i,p in enumerate(sorted(all_players, key=lambda x:-rating_A[x]))}

# ============ 方式 B1：增量更新 — 先跑历史12周得到θ_hist，然后用θ_hist做初值，只给新周48局跑N次迭代 ============
# 注意：训练历史时，可能有些选手（只在新周出场的）不在hist_players里。怎么办？—— 实际每周不会出现完全没打过的新人（都是熟人），这里就算有也默认θ=1.0。
print('\n========== 方式B1：增量更新（热启动+只训新周） ==========')
# 先跑历史12周得到warm start。注意历史选手可能比all少，所以训练历史时用hist_players + 只在新周出现的人（θ默认1.0）
extra_new = [p for p in all_players if p not in set(hist_players)]
players_for_hist = sorted(set(hist_players) | set(only_new_players))
rating_hist = bt_train(players_for_hist, hist_sets)
theta_hist_warm = {p: 10**((rating_hist[p] - 1000)/400) for p in rating_hist}  # 把rating还原回θ值做warm start
# 注意！增量更新时，BT迭代**不能只训新周的局**——因为历史对局的约束没有了，这会让θ在新周的梯度上狂奔，忘记历史！
# 所以"真正的BT增量更新"其实不存在——除非你用在线版本的BT（有正则/滑动窗口），否则单纯给新周跑几十轮会严重漂移。
# 先试一下（让用户看效果）
rating_B1_bad = bt_train(all_players, new_sets[-len(new_sets)+len(hist_sets):], warm_theta=theta_hist_warm, max_iter=500, tol=1e-20)
rank_B1_bad = {p:i+1 for i,p in enumerate(sorted(all_players, key=lambda x:-rating_B1_bad[x]))}

# ============ 方式 B2：真正的增量 = 用历史θ做warm start，然后再用【历史+新周全量】跑完整收敛 ============
# 这才是工程上正确的"增量"——初值用上周θ，这样可以省迭代次数（热启动收敛更快），但最终结果其实和全量冷启动收敛到同一个点（MLE是凸的）。
print('\n========== 方式B2：工程上正确的增量（热启动+全量重训收敛快，结果一样） ==========')
rating_B2 = bt_train(all_players, new_sets, warm_theta=theta_hist_warm)
rank_B2 = {p:i+1 for i,p in enumerate(sorted(all_players, key=lambda x:-rating_B2[x]))}

# ============ 对比 ============
def compare(name, rank_a, rank_b, label_a='A全量', label_b=None, rating_other=None):
    if label_b is None: label_b = name
    # 只比出场>=30的（纳入排名的有效选手）
    # 先算总出场
    w = defaultdict(int); l = defaultdict(int)
    for ta, tb, aw, sa, sb in new_sets:
        for p in ta:
            if aw: w[p]+=1
            else: l[p]+=1
        for p in tb:
            if not aw: w[p]+=1
            else: l[p]+=1
    valid = [p for p in all_players if w[p]+l[p] >= 30]
    diffs = []
    same_top10 = sum(1 for p in valid[:min(10,len(valid))] if rank_a[p] == rank_b[p])
    max_up = ('', 0); max_down = ('', 0)
    for p in valid:
        d = rank_a[p] - rank_b[p]
        diffs.append(abs(d))
        if d > max_up[1]: max_up = (p, d)
        if d < max_down[1]: max_down = (p, d)
    spearman = 1 - (6*sum(d*d for d in [rank_a[p]-rank_b[p] for p in valid]) / (len(valid)*(len(valid)**2-1))) if len(valid) > 1 else 0
    print(f'\n  {label_a} vs {label_b} （有效选手{len(valid)}人）')
    print(f'    名次平均绝对差: {sum(diffs)/len(diffs):.2f} 名')
    print(f'    名次最大差:   {max_up[0]} +{max_up[1]}名（比A高） / {max_down[0]} {max_down[1]}名（比A低）')
    print(f'    Spearman 秩相关: {spearman:.4f}  {"🟢几乎一致" if spearman > 0.995 else "🟡有偏差" if spearman>0.95 else "🔴差异大"}')
    # 表格对比前24名
    print(f'\n    前24名详细对比：')
    print(f'    {"排名A":>6}{"排名"+label_b[-2:]:>8}{"Δ名":>6}  {"选手":<8}{"ratingA":>9}{"rating"+label_b[-2:]:>9}{"Δrating":>10}')
    print('    ' + '-'*90)
    for p in sorted(valid, key=lambda x: rank_a[x])[:24]:
        rA, rB = rank_a[p], rank_b[p]
        rtA, rtB = rating_A.get(p,0), (rating_B1_bad if 'B1' in name else rating_B2).get(p,0)
        if rating_other is not None: rtB = rating_other.get(p, 0)
        print(f'    {rA:>6}{rB:>8}{rA-rB:>+6}  {p:<8}{rtA:>9.0f}{rtB:>9.0f}{rtA-rtB:>+10.0f}')

compare('B1_bad(只训新周48局，无历史约束)', rank_A, rank_B1_bad)
print('\n' + '='*100)
compare('B2(θ热启动+全量收敛，理论等价)', rank_A, rank_B2)
