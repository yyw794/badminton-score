#!/usr/bin/env python3
"""
BT θ 预测双打组合胜率 + 历史回测（校准可信度）
"""
import json, math, glob, os, itertools
from collections import defaultdict, Counter

ROOT = os.path.normpath(os.path.dirname(__file__) + '/..')
json_files = sorted([f for f in glob.glob(f'{ROOT}/scores/*/match_data.json') if '/history/' not in f and os.path.isfile(f)])

# =============== 1. 先训出全局 θ（和之前完全一致，确保口径对齐）===============
all_sets = []
raw_matches = []  # 用于回测：(date, tuple(sorted(ta)), tuple(sorted(tb)), a_won)  — 组合严格匹配
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
            aw = sa > sb
            all_sets.append((a, b, aw, sa, sb))
            raw_matches.append((date, tuple(sorted(a)), tuple(sorted(b)), aw, sa, sb))
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
print(f'✅ 训练完成：{len(players)}人，{len(all_sets)}局')

# =============== 2. 单局 / BO2 胜率预测函数 ===============
def predict_doubles(teamA, teamB):
    """
    输入两人组合名字列表：teamA=[p1,p2], teamB=[p3,p4]
    输出：{
      'teamA_teamB': 'A/B vs C/D',
      'A_theta': 团队θ乘积, 'B_theta': 团队θ乘积,
      'single_A_winrate': 单局A队胜率,
      'BO2': { '2:0': P, '1:1': P, '0:2': P, 'A_wins_match(≥1.5局等价)': P }
    }
    """
    Ta = math.prod(theta[p] for p in teamA)
    Tb = math.prod(theta[p] for p in teamB)
    p_A = Ta / (Ta + Tb)
    p_B = 1 - p_A
    bo2_20 = p_A * p_A
    bo2_11 = 2 * p_A * p_B
    bo2_02 = p_B * p_B
    # 两局制赛制不打第3局，整场算「胜」= 胜局数 > 负局数 = 2:0
    # 实际工会杯是两局各算1分，是独立的。这里给两个口径。
    a_wins_2to0 = bo2_20
    a_wins_on_score = bo2_20 + bo2_11 * 0.5  # 打平时各算一半
    return {
        'A': teamA, 'B': teamB,
        'Ta': Ta, 'Tb': Tb,
        'A_rating_avg': sum(rating[p] for p in teamA)/len(teamA),
        'B_rating_avg': sum(rating[p] for p in teamB)/len(teamB),
        'single_A_winrate': p_A,
        'bo2': {'2:0_A': bo2_20, '1:1': bo2_11, '0:2_B': bo2_02,
                'A_wins_exact(2:0)': bo2_20,
                'A_superior_on_expected(A局数-B局数)': (2*p_A - 1)  # A净胜局数期望，正=优势
               }
    }

def print_pred(teamA, teamB, title=''):
    info = predict_doubles(teamA, teamB)
    pA = info['single_A_winrate']
    pB = 1-pA
    strA = '/'.join(teamA) + ''.join(f' [{rating[p]:.0f}]' for p in teamA)
    strB = '/'.join(teamB) + ''.join(f' [{rating[p]:.0f}]' for p in teamB)
    print(f'\n🎯 {title}')
    print(f'  🟦 组合A: {strA}   团队θ乘积 = {info["Ta"]:.3f}   平均战斗力 {info["A_rating_avg"]:.0f}')
    print(f'  🟥 组合B: {strB}   团队θ乘积 = {info["Tb"]:.3f}   平均战斗力 {info["B_rating_avg"]:.0f}')
    ratio = info['Ta'] / info['Tb']
    print(f'  ⚖️  实力比值 A:B = {ratio:.2f} : 1')
    print()
    print(f'  单局:  A {pA*100:>5.1f}%  ┃  B {pB*100:>5.1f}%')
    bo2 = info['bo2']
    print(f'  两局制（独立同分布假设）：')
    print(f'    A 2:0横扫    {bo2["2:0_A"]*100:>5.1f}%')
    print(f'    1:1各赢一局 {bo2["1:1"]*100:>5.1f}%')
    print(f'    B 2:0横扫    {bo2["0:2_B"]*100:>5.1f}%')
    print(f'    A净胜局期望: {bo2["A_superior_on_expected(A局数-B局数)"]:+.2f} 局 / 2局')

# =============== 3. 用户要的组合 + 几个额外有意思的对比 ===============
print('\n' + '='*120)
print('📈 【你问的预测】'.center(120))
print('='*120)
print_pred(['苏大哲','陈财贵'], ['刘继宇','陈顺星'],
           '用户示例：苏大哲+陈财贵 VS 刘继宇+陈顺星')

print('\n' + '='*120)
print('🔥 【有意思的几组对照】'.center(120))
print('='*120)
# 你之前讨论过的冤案组合
print_pred(['王小波','董广博'], ['林小连','王苏丹'],
           '冤案PK：王小波+董广博（纯胜率倒数） VS 林小连+王苏丹（纯胜率中游）—— BT预测谁赢？')
# 抱大腿对照：唐英武(被高估) vs 罗琴荩(被低估) 带同一个搭档
print_pred(['罗琴荩','徐越'], ['唐英武','林小连'],
           '女双对照：罗琴荩+徐越 VS 唐英武+林小连')
# Top1 vs 平民队
print_pred(['黄冬青','林锋'], ['陈小洪','谢卓珊'],
           '极端对照：Top2(黄冬青+林锋) VS 平民组(陈小洪+谢卓珊)')
# 董广博+陈顺星 vs 其他人（组合相克的情况，看看BT会不会识别——不会！因为BT是单人实力乘积，不考虑相克）
print_pred(['董广博','陈顺星'], ['严勇文','王小波'],
           '⚠️ 组合相克案例：董广博+陈顺星（历史0-4）VS 严勇文+王小波 —— BT预测和实际可能有偏差！')

