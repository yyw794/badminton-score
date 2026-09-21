#!/usr/bin/env python3
"""加权排名 v3 — 平衡版
核心设计原则（用户强调的逻辑）：
  ① 基本盘不能丢：总胜率是核心（70%权重），纯胜率高的人不可能被只有逆袭3局的人反超
  ② 难度加权做修正（30%）：把每局的"难度价值"加进去，但不能让逆袭3局就逆天改命
  ③ 队友含金量做二次惩罚/奖励：队友越差（队友均分高）自己排名高 → 加奖励分；队友越好排名高 → 扣水分
"""

import json
import sys
from collections import defaultdict


def load_match_data(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def compute_base_rank(match_data):
    player_stats = defaultdict(lambda: {"wins": 0, "losses": 0, "total": 0, "score_diff": 0})
    for match in match_data["matches"]:
        sa = match["score_a"].split(":")
        sb = match["score_b"].split(":")
        try:
            a1, b1 = int(sa[0]), int(sa[1])
            a2, b2 = int(sb[0]), int(sb[1])
        except (ValueError, IndexError):
            continue
        team_a = match["team_a"]
        team_b = match["team_b"]
        for s_a, s_b in [(a1, b1), (a2, b2)]:
            diff = s_a - s_b
            if s_a > s_b:
                for p in team_a:
                    player_stats[p]["wins"] += 1
                    player_stats[p]["total"] += 1
                    player_stats[p]["score_diff"] += diff
                for p in team_b:
                    player_stats[p]["losses"] += 1
                    player_stats[p]["total"] += 1
                    player_stats[p]["score_diff"] -= diff
            else:
                diff2 = s_b - s_a
                for p in team_a:
                    player_stats[p]["losses"] += 1
                    player_stats[p]["total"] += 1
                    player_stats[p]["score_diff"] -= diff2
                for p in team_b:
                    player_stats[p]["wins"] += 1
                    player_stats[p]["total"] += 1
                    player_stats[p]["score_diff"] += diff2

    players = list(player_stats.keys())
    players_sorted = sorted(
        players,
        key=lambda p: (
            player_stats[p]["wins"] / player_stats[p]["total"] if player_stats[p]["total"] else 0,
            player_stats[p]["score_diff"],
        ),
        reverse=True,
    )
    rank_score = {p: idx + 1 for idx, p in enumerate(players_sorted)}
    return rank_score, player_stats, players_sorted


def compute_components(match_data, rank_score, player_stats, players_sorted):
    data = defaultdict(lambda: {
        "wins": 0, "losses": 0, "total": 0,
        "weighted_wins": 0.0,
        "weighted_total": 0.0,
        "weighted_net": 0.0,
        "teammate_ranks": [],
        "opponent_ranks": [],
    })

    for match in match_data["matches"]:
        sa = match["score_a"].split(":")
        sb = match["score_b"].split(":")
        try:
            a1, b1 = int(sa[0]), int(sa[1])
            a2, b2 = int(sb[0]), int(sb[1])
        except (ValueError, IndexError):
            continue
        team_a = match["team_a"]
        team_b = match["team_b"]
        a_sum = sum(rank_score[p] for p in team_a)
        b_sum = sum(rank_score[p] for p in team_b)
        a_avg = a_sum / len(team_a)
        b_avg = b_sum / len(team_b)

        for s_a, s_b in [(a1, b1), (a2, b2)]:
            # 难度A = A方平均排名分 / B方平均排名分 （越大=越难打）
            # 范围压缩：难度^(0.5)，避免逆袭局过度放大权重（因为权重不超过总分30%）
            d_a = pow(a_avg / b_avg if b_avg else 1.0, 0.5)
            d_b = pow(b_avg / a_avg if a_avg else 1.0, 0.5)
            a_won = s_a > s_b

            for p in team_a:
                d = data[p]
                d["total"] += 1
                d["opponent_ranks"].extend(rank_score[q] for q in team_b)
                d["teammate_ranks"].extend(rank_score[q] for q in team_a if q != p)
                if a_won:
                    d["wins"] += 1
                    d["weighted_wins"] += d_a
                    d["weighted_total"] += d_a
                    d["weighted_net"] += d_a
                else:
                    d["losses"] += 1
                    pen = 1.0 / d_a if d_a > 0 else 1.0
                    d["weighted_total"] += pen
                    d["weighted_net"] -= pen

            for p in team_b:
                d = data[p]
                d["total"] += 1
                d["opponent_ranks"].extend(rank_score[q] for q in team_a)
                d["teammate_ranks"].extend(rank_score[q] for q in team_b if q != p)
                if not a_won:
                    d["wins"] += 1
                    d["weighted_wins"] += d_b
                    d["weighted_total"] += d_b
                    d["weighted_net"] += d_b
                else:
                    d["losses"] += 1
                    pen = 1.0 / d_b if d_b > 0 else 1.0
                    d["weighted_total"] += pen
                    d["weighted_net"] -= pen

    # 汇总
    results = []
    for p in players_sorted:
        d = data[p]
        wins = player_stats[p]["wins"]
        losses = player_stats[p]["losses"]
        total = wins + losses
        base_rate = wins / total if total else 0
        score_diff = player_stats[p]["score_diff"]
        net_per_set = score_diff / total if total else 0

        # 1) 难度加权胜率（赢的加权和 / 总加权和）—— 做差值修正
        wwr = d["weighted_wins"] / d["weighted_total"] if d["weighted_total"] else 0
        # delta = 加权胜率 - 普通胜率 （正=难度加权后更强，负=水分多）
        wwr_delta = wwr - base_rate

        # 2) 加权净分（每局）—— 难度加权后每局净得分
        wnps = d["weighted_net"] / total if total else 0

        # 3) 队友含金量
        tms = d["teammate_ranks"]
        avg_tm = sum(tms) / len(tms) if tms else rank_score[p]
        own = rank_score[p]
        # tm_diff = 自己排名分 - 队友均分
        # 负值：自己排名前，队友排名后 → 典型carry型（如黄冬青: 2-13.3=-11.3）
        # 正值：自己排名后，队友排名前 → 典型抱大腿型（如王小波: 20-10.7=+9.3）
        tm_diff = own - avg_tm

        # 4) 对手含金量
        opps = d["opponent_ranks"]
        avg_opp = sum(opps) / len(opps) if opps else 10
        # avg_opp小 = 对手都是高手 → 赢了更有价值；输了可以理解

        # ============ 最终综合分 ============
        # 基础盘 65% = base_rate * 100 + net_per_set * 4
        #   （原胜率做主导，净胜分/局做微调，保证基本盘稳定）
        #
        # 难度修正 20% = wwr_delta * 150 + wnps * 10
        #   （Δ胜正的加，负的扣；加权净局正的加）
        #
        # 队友含金量 15% =  (carry奖励 + 对手强度奖励)
        #   carry奖励 = -tm_diff * 2.0  （tm_diff负 → 加奖励分）
        #   对手强度奖励 = (10.5 - avg_opp) * 1.5  （avg_opp越小=对手越强 → 加的越多）
        base_comp = base_rate * 100.0 + net_per_set * 4.0
        diff_comp = wwr_delta * 150.0 + max(wnps, -2) * 10.0
        carry_reward = -tm_diff * 2.2
        opp_reward = (10.5 - avg_opp) * 1.6   # 对手分越小=对手越强 → 加越多
        tm_comp = carry_reward + opp_reward
        final_score = base_comp * 0.65 + diff_comp * 0.20 + tm_comp * 0.15

        results.append({
            "player": p,
            "own_rank": own,
            "wins": wins,
            "losses": losses,
            "total": total,
            "base_rate": base_rate,
            "net_per_set": net_per_set,
            "avg_teammate": avg_tm,
            "tm_diff": tm_diff,
            "avg_opponent": avg_opp,
            "wwr": wwr,
            "wwr_delta": wwr_delta,
            "wnps": wnps,
            "base_comp": base_comp,
            "diff_comp": diff_comp,
            "tm_comp": tm_comp,
            "final_score": final_score,
        })

    return results


def print_table(results, sort_key, title):
    print("=" * 130)
    print(f"【{title}】")
    print("=" * 130)
    sorted_r = sorted(results, key=sort_key, reverse=True)
    print(
        f"{'排名':<4}{'选手':<7}{'原排':<5}{'胜':<3}{'负':<3}"
        f"{'原胜率':<8}{'加权胜':<8}{'Δ胜':<8}{'加权净/局':<11}"
        f"{'队友均':<7}{'队友差':<7}{'对手均':<7}{'综合分':<8}{'升降':<5}"
    )
    print("-" * 130)
    for i, r in enumerate(sorted_r):
        delta = r["own_rank"] - (i + 1)
        arrow = f"↑{delta}" if delta > 0 else (f"↓{-delta}" if delta < 0 else "=")
        print(
            f"{i+1:<4}{r['player']:<7}{r['own_rank']:<5}{r['wins']:<3}{r['losses']:<3}"
            f"{r['base_rate']*100:<7.1f}%{r['wwr']*100:<7.1f}%"
            f"{r['wwr_delta']*100:<+7.1f}%"
            f"{r['wnps']:<+10.2f} "
            f"{r['avg_teammate']:<6.1f}{r['tm_diff']:<+6.1f}{r['avg_opponent']:<6.1f}"
            f"{r['final_score']:<7.2f}{arrow}"
        )
    print()
    return sorted_r


def main():
    if len(sys.argv) < 2:
        path = "scores/20260817/match_data.json"
    else:
        path = sys.argv[1]

    md = load_match_data(path)
    rank_score, player_stats, players_sorted = compute_base_rank(md)
    results = compute_components(md, rank_score, player_stats, players_sorted)

    print("加权排名 v3（平衡版）— 65%原胜率 + 20%难度修正 + 15%队友/对手含金量奖励")
    print("=" * 130)
    print("设计说明：")
    print("  ① 原胜率占65% —— 保证战绩基本盘决定位置（不会3胜9负反超9胜3负）")
    print("  ② 难度修正20% —— 打赢难局（自己弱+对手强）加，翻船简单局扣")
    print("  ③ 含金量15% = carry奖励(队友越弱赢加分) + 对手强度奖励(对手越强赢加分)")
    print("  Δ胜 = 加权胜率 - 原胜率  （+ = 难度加权后更强，说明在打硬仗；- = 原胜率有水分）")
    print("=" * 130)
    print()

    sorted_final = print_table(results, lambda x: x["final_score"],
                               "综合加权排名（推荐使用）")

    print("=" * 130)
    print("【排名变动总结】")
    print("=" * 130)
    final_rank = {r["player"]: i + 1 for i, r in enumerate(sorted_final)}
    deltas = []
    for p in players_sorted:
        old = rank_score[p]
        new = final_rank[p]
        deltas.append((p, old, new, old - new))
    deltas.sort(key=lambda x: x[3], reverse=True)

    print("↑ 排名上升（原排名被低估，属于carry型/硬仗型选手）Top 5:")
    for p, old, new, d in deltas:
        if d > 0:
            print(f"   {p}: 第{old} → 第{new}，上升{d}名")
    print()
    print("↓ 排名下降（原排名含有水分，属于抱大腿/打弱队刷分选手）Top 5:")
    for p, old, new, d in deltas[::-1]:
        if d < 0:
            print(f"   {p}: 第{old} → 第{new}，下降{-d}名")
    print()


if __name__ == "__main__":
    main()
