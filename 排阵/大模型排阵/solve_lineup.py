#!/usr/bin/env python3
"""
排阵求解器（2026-09-21）—— 3 场地 15 人版
场地约束：3 个场地 × 7 轮 = 21 场；总能量 = 84（单打×2 + 双打×1）。
结构（每人确定，来自 instances/2026-09-21.json）：
  男单 2（范智强 vs 罗琴荩，R1/R4）；女单 2（徐越 vs 李祺祺，R2/R5）；
  女双vs混双 3（R3/R4/R6，李佳琳固定女双侧，3 女全上另配 1 男）；
  混双 1（R1，徐越+李佳琳）；开放男双 1（R7）；锚点男双 sc(7)/xl(5)。
锚点：苏大哲/陈财贵（sc，全 7 轮，"最强针对打"），陈顺星/严勇文（xl，R1/R4 休）。
硬约束：
  1. 锚点对锁死：凡打男双必须同队（不拆）。
  2. 无外援PK外援：每场至多 1 队含外援；男双组队优先 内部+内部 / 外援+外援。
  3. 每人 caps（8）+ mins（非锚点≥3）；女生能量由轮次模板锁死。
  4. 能量极差 ≤ spread_max（2026-09-21 结构为 4；女生/单打结构性偏低端）。
方法：回溯搜索 + 多随机重启，取 BT 强度 + 能量均衡 最优的可行解。
输出：与本目录 lineup JSON 同结构，可直接交给 export_lineup.py。
"""
import itertools
import json
import os
import random
import sys
from collections import defaultdict
from pathlib import Path

DEBUG_TRACE = bool(os.environ.get("SOLVE_DEBUG"))
_repair_theta = None   # repair_balance 内 balanced_split 用

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
from export_lineup import load_theta, prod_theta, win_prob  # noqa: E402

# ===== 周实例配置（名单/角色/结构/偏好 —— 每周变，算法不变）=====
from weekly import load as _load_week
WEEK = _load_week()

SC = tuple(WEEK.anchor_pairs[0]) if len(WEEK.anchor_pairs) >= 1 else None   # 锚点1（最强）
SC_OPP_POOL = set(WEEK.sc_opp_pool) if WEEK.sc_opp_pool else None   # 苏陈对手硬候选池
XL_ANCHOR = WEEK.xl_anchor          # 第二男双固定成员（严勇文）
XL_PARTNER = tuple(WEEK.xl_partner or [])   # 第二男双搭档候选池
MS_PAIR = tuple(WEEK.ms_pair)              # 男单固定对战（范智强/罗琴荩）
WS_PAIR = tuple(WEEK.ws_pair)              # 女单固定对战（徐越/李祺祺）
WD_SIDES = WEEK.wd_sides                   # 女双vs混双 女方分配 {"女双":[..],"混双":[..]}
SEEDS = tuple(WEEK.seeds)                  # 单打种子（本周为空）
MS_OPP_FOREIGN = WEEK.ms_opp_foreign
MS_OPP_INTERNAL = set(WEEK.ms_opp_internal)
MS_OPP_POOL = WEEK.ms_opp_pool
XD_PREFER = set(WEEK.xd_prefer)
MS_OPP_ORDER = WEEK.ms_opp_order
XD_ORDER = WEEK.xd_order
MS_OPP_CAP = WEEK.ms_opp_cap
# 非锚点池 = 非锚点内部男 + 外援；严勇文 专任第二男双(不占自由池，避免和他抢槽)
NON_ANCHOR = [p for p in WEEK.non_anchor if p != XL_ANCHOR]
FOREIGN = WEEK.foreign
W_XD0 = WEEK.xd_women[0]                   # 混双女1（徐越）
W_XD1 = WEEK.xd_women[1]                   # 混双女2（李佳琳）
COURTS = WEEK.courts
NR = WEEK.rounds_count
CAP = {p: WEEK.cap for p in NON_ANCHOR}
MIN_CAP = WEEK.min_cap
ROUNDS = WEEK.rounds
OM_ROUNDS = {r for r, s in ROUNDS.items() if s["om"]}
SC_ROUNDS = set(WEEK.sc_rounds)
XL_ROUNDS = set(WEEK.xl_rounds)
DUEL_ROUNDS = tuple(WEEK.duel_rounds)
# 指定合练对（男双固定搭档）：实例层 pairs 字段
PAIRS = WEEK.pair_list
PAIR_KEYS = {pr for pr, _ in PAIRS}
PAIR_MIN = {pr: mn for pr, mn in PAIRS}
ANCHOR_SETS = {frozenset(p) for p in WEEK.anchor_pairs}
NONANCHOR_PAIR_KEYS = PAIR_KEYS - ANCHOR_SETS
RESHUFFLE_ROUNDS = set(WEEK.reshuffle_rounds)
RESHUFFLE_TEAMS = [tuple(t) for t in WEEK.reshuffle_teams]
MIN_CAPS = WEEK.min_caps
MAX_PAIRS = WEEK.max_pair_list
MAX_PAIR_KEYS = {pr for pr, _ in MAX_PAIRS}
MAX_PAIR_CAP = {pr: mx for pr, mx in MAX_PAIRS}
_XD_MIN0 = (WEEK.goals.get("xd_min") or [{}])[0]
XD_KEY_PLAYER = _XD_MIN0.get("player")
XD_KEY_MIN = int(_XD_MIN0.get("min", 0))

