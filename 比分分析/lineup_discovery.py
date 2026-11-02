#!/usr/bin/env python3
"""工会杯主备名单挖掘：按项目(男单/女单/混双/女双/男双)统计
- 个人分项目胜率/战绩
- 组合分项目战绩(混双男/女、男双、女双)
- 兼顾近期(windows: 最近4周) 与 全部
"""
import json, glob, os
from collections import defaultdict

ROOT = os.path.normpath(os.path.dirname(__file__) + '/..')
json_files = sorted([f for f in glob.glob(f'{ROOT}/活动/*/比分/match_data.json')
                     if '/history/' not in f and os.path.isfile(f)])

# ---------- 载入θ（与 BT排名总表 保持一致：直接用 20260928 的 theta） ----------
theta_src = json.load(open(f'{ROOT}/活动/2026-09-28/比分/bt_theta_ratings.json'))
theta = {p: v['theta'] for p, v in theta_src['players'].items()}

TYPMAP = {"男双": "MD", "混双": "XD", "女双": "WD", "男单": "MS", "女单": "WS", "女双vs混双": "WDvsXD"}

# 内部名单（excel_exporter 口径）
INTERNAL_M = {"苏大哲","严勇文","陈顺星","陈小洪","卢志辉","林锋","王小波","刘继宇","董广博","林琪琛","罗琴荩","陈财贵","范智强","王苏丹"}
GUEST_M = {"张欣欣","黄冬青","程建兴","陈宇霆","卢子龙","吴煜","罗蒙","江锐","刘海锐"}
INTERNAL_F = {"唐英武","李祺祺","高洁","滕菲","谢卓珊","崔倩男","林小连","徐越","李佳琳"}
GUEST_F = {"张燕红","李杏芝","项小英","田茜","曹杨"}

def is_male(p): return p in INTERNAL_M or p in GUEST_M
def is_female(p): return p in INTERNAL_F or p in GUEST_F

# ---------- 数据收集 ----------
# per_player[(type, player)] = {w, l}
# per_pair[(type, pair)] = {w, l, opps:[...]}
player_stats = defaultdict(lambda: {"w": 0, "l": 0})
pair_stats = defaultdict(lambda: {"w": 0, "l": 0, "recent_w": 0, "recent_l": 0, "dates": []})
recents = {"2026-09-07","2026-09-14","2026-09-21","2026-09-28"}

all_matches = []
for fp in json_files:
    data = json.load(open(fp))
    date = data.get('match_date') or os.path.basename(os.path.dirname(fp))
    for m in data.get('matches', []):
        m['_date'] = date
        all_matches.append(m)

for m in all_matches:
    typ = m.get('type','?')
    if typ not in TYPMAP: continue
    code = TYPMAP[typ]
    a, b = m['team_a'], m['team_b']
    for sk in (0, 1):
        s = [m['score_a'], m['score_b']][sk]
        try: sa, sb = map(int, str(s).split(':'))
        except Exception: continue
        if sa == sb: continue
        aw = sa > sb
        recent = m['_date'] in recents
        # 个人
        for p in a: player_stats[(code, p)]["w" if aw else "l"] += 1
        for p in b: player_stats[(code, p)]["w" if (not aw) else "l"] += 1
        # 组合(双打)
        if len(a) == 2 and len(b) == 2:
            for team, won in ((a, aw), (b, not aw)):
                pair = tuple(sorted(team))
                ps = pair_stats[(code, pair)]
                ps["w" if won else "l"] += 1
                if recent:
                    ps["recent_w" if won else "recent_l"] += 1
                ps["dates"].append(m['_date'])

def fmt_ttl(s):
    t = s["w"] + s["l"]
    wr = s["w"] / t * 100 if t else 0
    return f"{s['w']}/{t} {wr:4.0f}%"

def fmt_pair(p, s):
    t = s["w"] + s["l"]
    wr = s["w"] / t * 100 if t else 0
    return f"{p[0]}/{p[1]}: {s['w']}W{s['l']}L ({wr:.0f}%)"

def show_personal(code, label, name_filter, min_n=2):
    rows = []
    for (c, p), s in player_stats.items():
        if c != code: continue
        if not name_filter(p): continue
        t = s["w"] + s["l"]
        if t < min_n: continue
        rows.append((p, s))
    rows.sort(key=lambda x: -(x[1]["w"] / (x[1]["w"] + x[1]["l"])))
    print(f"\n===== {label} [{code}] (≥{min_n}局) =====")
    print(f"{'选手':<8}{'θ':>7}{'战绩':<14}{'胜率':>7}")
    for p, s in rows:
        t = s["w"] + s["l"]
        wr = s["w"] / t * 100
        th = f"{theta[p]:.2f}" if p in theta else " -- "
        print(f"{p:<8}{th:>7}{s['w']}/{t:<10} {wr:>5.1f}%")
    return rows

