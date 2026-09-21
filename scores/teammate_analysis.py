#!/usr/bin/env python3
"""队友含金量分析脚本
思路：用选手总排名作为其实力值（第1名=1分，第20名=20分，分数越小越强）
计算每个选手所有队友的排名分平均值，看是否抱大腿
"""

import json
import sys
from collections import defaultdict


def load_match_data(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def compute_player_ranks(match_data):
    """计算每个选手的胜负和排名，返回 (rank_score, wins, losses, total) dict"""
    player_stats = defaultdict(lambda: {"wins": 0, "losses": 0, "total": 0})

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

        # 第1局
        if a1 > b1:
            for p in team_a:
                player_stats[p]["wins"] += 1
                player_stats[p]["total"] += 1
            for p in team_b:
                player_stats[p]["losses"] += 1
                player_stats[p]["total"] += 1
        else:
            for p in team_a:
                player_stats[p]["losses"] += 1
                player_stats[p]["total"] += 1
            for p in team_b:
                player_stats[p]["wins"] += 1
                player_stats[p]["total"] += 1

        # 第2局
        if a2 > b2:
            for p in team_a:
                player_stats[p]["wins"] += 1
                player_stats[p]["total"] += 1
            for p in team_b:
                player_stats[p]["losses"] += 1
                player_stats[p]["total"] += 1
        else:
            for p in team_a:
                player_stats[p]["losses"] += 1
                player_stats[p]["total"] += 1
            for p in team_b:
                player_stats[p]["wins"] += 1
                player_stats[p]["total"] += 1

    # 按胜率+净胜分排序，分配排名分（1=最强，N=最弱）
    players = list(player_stats.keys())

    def score(p):
        s = player_stats[p]
        win_rate = s["wins"] / s["total"] if s["total"] else 0
        # 用胜率+净胜分替代，但这里只需要排名
        return (win_rate, s["wins"])

    players_sorted = sorted(players, key=lambda p: (player_stats[p]["wins"] / player_stats[p]["total"] if player_stats[p]["total"] else 0, -player_stats[p]["total"]), reverse=True)

    rank_score = {}  # 第1名=1分，第20名=20分
    for idx, p in enumerate(players_sorted):
        rank_score[p] = idx + 1  # 排名分，越小越强

    return rank_score, player_stats, players_sorted


def collect_teammates(match_data):
    """收集每个选手的所有队友（按每次搭档计一次）"""
    teammates = defaultdict(list)  # player -> [(round, court, teammate)]
    for match in match_data["matches"]:
        rd = match["round"]
        ct = match["court"]
        team_a = match["team_a"]
        team_b = match["team_b"]

        for i, p in enumerate(team_a):
            for j, q in enumerate(team_a):
                if i != j:
                    teammates[p].append((rd, ct, q))

        for i, p in enumerate(team_b):
            for j, q in enumerate(team_b):
                if i != j:
                    teammates[p].append((rd, ct, q))

    return teammates


def main():
    if len(sys.argv) < 2:
        path = "scores/20260817/match_data.json"
    else:
        path = sys.argv[1]

    data = load_match_data(path)
    rank_score, stats, players_sorted = compute_player_ranks(data)
    teammates = collect_teammates(data)

    print("=" * 80)
    print("队友含金量分析")
    print("说明：排名分越小代表实力越强（第1名=1分，第20名=20分）")
    print("队友平均分越小 = 抱大腿越多（队友都很强）")
    print("队友平均分越大 = 带飞队友越多（队友都较弱）")
    print("=" * 80)
    print()

    results = []
    for p in players_sorted:
        my_rank = rank_score[p]
        tm_list = teammates[p]
        if not tm_list:
            tm_avg = 0
            tm_count = 0
            unique_tm = []
        else:
            scores = [rank_score[t[2]] for t in tm_list if t[2] in rank_score]
            tm_avg = sum(scores) / len(scores) if scores else 0
            tm_count = len(tm_list)
            unique_tm = list(set(t[2] for t in tm_list))

        # 差值：自己排名分 - 队友平均分
        # 正数 = 自己排名分大(弱)但队友平均分小(强) = 抱大腿
        # 负数 = 自己排名分小(强)但队友平均分大(弱) = 带飞队友
        diff = my_rank - tm_avg if tm_avg else 0

        results.append({
            "player": p,
            "my_rank": my_rank,
            "wins": stats[p]["wins"],
            "losses": stats[p]["losses"],
            "win_rate": stats[p]["wins"] / stats[p]["total"] * 100 if stats[p]["total"] else 0,
            "teammate_avg": tm_avg,
            "teammate_count": tm_count,
            "unique_teammates": unique_tm,
            "diff": diff,
        })

    # 表格输出
    header = f"{'排名':<3}{'选手':<6}{'胜':<3}{'负':<3}{'胜率':<7}{'排名分':<6}{'队友均分':<8}{'队友数':<5}{'差值':<7}{'结论'}"
    print(header)
    print("-" * 80)

    for i, r in enumerate(results):
        diff = r["diff"]
        if diff > 3:
            conclusion = "★ 抱大腿严重"
        elif diff > 0.5:
            conclusion = "↗ 抱大腿略多"
        elif diff < -3:
            conclusion = "★★ 真正大腿"
        elif diff < -0.5:
            conclusion = "↘ 带飞队友"
        else:
            conclusion = "= 中规中矩"

        print(f"{i+1:<3}{r['player']:<6}{r['wins']:<3}{r['losses']:<3}{r['win_rate']:<6.1f}%{r['my_rank']:<6}{r['teammate_avg']:<7.2f}{r['teammate_count']:<5}{diff:<+6.2f}{conclusion}")

    print()
    print("=" * 80)
    print("详细分析（按'差值'排序 — 正数抱大腿，负数带飞）：")
    print("=" * 80)
    print()

    results_sorted = sorted(results, key=lambda x: x["diff"], reverse=True)
    for i, r in enumerate(results_sorted):
        diff = r["diff"]
        if diff > 3:
            tag = "【抱大腿王】"
        elif diff > 0.5:
            tag = "【略抱大腿】"
        elif diff < -3:
            tag = "【真正大腿】"
        elif diff < -0.5:
            tag = "【带飞队友】"
        else:
            tag = "【中规中矩】"

        teammates_str = ", ".join(
            f"{t}(排名{rank_score[t]})" for t in sorted(r["unique_teammates"], key=lambda x: rank_score[x])
        )
        print(f"{i+1}. {tag} {r['player']} — 自己排名分 {r['my_rank']}，队友均分 {r['teammate_avg']:.2f}，差值 {diff:+.2f}")
        print(f"   队友：{teammates_str}")
        print()


if __name__ == "__main__":
    main()