# ---- 算法参数（通用、稳定）----
# 2026-09-21：14 人 84 能量，人均 6.0；目标全员落 [5,7]（极差 2，与需求文档"能量均衡最高优先"一致）。
# 结构定死者：苏/财 sc=7、严勇文 xl=5、女生 徐/李=7 佳琳=5；非锚点 8 男 46 能量落 [5,7]。
WORK_MIN, WORK_MAX = 6, 7   # WORK_MAX=7 硬上限；WORK_MIN=6 软下限（排序/方差往均值拉）
WORK_LOW = 5                # 硬下限（能量）：非锚点 ≥5
OM_MAX_COMBOS = 24
WORK_BAL_W = 2.0             # 能量均衡权重（用户最关心，压过强度项1.0 成绝对主导）
WORK_FLOOR_W = 8.0           # 低于下限 WORK_MIN 的平方惩罚权重
SC_STRONG_W = 0.05           # 最强锚点(苏陈)对手强度奖励（次级，强手池硬过滤为主）
SC_REPEAT_W = 1.0            # 苏陈对手组合重复惩罚（别老同一对，软）
SC_OPP_MAX_REPEAT = 2        # 苏陈对手同一组合上限（硬：别 7 轮同一对）
MIXED_W = 0.2                # 男双混合队(外援+内部)惩罚
SEED_DISTINCT_W = 0.2        # 仅 ms_s 模型用（本周无种子，无效）
COVERAGE_W = 0.5             # 互搞覆盖奖励（无合练对，无效）

# 外援规则：每场至多 1 队含外援（外援+外援同队允许）
ROLE_FOREIGN_CAP = {"ms_s": 1, "xd": 1, "wd_xd": 1, "sc": 2, "xl": 2, "xlp": 1, "om": 2}


def group_foreign_ok(name, grp):
    return sum(1 for p in grp if p in FOREIGN) <= ROLE_FOREIGN_CAP[name]


def balanced_split(four, theta):
    fs = [p for p in four if p in FOREIGN]
    if len(fs) == 2:   # 2 外援必须同队（无外援PK外援）
        return tuple(fs), tuple(p for p in four if p not in FOREIGN)
    s = sorted(four, key=lambda p: -theta[p])
    return (s[0], s[3]), (s[1], s[2])


def xd_assign(men, w0, w1, theta):
    """混双：两名男生各配一名女生，强度均衡。"""
    a, b = sorted(men, key=lambda p: -theta[p])
    opt1 = (abs(theta[a] * theta[w0] - theta[b] * theta[w1]),
            [a, w0], [b, w1])
    opt2 = (abs(theta[b] * theta[w0] - theta[a] * theta[w1]),
            [b, w0], [a, w1])
    return (opt1 if opt1[0] <= opt2[0] else opt2)[1:]