def show_pairs(code, label, min_n=2, only=None):
    rows = []
    for (c, pair), s in pair_stats.items():
        if c != code: continue
        t = s["w"] + s["l"]
        if t < min_n: continue
        if only and not only(pair): continue
        rows.append((pair, s))
    rows.sort(key=lambda x: -(x[1]["w"] / (x[1]["w"] + x[1]["l"])))
    print(f"\n===== {label} [组合 {code}, ≥{min_n}局] =====")
    print(f"{'组合':<18}{'局数':>4}{'战绩':<10}{'胜率':>7}  近期(4周)")
    for pair, s in rows:
        t = s["w"] + s["l"]
        wr = s["w"] / t * 100
        rt = s["recent_w"] + s["recent_l"]
        rstr = f"{s['recent_w']}/{rt}" if rt else " - "
        print(f"{pair[0]}/{pair[1]:<13}{t:>4}{s['w']}W{s['l']}L  {wr:>5.1f}%  {rstr}")
    return rows

if __name__ == "__main__":
    print("#" * 78)
    print("#  工会杯主备名单挖掘 —— 全部17场训练 + 近期4周(09-07~09-28) ")
    print("#" * 78)

    print("\n【θ 全览】")
    # 按性别打印θ
    male_row = [(p, theta[p]) for p in theta if is_male(p)]
    fem_row = [(p, theta[p]) for p in theta if is_female(p)]
    male_row.sort(key=lambda x: -x[1]); fem_row.sort(key=lambda x: -x[1])
    print("男  : " + "  ".join(f"{p}({t:.2f})" for p, t in male_row))
    print("女  : " + "  ".join(f"{p}({t:.2f})" for p, t in fem_row))

    # ============ 男单 ============
    show_personal("MS", "男单", lambda p: True)
    # ============ 女单 ============
    show_personal("WS", "女单", lambda p: True)
    # ============ 混双 ============
    show_personal("XD", "混双-男", is_male)
    show_personal("XD", "混双-女", is_female)
    show_pairs("XD", "混双组合")
    # ============ 男双 ============
    show_personal("MD", "男双-个人", is_male)
    show_pairs("MD", "男双组合")
    # ============ 女双 ============
    show_personal("WD", "女双-个人", is_female)
    show_pairs("WD", "女双组合")

    # ============ 关键组合矩阵 ============
    print("\n" + "=" * 78)
    print("🔍 关键组合矩阵（混双 & 男双备选）")
    print("=" * 78)
    key_xd_males = ["林锋", "王小波", "陈顺星", "刘继宇", "范智强", "罗琴荩", "严勇文"]
    key_females = ["徐越", "李祺祺", "李佳琳", "滕菲", "唐英武", "林小连", "张燕红", "项小英", "田茜", "崔倩男", "谢卓珊", "曹杨"]
    print("\n--- 混双组合(男性x女性) ---")
    for mm in key_xd_males:
        for ff in key_females:
            key = tuple(sorted([mm, ff]))
            s = pair_stats[("XD", key)]
            t = s["w"] + s["l"]
            if t:
                print(f"  {mm}×{ff}: {s['w']}/{t} ({s['w']/t*100:.0f}%)")
    print("\n--- 男双组合(内部x内部, ≥1局) ---")
    def pair_total(s): return s["w"] + s["l"]
    for (c, pair), s in sorted(pair_stats.items(), key=lambda x: -pair_total(x[1])):
        if c != "MD": continue
        t = pair_total(s)
        if t < 1: continue
        if not (is_male(pair[0]) and is_male(pair[1])): continue
        wr = s["w"] / t * 100
        print(f"  {pair[0]}/{pair[1]}: {s['w']}W{s['l']}L ({t}局, {wr:.0f}%)")

    # ============ 近期活跃度（谁还在打） ============
    print("\n" + "=" * 78)
    print("📅 近期(09-07~09-28)各项目参与情况")
    print("=" * 78)
    for code, label in [("MS","男单"),("WS","女单"),("XD","混双"),("WD","女双"),("MD","男双")]:
        vars_by_player = defaultdict(lambda: {"w":0,"l":0})
        for (c, p), s in player_stats.items():
            if c != code: continue
            # 因为 player_stats 是全量，需从 recent 再算 —— 用 pair 方式近似，这里直接重算
        # 重算近期个人
        recent_p = defaultdict(lambda: {"w":0,"l":0})
        for m in all_matches:
            if m['_date'] not in recents: continue
            typ = m.get('type','?')
            if TYPMAP.get(typ) != code: continue
            a, b = m['team_a'], m['team_b']
            for sk in (0,1):
                s = [m['score_a'], m['score_b']][sk]
                try: sa, sb = map(int, str(s).split(':'))
                except Exception: continue
                if sa == sb: continue
                aw = sa > sb
                for p in a: recent_p[p]["w" if aw else "l"] += 1
                for p in b: recent_p[p]["w" if (not aw) else "l"] += 1
        print(f"\n[{label}]")
        for p, s in sorted(recent_p.items(), key=lambda x: -x[1]["w"]/(x[1]["w"]+x[1]["l"]) if x[1]["w"]+x[1]["l"] else 0):
            t = s["w"] + s["l"]
            if t == 0: continue
            wr = s["w"]/t*100
            print(f"  {p:<8} {s['w']}/{t}局 ({wr:.0f}%)")