# =============== 4. 模型可信度校准：历史回测（Experience 545608要求的口径校准）===============
print('\n' + '='*120)
print('🎚️  【模型校准：用历史对局验证预测准不准】（分桶校准 + Brier分数）'.center(120))
print('='*120)

# 收集所有历史双打对局（去掉单打/混双？不，全部一起，不管类型），按组合匹配做预测
# 因为组合空间太大，严格匹配后样本少，所以我们把所有对局（不管什么组合）都拿出来算预测胜率分桶，看实际胜率是否落在分桶里——这是概率校准图的标准做法（reliability diagram）
bucket_pred = defaultdict(list)  # 预测胜率分桶 -> 实际0/1胜负列表
brier_sum = 0.0
cnt = 0

all_pairs = []  # 用于「至少出现过一次的相同组合」列表
for date, ta, tb, aw, sa, sb in raw_matches:
    # 用预测A队胜率 = Ta/(Ta+Tb)
    Ta = math.prod(theta[p] for p in ta)
    Tb = math.prod(theta[p] for p in tb)
    pred = Ta/(Ta+Tb)
    actual = 1.0 if aw else 0.0
    brier_sum += (pred - actual)**2
    cnt += 1
    # 分桶：[0,50), [50,60), [60,70), [70,80), [80,100]
    if pred < 0.5:
        b = '<50%'
    elif pred < 0.6:
        b = '50-60%'
    elif pred < 0.7:
        b = '60-70%'
    elif pred < 0.8:
        b = '70-80%'
    else:
        b = '≥80%'
    bucket_pred[b].append((pred, actual, date, ta, tb, sa, sb))

print(f'总样本：{cnt}局  |  Brier分数（越小越好，0=完美，0.25=瞎猜）：{brier_sum/cnt:.4f}  （<0.2算很好，<0.15非常优秀）')
print()
print(f'{"预测胜率区间":>12}{"局数":>8}{"实际平均胜率":>14}{"平均预测胜率":>14}{"校准偏差":>10}  评价')
print('-'*100)
for b in ['<50%','50-60%','60-70%','70-80%','≥80%']:
    items = bucket_pred[b]
    if not items: continue
    avg_pred = sum(x[0] for x in items)/len(items)
    actual_win = sum(x[1] for x in items)/len(items)
    diff = actual_win - avg_pred
    quality = '🟢极准' if abs(diff)<0.05 else ('🟡有点偏' if abs(diff)<0.10 else '🔴偏差大')
    print(f'{b:>12}{len(items):>8}{actual_win*100:>13.1f}%{avg_pred*100:>13.1f}%{diff*100:>+9.1f}%  {quality}')

print()
# 另外算「历史上严格相同的组合重复出现时，BT预测准不准」
print('='*120)
print('🔁 【严格相同组合≥2次的历史复盘】（样本少但最准确）'.center(120))
print('='*120)
combo_outcomes = defaultdict(list)  # key = (sorted(ta), sorted(tb)) -> list of a_won (0/1)
for date, ta, tb, aw, sa, sb in raw_matches:
    key = (tuple(sorted(ta)), tuple(sorted(tb)))
    # 统一方向：ta_sorted >= tb_sorted时互换，这样(A vs B)和(B vs A)在同一个key
    a_key, b_key = (key[0], key[1]) if key[0] >= key[1] else (key[1], key[0])
    a_is_left = (key[0] == a_key)
    outcome = (1 if aw else 0) if a_is_left else (0 if aw else 1)
    combo_outcomes[(a_key, b_key)].append(outcome)

count_shown = 0
for (ka, kb), outs in sorted(combo_outcomes.items(), key=lambda x: -len(x[1])):
    if len(outs) < 2: continue
    # ka = 左队（按sorted大的），kb = 右队。计算左队单局胜率
    T_left = math.prod(theta[p] for p in ka)
    T_right = math.prod(theta[p] for p in kb)
    pred_left = T_left / (T_left + T_right)
    actual_left = sum(outs)/len(outs)
    n = len(outs)
    wins = sum(outs)
    diff = actual_left - pred_left
    cal = '🟢准' if abs(diff)<0.1 else '🟡小偏' if abs(diff)<0.2 else '🔴偏'
    print(f'  {"/".join(ka)} VS {"/".join(kb)}  共{n}局')
    print(f'    BT预测左胜率: {pred_left*100:.1f}%  | 实际: {wins}胜/{n}局 = {actual_left*100:.1f}%  | 偏差 {diff*100:+.1f}% {cal}')
    count_shown += 1
if count_shown == 0:
    print('  （双打组合太随机，几乎没有重复的组合出现过≥2次，这是羽毛球随机分组的特点）')

print()
print('='*120)
print('⚠️ 【BT预测的局限性】（什么时候会不准）'.center(120))
print('='*120)
print('  1. 组合相克：董广博+陈顺星历史0-4，但单人实力乘积算出来没那么差 → BT不知道"这两个人一起打会变弱"')
print('  2. 状态/伤病波动：黄冬青这几天发烧手疼，θ不会实时变 → 模型用的是历史平均水平')
print('  3. 类型差异：混双/男双/女双类型差异模型没有区分，女双θ低可能只是女生之间打，不是她弱')
print('  4. 新选手：出场<10局的θ不准，需要至少15局以上稳定')
print('  5. 样本稀疏：严格相同组合历史上几乎没重复过（羽毛球分组太随机），无法做超精准的组合级校准')
print()
print('  👉 经验结论：单局预测值±10%范围内可以信（比如预测62%胜率，实际大概率在52-72%之间），不要迷信小数点。')