def build(sc_rounds, xl_rounds, assign, theta, duel_rounds=frozenset()):
    rounds_out = []
    for r in range(1, NR + 1):
        spec = ROUNDS[r]
        A = assign[r]
        ordered = []
        if spec.get("ms"):
            ordered.append(("男单", [MS_PAIR[0]], [MS_PAIR[1]]))
        if spec.get("ws"):
            ordered.append(("女单", [WS_PAIR[0]], [WS_PAIR[1]]))
        if spec.get("wd_xd"):
            man = A["wd_xd"][0]
            sides = spec.get("wd_sides") or WD_SIDES
            ordered.append(("女双vs混双",
                            list(sides.get("女双", [])),
                            [man] + list(sides.get("混双", []))))
        if spec.get("xd"):
            xw = spec.get("xd_women") or (W_XD0, W_XD1)
            xda, xdb = xd_assign(A["xd"], xw[0], xw[1], theta)
            ordered.append(("混双", xda, xdb))
        if r in sc_rounds:
            ordered.append(("男双", list(SC), list(A["sc_opp"])))
        if r in xl_rounds:
            ordered.append(("男双", [XL_ANCHOR] + list(A["xlp"]), list(A["xl_opp"])))
        if spec.get("om"):
            t1, t2 = balanced_split(A["om"], theta)
            ordered.append(("男双", list(t1), list(t2)))
        assert len(ordered) == len(COURTS), f"R{r} 场次={len(ordered)}"
        matches = [{"court": c, "type": t, "a": a, "b": b}
                   for c, (t, a, b) in zip(COURTS, ordered)]
        rounds_out.append({"round": r, "matches": matches})
    return rounds_out


def _plays_mens_double(assign, p):
    return any(p in assign[r].get(k, []) for r in range(1, NR + 1)
               for k in ("om", "sc_opp", "xl_opp"))


def _pair_counts(assign):
    pc, mc = defaultdict(int), defaultdict(int)
    for r in range(1, NR + 1):
        A = assign[r]
        for key in ("sc_opp", "xl_opp"):
            g = A.get(key, [])
            if len(g) == 2:
                k = frozenset(g)
                if k in PAIR_KEYS:
                    pc[k] += 1
                if k in MAX_PAIR_KEYS:
                    mc[k] += 1
        xlp = A.get("xlp", [])
        if len(xlp) == 1:
            k = frozenset([XL_ANCHOR, xlp[0]])
            if k in PAIR_KEYS:
                pc[k] += 1
            if k in MAX_PAIR_KEYS:
                mc[k] += 1
        om = A.get("om", [])
        if len(om) == 4:
            for team in balanced_split(om, _repair_theta):
                k = frozenset(team)
                if k in MAX_PAIR_KEYS:
                    mc[k] += 1
    return pc, mc


def repair_balance(assign, theta, sc_rounds, xl_rounds, duel_rounds, max_iters=600):
    """通用局数极差压缩（局部搜索）：把局数最多者的某场男双，换成同轮坐场、局数较少者。
    不改硬约束；仅改 om/sc_opp/xl_opp。返回 (assign, 是否改进)。"""
    global _repair_theta
    _repair_theta = theta

    def round_playing(r):
        A = assign[r]
        s = set(A.get("xd", [])) | set(A.get("wd_xd", [])) | set(A.get("om", [])) \
            | set(A.get("xlp", [])) \
            | set(A.get("sc_opp", [])) | set(A.get("xl_opp", []))
        if ROUNDS[r].get("ms"):
            s |= set(MS_PAIR)
        return s

    def match_count(p):
        c = 0
        for r in range(1, NR + 1):
            A = assign[r]
            if any(p in A.get(k, []) for k in ("xd", "wd_xd", "om", "xlp", "sc_opp", "xl_opp")):
                c += 1
            if ROUNDS[r].get("ms") and p in MS_PAIR:
                c += 1
        return c

    def spread_of():
        w = player_workload(build(sc_rounds, xl_rounds, assign, theta, duel_rounds))
        vals = list(w.values())
        avg = sum(vals) / len(vals)
        var = sum((v - avg) ** 2 for v in vals)
        return max(vals) - min(vals), max(vals), var, dict(w)

    improved = False
    for _ in range(max_iters):
        cur_spread, cur_max, cur_var, w = spread_of()
        cands_H = [p for p in w if p in NON_ANCHOR
                   and p not in (W_XD0, W_XD1)
                   and _plays_mens_double(assign, p)
                   and match_count(p) - 1 >= MIN_CAPS.get(p, 0)]
        if not cands_H:
            break
        cands_H.sort(key=lambda p: (-w[p], p))
        moved = False
        for H in cands_H:
            if moved:
                break
            for r in range(1, NR + 1):
                if moved:
                    break
                A = assign[r]
                swap_roles = (("om", "om"), ("sc", "sc_opp"), ("xl", "xl_opp"))
                if SC_OPP_POOL is not None:
                    # 苏陈对手已限定强手池：repair 不碰 sc（保住"对手尽量强"），只换 om/xl
                    swap_roles = (("om", "om"), ("xl", "xl_opp"))
                for role, key in swap_roles:
                    if moved:
                        break
                    g = A.get(key, [])
                    if H not in g:
                        continue
                    for L in NON_ANCHOR:
                        if L == H or L in round_playing(r):
                            continue
                        if match_count(L) >= CAP[L]:
                            continue
                        # 苏陈对手：swap 也须留在强手池（修复把强对手换成弱手的问题）
                        if role == "sc" and SC_OPP_POOL is not None and L not in SC_OPP_POOL:
                            continue
                        new_g = [L if p == H else p for p in g]
                        if sum(1 for p in new_g if p in FOREIGN) > ROLE_FOREIGN_CAP[role]:
                            continue
                        A[key] = new_g
                        pc, mc = _pair_counts(assign)
                        ok = (all(pc[k] >= PAIR_MIN[k] for k in PAIR_KEYS)
                              and all(mc[k] <= MAX_PAIR_CAP[k] for k in MAX_PAIR_KEYS))
                        if not ok:
                            A[key] = g
                            continue
                        new_spread, new_max, new_var, _ = spread_of()
                        if (new_spread < cur_spread
                                or (new_spread == cur_spread and new_var < cur_var)):
                            improved = True
                            moved = True
                            break
                        A[key] = g
        if not moved:
            break
    return assign, improved


