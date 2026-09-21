#!/usr/bin/env python3
"""羽毛球趣味统计分析"""

import json
from collections import defaultdict, Counter

JSON_PATH = "scores/20260803/match_data.json"


def parse_score(s):
    a, b = s.split(":")
    return int(a), int(b)


def main():
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    matches = data["matches"]

    # ============================================================
    # 1. 出场劳模 & 2. 不败金身 & 全败惨绿
    # ============================================================
    player_matches = defaultdict(list)
    player_set_wins = defaultdict(int)
    player_set_total = defaultdict(int)

    for m in matches:
        round_n = m["round"]
        court = m["court"]
        sa1, sb1 = parse_score(m["score_a"])
        sa2, sb2 = parse_score(m["score_b"])
        for p in m["team_a"]:
            player_matches[p].append(m)
            player_set_total[p] += 2
            if sa1 > sb1:
                player_set_wins[p] += 1
            if sa2 > sb2:
                player_set_wins[p] += 1
        for p in m["team_b"]:
            player_matches[p].append(m)
            player_set_total[p] += 2
            if sb1 > sa1:
                player_set_wins[p] += 1
            if sb2 > sa2:
                player_set_wins[p] += 1

    print("=" * 60)
    print("🔥 出场劳模（总局数最多）")
    print("=" * 60)
    total_sorted = sorted(player_set_total.items(), key=lambda x: -x[1])
    for p, n in total_sorted[:5]:
        wins = player_set_wins[p]
        print(f"  {p}: {n}局 ({wins}胜{n-wins}负)")

    print()
    print("=" * 60)
    print("💎 单场胜率王（出场≥8局的选手中胜率最高）")
    print("=" * 60)
    rates = []
    for p, n in player_set_total.items():
        if n >= 8:
            rates.append((p, player_set_wins[p] / n, player_set_wins[p], n))
    rates.sort(key=lambda x: -x[1])
    for p, r, w, n in rates[:5]:
        print(f"  {p}: {r:.1%} ({w}胜{n-w}负, 共{n}局)")

    # ============================================================
    # 3. 净胜分狂魔 & 惨案制造者
    # ============================================================
    player_net = defaultdict(int)
    set_results = []  # (round, court, team_a_str, team_b_str, diff, set_n, score)

    for m in matches:
        sa1, sb1 = parse_score(m["score_a"])
        sa2, sb2 = parse_score(m["score_b"])
        ta = "/".join(m["team_a"])
        tb = "/".join(m["team_b"])
        set_results.append((m["round"], m["court"], ta, tb, sa1 - sb1, 1, f"{sa1}:{sb1}"))
        set_results.append((m["round"], m["court"], ta, tb, sa2 - sb2, 2, f"{sa2}:{sb2}"))
        for p in m["team_a"]:
            player_net[p] += (sa1 - sb1) + (sa2 - sb2)
        for p in m["team_b"]:
            player_net[p] += (sb1 - sa1) + (sb2 - sa2)

    print()
    print("=" * 60)
    print("🔥 净胜分狂魔（每局狂虐对手最多）")
    print("=" * 60)
    net_sorted = sorted(player_net.items(), key=lambda x: -x[1])
    for p, n in net_sorted[:5]:
        avg = n / player_set_total[p]
        print(f"  {p}: 净胜 {n:+d} 分，场均 {avg:+.1f} 分/局")

    print()
    print("=" * 60)
    print("😱 惨案现场（单局分差最大的5局）")
    print("=" * 60)
    set_sorted = sorted(set_results, key=lambda x: -abs(x[4]))
    for r, c, ta, tb, diff, sn, score in set_sorted[:5]:
        winner = ta if diff > 0 else tb
        print(f"  R{r}C{c} 第{sn}局 {ta} vs {tb} → {score} ({winner} 净胜 {abs(diff)} 分)")

    print()
    print("=" * 60)
    print("⚡ 最焦灼的5局（分差最小，含1分险胜）")
    print("=" * 60)
    set_close = sorted([s for s in set_results if abs(s[4]) > 0], key=lambda x: abs(x[4]))
    for r, c, ta, tb, diff, sn, score in set_close[:5]:
        winner = ta if diff > 0 else tb
        print(f"  R{r}C{c} 第{sn}局 {ta} vs {tb} → {score} ({winner} 险胜 {abs(diff)} 分)")

    # ============================================================
    # 4. 黄金搭档（共同出场≥2次的组合）
    # ============================================================
    pair_stats = defaultdict(lambda: {"wins": 0, "total": 0, "net": 0})
    for m in matches:
        sa1, sb1 = parse_score(m["score_a"])
        sa2, sb2 = parse_score(m["score_b"])
        # team_a 组合
        if len(m["team_a"]) == 2:
            k = tuple(sorted(m["team_a"]))
            pair_stats[k]["total"] += 2
            pair_stats[k]["wins"] += (1 if sa1 > sb1 else 0) + (1 if sa2 > sb2 else 0)
            pair_stats[k]["net"] += (sa1 - sb1) + (sa2 - sb2)
        if len(m["team_b"]) == 2:
            k = tuple(sorted(m["team_b"]))
            pair_stats[k]["total"] += 2
            pair_stats[k]["wins"] += (1 if sb1 > sa1 else 0) + (1 if sb2 > sa2 else 0)
            pair_stats[k]["net"] += (sb1 - sa1) + (sb2 - sa2)

    print()
    print("=" * 60)
    print("🤝 黄金搭档（共同出场≥4局的组合胜率排名）")
    print("=" * 60)
    pairs = []
    for k, v in pair_stats.items():
        if v["total"] >= 4:
            pairs.append((k, v["wins"] / v["total"], v["wins"], v["total"], v["net"]))
    pairs.sort(key=lambda x: (-x[1], -x[4]))
    for (p1, p2), r, w, t, n in pairs:
        print(f"  {p1} & {p2}: {r:.1%} ({w}胜{t-w}负, 净胜{n:+d}分)")

    # ============================================================
    # 5. 逆转王（先输后赢的场次统计）
    # ============================================================
    comebacks = defaultdict(int)
    chokers = defaultdict(int)
    total_cb = 0

    for m in matches:
        sa1, sb1 = parse_score(m["score_a"])
        sa2, sb2 = parse_score(m["score_b"])
        # 第一局A赢但第二局B赢，或第一局B赢第二局A赢 → 发生逆转
        set1_Awin = sa1 > sb1
        set2_Awin = sa2 > sb2
        if set1_Awin != set2_Awin:
            total_cb += 1
            if set2_Awin:  # A队逆转
                for p in m["team_a"]:
                    comebacks[p] += 1
                for p in m["team_b"]:
                    chokers[p] += 1
            else:
                for p in m["team_b"]:
                    comebacks[p] += 1
                for p in m["team_a"]:
                    chokers[p] += 1

    print()
    print("=" * 60)
    print(f"🔄 逆转统计（24场中 {total_cb} 场打到了各自赢一局，占 {total_cb/24:.1%}）")
    print("=" * 60)
    cb_sorted = sorted(comebacks.items(), key=lambda x: -x[1])
    print("  逆转王（经历先输后赢并最终拿下场次最多）：")
    for p, n in cb_sorted[:5]:
        print(f"    {p}: {n} 次")
    print("  被逆转王（先赢后输被翻盘次数最多）：")
    ch_sorted = sorted(chokers.items(), key=lambda x: -x[1])
    for p, n in ch_sorted[:5]:
        print(f"    {p}: {n} 次")

    # ============================================================
    # 6. 场地玄学 & 轮次疲劳
    # ============================================================
    court_stats = defaultdict(lambda: {"sets": 0, "total_diff": 0, "a_wins": 0})
    round_stats = defaultdict(lambda: {"sets": 0, "total_diff": 0, "close_sets": 0})

    for m in matches:
        sa1, sb1 = parse_score(m["score_a"])
        sa2, sb2 = parse_score(m["score_b"])
        for (sa, sb) in [(sa1, sb1), (sa2, sb2)]:
            diff = sa - sb
            key = m["court"]
            court_stats[key]["sets"] += 1
            court_stats[key]["total_diff"] += abs(diff)
            if diff > 0:
                court_stats[key]["a_wins"] += 1
            rk = m["round"]
            round_stats[rk]["sets"] += 1
            round_stats[rk]["total_diff"] += abs(diff)
            if abs(diff) <= 2:
                round_stats[rk]["close_sets"] += 1

    print()
    print("=" * 60)
    print("🏟  场地玄学（1/2/3号场地平均每局分差）")
    print("=" * 60)
    for c in sorted(court_stats.keys()):
        v = court_stats[c]
        avg = v["total_diff"] / v["sets"]
        print(f"  {c}号场: 平均分差 {avg:.1f} 分，A队胜率 {v['a_wins']/v['sets']:.0%}")

    print()
    print("=" * 60)
    print("⏱  轮次疲劳观察（焦灼局比率 - 分差≤2分的局占比）")
    print("=" * 60)
    for r in sorted(round_stats.keys()):
        v = round_stats[r]
        close_rate = v["close_sets"] / v["sets"] * 100
        avg = v["total_diff"] / v["sets"]
        print(f"  第{r}轮: 焦灼局 {v['close_sets']}/{v['sets']} ({close_rate:.0f}%), 平均分差 {avg:.1f} 分")

    # ============================================================
    # 7. 男女选手混双表现对比
    # ============================================================
    females = {"田茜", "唐英武", "李祺祺", "高洁", "滕菲", "谢卓珊", "崔倩男", "林小连", "张燕红", "李杏芝", "项小英", "徐越"}
    # 注意：徐越也是女性（从混双配对：林锋/徐越、王小波/徐越、陈顺星/徐越判断）
    female_in_mixed = defaultdict(lambda: {"wins": 0, "total": 0, "net": 0})
    male_in_mixed = defaultdict(lambda: {"wins": 0, "total": 0, "net": 0})

    for m in matches:
        if m["type"] != "混双":
            continue
        sa1, sb1 = parse_score(m["score_a"])
        sa2, sb2 = parse_score(m["score_b"])
        for p in m["team_a"]:
            if p in females:
                female_in_mixed[p]["total"] += 2
                female_in_mixed[p]["wins"] += (1 if sa1 > sb1 else 0) + (1 if sa2 > sb2 else 0)
                female_in_mixed[p]["net"] += (sa1 - sb1) + (sa2 - sb2)
            else:
                male_in_mixed[p]["total"] += 2
                male_in_mixed[p]["wins"] += (1 if sa1 > sb1 else 0) + (1 if sa2 > sb2 else 0)
                male_in_mixed[p]["net"] += (sa1 - sb1) + (sa2 - sb2)
        for p in m["team_b"]:
            if p in females:
                female_in_mixed[p]["total"] += 2
                female_in_mixed[p]["wins"] += (1 if sb1 > sa1 else 0) + (1 if sb2 > sa2 else 0)
                female_in_mixed[p]["net"] += (sb1 - sa1) + (sb2 - sa2)
            else:
                male_in_mixed[p]["total"] += 2
                male_in_mixed[p]["wins"] += (1 if sb1 > sa1 else 0) + (1 if sb2 > sa2 else 0)
                male_in_mixed[p]["net"] += (sb1 - sa1) + (sb2 - sa2)

    print()
    print("=" * 60)
    print("👑 混双女王（混双中女选手胜率排名）")
    print("=" * 60)
    fm = []
    for p, v in female_in_mixed.items():
        fm.append((p, v["wins"] / v["total"], v["wins"], v["total"], v["net"]))
    fm.sort(key=lambda x: (-x[1], -x[4]))
    for p, r, w, t, n in fm:
        print(f"  {p}: {r:.1%} ({w}胜{t-w}负, 净胜{n:+d}分)")

    print()
    print("=" * 60)
    print("🦸 混双男帝（混双中男选手胜率排名）")
    print("=" * 60)
    mm = []
    for p, v in male_in_mixed.items():
        mm.append((p, v["wins"] / v["total"], v["wins"], v["total"], v["net"]))
    mm.sort(key=lambda x: (-x[1], -x[4]))
    for p, r, w, t, n in mm:
        print(f"  {p}: {r:.1%} ({w}胜{t-w}负, 净胜{n:+d}分)")

    # ============================================================
    # 8. 15:X 送蛋统计
    # ============================================================
    count_15_x = 0
    count_15_5_less = 0
    for r, c, ta, tb, diff, sn, score in set_results:
        a, b = parse_score(score)
        winner_s = max(a, b)
        loser_s = min(a, b)
        if winner_s == 15:
            count_15_x += 1
            if loser_s <= 5:
                count_15_5_less += 1
    print()
    print("=" * 60)
    print(f"🎯 送蛋统计（全场 48 局中）")
    print("=" * 60)
    print(f"  一方拿到 15 分的局数: {count_15_x} / 48 ({count_15_x/48:.1%})")
    print(f"  打到 15:5 及以下的碾压局: {count_15_5_less} / 48 ({count_15_5_less/48:.1%})")
    print(f"  平均每局得分: {sum(parse_score(s[6])[0]+parse_score(s[6])[1] for s in set_results)/len(set_results):.1f} 分")

    print()
    print("=" * 60)
    print("🗺  选手关系网（和最多不同队友搭档过的社交王）")
    print("=" * 60)
    partners = defaultdict(set)
    for m in matches:
        for p in m["team_a"]:
            for q in m["team_a"]:
                if p != q:
                    partners[p].add(q)
        for p in m["team_b"]:
            for q in m["team_b"]:
                if p != q:
                    partners[p].add(q)
    social = sorted(partners.items(), key=lambda x: -len(x[1]))
    for p, pals in social[:5]:
        print(f"  {p}: 搭档过 {len(pals)} 人 — {', '.join(sorted(pals))}")


if __name__ == "__main__":
    main()