def workload_of(match_type):
    return 2 if match_type in ("男单", "女单") else 1   # 1 单打=2 局，1 双打=1 局


def player_workload(rounds):
    work = defaultdict(int)
    for rd in rounds:
        for m in rd["matches"]:
            inc = workload_of(m["type"])
            for player in m["a"] + m["b"]:
                work[player] += inc
    return work


def lineup_score(rounds, theta):
    total = 0.0
    work = defaultdict(int)
    for rd in rounds:
        for m in rd["matches"]:
            if m["type"] in ("男单", "女单"):
                sa, sb = theta[m["a"][0]], theta[m["b"][0]]
            else:
                sa, sb = prod_theta(m["a"], theta), prod_theta(m["b"], theta)
            p = win_prob(sa, sb)
            total += abs(max(p, 1 - p) - 0.5)
            inc = workload_of(m["type"])
            for player in m["a"] + m["b"]:
                work[player] += inc
    mixed = sum(1 for rd in rounds for m in rd["matches"]
                if m["type"] == "男双"
                for side in (m["a"], m["b"])
                if sum(1 for p in side if p in FOREIGN) == 1)
    total += MIXED_W * mixed
    # 最强锚点(苏陈)对手：强度奖励（θ 和越大越好）+ 组合重复惩罚（软：尽量不重复）
    if SC is not None:
        scset = frozenset(SC)
        str_sum = 0.0
        seen_pairs = defaultdict(int)
        for rd in rounds:
            for m in rd["matches"]:
                if m["type"] != "男双":
                    continue
                if frozenset(m["a"]) == scset and len(m["b"]) == 2:
                    opp = m["b"]
                elif frozenset(m["b"]) == scset and len(m["a"]) == 2:
                    opp = m["a"]
                else:
                    continue
                str_sum += theta[opp[0]] + theta[opp[1]]
                seen_pairs[frozenset(opp)] += 1
        total -= SC_STRONG_W * str_sum
        total += SC_REPEAT_W * sum(v - 1 for v in seen_pairs.values())
    if work:
        avg = sum(work.values()) / len(work)
        total += WORK_BAL_W * sum((w - avg) ** 2 for w in work.values())
        total += WORK_FLOOR_W * sum(max(0, WORK_MIN - w) ** 2 for w in work.values())
    return total


ROLE_KEY = {"sc": "sc_opp", "xl": "xl_opp", "xlp": "xlp",
            "xd": "xd", "wd_xd": "wd_xd", "om": "om"}


def solve(sc_rounds, xl_rounds, theta, rng, node_cap=60000,
          duel_rounds=frozenset()):
    # 固定占位：男单轮 范/罗 该轮不进池子（固定对战）
    fixed_occ = {}
    for r in range(1, NR + 1):
        occ = set()
        if ROUNDS[r].get("ms"):
            occ |= set(MS_PAIR)
        fixed_occ[r] = occ

    roles, need = {}, {}
    for r in range(1, NR + 1):
        spec = ROUNDS[r]
        # 角色顺序 = 挑选优先级：第二男双搭档 > 最强锚点对手(强手优先) > 第二男双对手
        #           > 混双 > 女双vs混双男 > 开放男双
        rs = []
        if r in xl_rounds:
            rs.append(("xlp", 1, None))    # 严勇文 搭档（池内轮换）
        if r in sc_rounds:
            rs.append(("sc", 2, None))     # 苏陈对手（尽量强）
        if r in xl_rounds:
            rs.append(("xl", 2, None))
        if spec.get("xd"):
            rs.append(("xd", 2, None))
        if spec.get("wd_xd"):
            rs.append(("wd_xd", 1, None))
        if spec.get("om"):
            rs.append(("om", 4, None))
        roles[r] = rs
        need[r] = sum(sz for _, sz, _ in rs)

    # 男单固定对战先计场/能量（范/罗 +4 底仓）
    ms_count = defaultdict(int)
    for r in range(1, NR + 1):
        if ROUNDS[r].get("ms"):
            for p in MS_PAIR:
                ms_count[p] += 1
    used = {p: ms_count.get(p, 0) for p in NON_ANCHOR}
    work = {p: ms_count.get(p, 0) * 2 for p in NON_ANCHOR}
    lf_xd = [0]
    wd_cnt = defaultdict(int)   # 各男已当过女双vs混双的"混双男"次数（软：轮换，别老同一人）
    sc_pairs_cnt = defaultdict(int)   # 苏陈对手组合次数（硬上限 SC_OPP_MAX_REPEAT）
    pair_cnt = {pr: 0 for pr in PAIR_KEYS}
    max_pair_cnt = {pr: 0 for pr in MAX_PAIR_KEYS}
    assign = {}
    nodes = [0]

    order = NON_ANCHOR[:]
    rng.shuffle(order)

    def forward_ok(r_cur):
        if XD_KEY_MIN > 0:
            need_xd = XD_KEY_MIN - lf_xd[0]
            if need_xd > 0:
                avail = 0
                for r2 in range(r_cur + 1, NR + 1):
                    if (any(nm == "xd" for nm, _, _ in roles[r2])
                            and XD_KEY_PLAYER not in fixed_occ[r2]
                            and used[XD_KEY_PLAYER] < CAP[XD_KEY_PLAYER]):
                        avail += 1
                if avail < need_xd:
                    return False
        for r2 in range(r_cur + 1, NR + 1):
            pool2 = sum(1 for p in NON_ANCHOR
                        if p not in fixed_occ[r2] and used[p] < CAP[p])
            if pool2 < need[r2]:
                return False
        for p in NON_ANCHOR:
            deficit = MIN_CAPS[p] - used[p]
            if deficit > 0:
                avail = sum(1 for r2 in range(r_cur + 1, NR + 1)
                            if p not in fixed_occ[r2] and used[p] < CAP[p])
                if avail < deficit:
                    return False
        # 能量硬下限 WORK_LOW：按"每轮 +1"估（本周只有范/罗固定单打 +2，已在底仓计入）
        for p in NON_ANCHOR:
            if work[p] < WORK_LOW:
                avail = sum(1 for r2 in range(r_cur + 1, NR + 1)
                            if p not in fixed_occ[r2] and used[p] < CAP[p])
                if work[p] + 1 * avail < WORK_LOW:
                    return False
        return True

    def dfs(r, taken):
        if nodes[0] > node_cap:
            return False
        nodes[0] += 1
        if r == NR + 1:
            if lf_xd[0] != XD_KEY_MIN:
                return False
            if any(work[p] > WORK_MAX or work[p] < WORK_LOW for p in NON_ANCHOR):
                return False
            if not all(pair_cnt[pr] >= PAIR_MIN[pr] for pr in PAIR_KEYS):
                return False
            return all(used[p] >= MIN_CAPS[p] for p in NON_ANCHOR)
        pool = [p for p in order if p not in fixed_occ[r] and used[p] < CAP[p]]
        if len(pool) < need[r]:
            return False
        A = {}
        rlist = roles[r]

        def prune(idx, taken):
            rem = [p for p in pool if p not in taken]
            need_rem = sum(sz for _, sz, _ in rlist[idx:])
            return len(rem) >= need_rem

        def rec(idx, taken):
            if idx == len(rlist):
                if not forward_ok(r):
                    return False
                assign[r] = A
                return dfs(r + 1, set())
            name, size, seed = rlist[idx]
            if not prune(idx, taken):
                return False
            cands = [p for p in pool if p not in taken and p != seed]
            if name == "xlp":
                # 严勇文 搭档：限候选池（陈顺星/范智强/罗琴荩），能量欠账者优先
                cands = [p for p in cands if p in XL_PARTNER and work[p] + 1 <= WORK_MAX]
                cands = sorted(cands, key=lambda p: (work[p] >= WORK_MIN, work[p],
                                                     0 if p in XD_PREFER else 1,
                                                     XD_ORDER.get(p, 9)))
            elif name == "wd_xd":
                cands = [p for p in cands if work[p] + 1 <= WORK_MAX]
                cands = sorted(cands, key=lambda p: (wd_cnt[p],
                                                     work[p] >= WORK_MIN, work[p],
                                                     0 if p in XD_PREFER else 1,
                                                     XD_ORDER.get(p, 9)))
            elif name == "xd":
                cands = sorted(cands, key=lambda p: (work[p] >= WORK_MIN, work[p],
                                                     0 if p in XD_PREFER else 1,
                                                     XD_ORDER.get(p, 9)))
            elif name == "sc":
                # 苏陈对手：硬候选池(排除最弱)；池内洗牌探索不同强组合(多样性)，
                # 由 强度奖励+重复惩罚 在多重启里选出最优
                cands = [p for p in cands if work[p] + 1 <= WORK_MAX
                         and (SC_OPP_POOL is None or p in SC_OPP_POOL)]
                cands = sorted(cands, key=lambda p: -theta[p])
                rng.shuffle(cands)
            else:
                cands = [p for p in cands if work[p] + 1 <= WORK_MAX]
                cands = sorted(cands, key=lambda p: (work[p] >= WORK_MIN,
                                                     work[p], -theta[p]))
            if len(cands) < size:
                return False
            if len(cands) == size:
                g = tuple(cands)
                groups = [g] if group_foreign_ok(name, g) else []
            else:
                groups = [c for c in itertools.combinations(cands, size)
                          if group_foreign_ok(name, c)]

                def grp_key(g):
                    if name == "sc":
                        # 苏陈对手：组合 θ 和越大越好（强手优先），次看能量
                        return (-(theta[g[0]] + theta[g[1]]),
                                sum(work[p] for p in g))
                    if name in ("sc", "xl"):
                        k = frozenset(g)
                        pf = 0 if (k in PAIR_KEYS
                                   and pair_cnt[k] < PAIR_MIN[k]) else 1
                    else:
                        pf = 0
                    n_over = sum(1 for p in g if work[p] >= WORK_MIN)
                    return (pf, n_over, sum(work[p] for p in g),
                            1 if sum(1 for p in g if p in FOREIGN) == 1 else 0)

                groups.sort(key=grp_key)
                if name == "om":
                    groups = groups[:OM_MAX_COMBOS]
            for grp in groups:
                if name == "xd":
                    add = 1 if XD_KEY_PLAYER in grp else 0
                    if lf_xd[0] + add > XD_KEY_MIN:
                        continue
                pair_hit = None
                if name in ("sc", "xl"):
                    k = frozenset(grp)
                    if k in PAIR_KEYS:
                        pair_hit = k
                # 苏陈对手同一组合上限（硬）：避免 7 轮全是同一对
                sc_pair_key = None
                if name == "sc" and SC_OPP_MAX_REPEAT:
                    sc_pair_key = frozenset(grp)
                    if sc_pairs_cnt[sc_pair_key] >= SC_OPP_MAX_REPEAT:
                        continue
                if name in ("sc", "xl"):
                    team_list = [tuple(grp)]
                elif name == "xlp":
                    team_list = [(XL_ANCHOR, grp[0])]
                elif name == "om":
                    team_list = list(balanced_split(grp, theta))
                else:
                    team_list = []
                mp_hits, mp_violate = [], False
                for team in team_list:
                    k = frozenset(team)
                    if k in MAX_PAIR_KEYS:
                        if max_pair_cnt[k] >= MAX_PAIR_CAP[k]:
                            mp_violate = True
                            break
                        mp_hits.append(k)
                if mp_violate:
                    continue
                for p in grp:
                    used[p] += 1
                A[ROLE_KEY[name]] = grp
                if DEBUG_TRACE and name in ("om", "sc", "xl", "wd_xd"):
                    print(f"  R{r} {name}: {[(p, work[p]) for p in grp]}", flush=True)
                for p in grp:
                    work[p] += 1
                if name == "wd_xd":
                    wd_cnt[grp[0]] += 1
                if name == "xd":
                    lf_xd[0] += 1 if XD_KEY_PLAYER in grp else 0
                if pair_hit:
                    pair_cnt[pair_hit] += 1
                if sc_pair_key is not None:
                    sc_pairs_cnt[sc_pair_key] += 1
                for k in mp_hits:
                    max_pair_cnt[k] += 1
                if rec(idx + 1, taken | set(grp)):
                    return True
                if name == "wd_xd":
                    wd_cnt[grp[0]] -= 1
                if name == "xd":
                    lf_xd[0] -= 1 if XD_KEY_PLAYER in grp else 0
                if pair_hit:
                    pair_cnt[pair_hit] -= 1
                if sc_pair_key is not None:
                    sc_pairs_cnt[sc_pair_key] -= 1
                for k in mp_hits:
                    max_pair_cnt[k] -= 1
                for p in grp:
                    work[p] -= 1
                for p in grp:
                    used[p] -= 1
            return False

        return rec(0, taken)

    if dfs(1, set()):
        return assign
    return None


def _solve_task(seed):
    """多核并发的单个重启单元。"""
    rng = random.Random(seed)
    theta = load_theta()
    duel = set(DUEL_ROUNDS)
    assign = solve(SC_ROUNDS, XL_ROUNDS, theta, rng, node_cap=400000, duel_rounds=duel)
    if not assign:
        return None
    rounds = build(SC_ROUNDS, XL_ROUNDS, assign, theta, duel)
    score = lineup_score(rounds, theta)
    return (score, assign)


def main():
    theta = load_theta()

    import os
    import time
    import concurrent.futures
    import multiprocessing as mp

    try:
        mp.set_start_method("fork")
    except RuntimeError:
        pass

    scenario_name = " / ".join("/".join(p) for p in WEEK.anchor_pairs)
    n_cpu = os.cpu_count() or 4
    per_core = 4                 # 每核重启数（多核并发 → 总重启 = per_core × n_cpu）
    n_restarts = per_core * n_cpu
    seeds = [20260921 + i for i in range(n_restarts)]
    deadline = time.time() + 85

    best = None
    done = [0]
    with concurrent.futures.ProcessPoolExecutor(max_workers=n_cpu) as ex:
        futures = [ex.submit(_solve_task, s) for s in seeds]
        for fut in concurrent.futures.as_completed(futures):
            if time.time() > deadline:
                break
            try:
                res = fut.result(timeout=10)
            except Exception:
                continue
            if not res:
                continue
            score, assign = res
            done[0] += 1
            if best is None or score < best[0]:
                best = (score, scenario_name, tuple(DUEL_ROUNDS),
                        SC_ROUNDS, XL_ROUNDS, assign)
                print(f"  [{scenario_name}] 第{done[0]}个可行解 均衡分 {score:.3f}", flush=True)
    print(f"  （{n_cpu} 核并发 × {per_core} 重启；时间兜底 85s）", flush=True)

    if not best:
        print("无可行解")
        sys.exit(1)

    score, name, duel, sc_rounds, xl_rounds, assign = best
    assign, repaired = repair_balance(assign, theta, sc_rounds, xl_rounds, set(duel))
    rounds = build(sc_rounds, xl_rounds, assign, theta, set(duel))
    score = lineup_score(rounds, theta)
    if repaired:
        print(f"  局数均衡局部搜索：极差已压缩（均衡分 {score:.3f}）", flush=True)
    # 能量极差硬约束（结构不同，阈值来自实例 spread_max）
    w_all = player_workload(rounds)
    spread = max(w_all.values()) - min(w_all.values())
    if spread > WEEK.spread_max:
        print(f"✗ 能量极差 {spread} > {WEEK.spread_max}（硬约束未达标），不写出 lineup；请调整结构/预算后重跑")
        sys.exit(1)
    print(f"  能量极差 {spread}（硬约束 ≤{WEEK.spread_max}）min={min(w_all.values())} max={max(w_all.values())}",
          flush=True)

    ms_rounds = "/".join("R" + str(r) for r in sorted(
        r for r, s in ROUNDS.items() if s.get("ms")))
    ws_rounds = "/".join("R" + str(r) for r in sorted(
        r for r, s in ROUNDS.items() if s.get("ws")))
    wdxd_rounds = "/".join("R" + str(r) for r in sorted(
        r for r, s in ROUNDS.items() if s.get("wd_xd")))
    xd_rounds = "/".join("R" + str(r) for r in sorted(
        r for r, s in ROUNDS.items() if s.get("xd")))
    om_rounds = "/".join("R" + str(r) for r in sorted(OM_ROUNDS))
    anchor_desc = []
    for pair, played in zip(WEEK.anchor_pairs, (sc_rounds, xl_rounds)):
        rest = sorted(set(range(1, NR + 1)) - played)
        suffix = (f"({'/'.join('R' + str(r) for r in rest)}休)" if rest
                  else f"({len(played)}轮)")
        anchor_desc.append(f"{'/'.join(pair)} 男双锁死{suffix}")
    xl_rest = sorted(set(range(1, NR + 1)) - set(xl_rounds))
    xl_desc = (f"{XL_ANCHOR} 固定 + 搭档轮换({'/'.join(XL_PARTNER)}；"
               f"严勇文+陈顺星≤2)（{'/'.join('R' + str(r) for r in xl_rounds)}"
               f"{'，' + '/'.join('R' + str(r) + '休' for r in xl_rest) if xl_rest else ''}）")
    wd_desc = (f"女双({'/'.join(WD_SIDES.get('女双', []))}) vs "
               f"混双(男+{'/'.join(WD_SIDES.get('混双', []))})")
    lineup = {
        "title": WEEK.title,
        "date": WEEK.date,
        "courts": COURTS,
        "caps": WEEK.caps,
        "design_notes": {
            "目标": (f"3场地 {NR}轮 共{NR * len(COURTS)}场：锚点不拆 + 无外援PK外援 + "
                     "男双干净组合(外援+内部兜底) + 能量均衡(能量=单打×2+双打×1，"
                     f"极差≤{WEEK.spread_max}) + 强度均衡"),
            "锚点": "；".join(anchor_desc),
            "第二男双": xl_desc,
            "男单": f"{'/'.join(MS_PAIR)} 固定对战（{ms_rounds}，各2场）",
            "女单": f"{'/'.join(WS_PAIR)} 固定对战（{ws_rounds}，各2场）",
            "女双vs混双": f"{wdxd_rounds} {wd_desc}（李佳琳固定女双侧补位，3女全上另配1男）",
            "混双": (f"{xd_rounds} 各1场；" +
                     "；".join(f"R{r}:{'/'.join(ROUNDS[r].get('xd_women') or (W_XD0, W_XD1))}"
                               for r in sorted(r for r, s in ROUNDS.items() if s.get('xd')))),
            **({"开放男双": f"{om_rounds} 各1场(非锚点2v2)"} if om_rounds else {}),
            "能量均衡": ("能量=单打×2+双打×1；硬约束极差≤"
                         f"{WEEK.spread_max}(女生/固定单打结构性定死，"
                         "补位弱者李佳琳偏低端)，通用方差项往均值拉"),
            "外援规则": "无外援PK外援：每场至多1队含外援(外援+外援同队允许)；混双至多1外援男",
            "男双组合": ("最强锚点(苏陈)对手尽量挑强手(θ排序)；对手队组成优先 内部+内部/"
                         "外援+外援，外援+内部 仅兜底"),
            "强度": "BT θ 匹配；多解取最均衡",
        },
        "rounds": rounds,
    }

    out = BASE / f"{WEEK.date}-lineup.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(lineup, f, ensure_ascii=False, indent=2)
    print(f"✓ 已写出 {out}  （均衡分 {score:.3f}）")

    total = defaultdict(int)
    bad = 0
    mixed = 0
    for rd in rounds:
        for m in rd["matches"]:
            if (set(m["a"]) & FOREIGN) and (set(m["b"]) & FOREIGN):
                bad += 1
            if m["type"] == "男双":
                for side in (m["a"], m["b"]):
                    if sum(1 for p in side if p in FOREIGN) == 1:
                        mixed += 1
            for p in set(m["a"]) | set(m["b"]):
                total[p] += 1
    print("  外援PK外援 的场次:", bad)
    print("  男双混合队(外援+内部) 数:", mixed)
    print("  场次:", dict(sorted(total.items(), key=lambda x: (-x[1], x))))


if __name__ == "__main__":
    main()
