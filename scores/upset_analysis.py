#!/usr/bin/env python3
"""以弱胜强分析脚本
思路：用每队总排名分作为纸面实力（分数越小=越强）
如果A队总分 > B队（A纸面更弱），但A赢了 → 记为一次以弱胜强，体现配合/化学反应
"""

import json
import sys
from collections import defaultdict


def load_match_data(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def compute_rank_score(match_data):
    """计算每个选手的排名分（第1名=1分，越小越强）"""
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

        for score_a_s, score_b_s in [(a1, b1), (a2, b2)]:
            if score_a_s > score_b_s:
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

    players = list(player_stats.keys())
    players_sorted = sorted(
        players,
        key=lambda p: (
            player_stats[p]["wins"] / player_stats[p]["total"] if player_stats[p]["total"] else 0,
            -player_stats[p]["total"],
        ),
        reverse=True,
    )
    rank_score = {p: idx + 1 for idx, p in enumerate(players_sorted)}
    return rank_score, player_stats, players_sorted


def main():
    if len(sys.argv) < 2:
        path = "scores/20260817/match_data.json"
    else:
        path = sys.argv[1]

    data = load_match_data(path)
    rank_score, stats, players_sorted = compute_rank_score(data)

    print("=" * 90)
    print("以弱胜强分析（纸面实力逆袭 = 配合/化学反应好）")
    print("说明：排名分越小实力越强；每队'纸面实力分'=队内成员排名分之和")
    print("纸面分高的队=纸面更弱，若赢了就是'逆袭'，体现配合加成")
    print("=" * 90)
    print()

    # 统计每局的逆袭情况
    upsets = []
    player_upset = defaultdict(lambda: {"upset_wins": 0, "upset_losses": 0,
                                         "favored_wins": 0, "favored_losses": 0,
                                         "total_sets": 0})
    pair_upset = defaultdict(lambda: {"upset_wins": 0, "upset_losses": 0,
                                       "favored_wins": 0, "favored_losses": 0,
                                       "total_sets": 0,
                                       "upset_margin_sum": 0})  # 逆袭的实力差之和

    for match in data["matches"]:
        sa = match["score_a"].split(":")
        sb = match["score_b"].split(":")
        try:
            a1, b1 = int(sa[0]), int(sa[1])
            a2, b2 = int(sb[0]), int(sb[1])
        except (ValueError, IndexError):
            continue

        team_a = match["team_a"]
        team_b = match["team_b"]
        rd = match["round"]
        ct = match["court"]
        mtype = match["type"]

        score_a_total = sum(rank_score[p] for p in team_a)
        score_b_total = sum(rank_score[p] for p in team_b)

        for set_idx, (sa_s, sb_s) in enumerate([(a1, b1), (a2, b2)]):
            set_num = set_idx + 1
            paper_diff = score_a_total - score_b_total  # +→A纸面弱，-→A纸面强
            margin = abs(paper_diff)  # 纸面实力差距

            if sa_s > sb_s:  # A赢了
                winner = team_a
                loser = team_b
                if paper_diff > 0:  # A纸面更弱但赢了 = 逆袭！
                    is_upset = True
                    upset_type = "A逆袭B"
                else:
                    is_upset = False
                    upset_type = "A正常赢B"
            else:  # B赢了
                winner = team_b
                loser = team_a
                if paper_diff < 0:  # B纸面更弱（A分更小）但赢了 = 逆袭！
                    is_upset = True
                    upset_type = "B逆袭A"
                else:
                    is_upset = False
                    upset_type = "B正常赢A"

            # 记录本局
            upsets.append({
                "round": rd,
                "court": ct,
                "type": mtype,
                "set": set_num,
                "team_a": team_a,
                "team_b": team_b,
                "score": f"{sa_s}:{sb_s}",
                "paper_a": score_a_total,
                "paper_b": score_b_total,
                "paper_diff": abs(paper_diff),
                "winner": winner,
                "loser": loser,
                "is_upset": is_upset,
                "upset_type": upset_type,
            })

            # 统计选手个人
            for p in team_a:
                player_upset[p]["total_sets"] += 1
                if sa_s > sb_s:  # A赢
                    if paper_diff > 0:
                        player_upset[p]["upset_wins"] += 1  # 以弱胜强赢了
                    else:
                        player_upset[p]["favored_wins"] += 1  # 纸面强正常赢
                else:  # A输
                    if paper_diff > 0:
                        player_upset[p]["upset_losses"] += 1  # 纸面弱正常输
                    else:
                        player_upset[p]["favored_losses"] += 1  # 纸面强被逆袭输了
            for p in team_b:
                player_upset[p]["total_sets"] += 1
                if sb_s > sa_s:  # B赢
                    if paper_diff < 0:
                        player_upset[p]["upset_wins"] += 1
                    else:
                        player_upset[p]["favored_wins"] += 1
                else:  # B输
                    if paper_diff < 0:
                        player_upset[p]["upset_losses"] += 1
                    else:
                        player_upset[p]["favored_losses"] += 1

            # 统计搭档组合（队）
            def add_pair(team, won, is_upset_p, margin_val):
                if len(team) < 2:
                    return
                key = tuple(sorted(team))
                pair_upset[key]["total_sets"] += 1
                if won and is_upset_p:
                    pair_upset[key]["upset_wins"] += 1
                    pair_upset[key]["upset_margin_sum"] += margin_val
                elif won and not is_upset_p:
                    pair_upset[key]["favored_wins"] += 1
                elif not won and is_upset_p:
                    pair_upset[key]["upset_losses"] += 1
                else:
                    pair_upset[key]["favored_losses"] += 1

            a_won = sa_s > sb_s
            a_is_upset = a_won and paper_diff > 0
            b_won = sb_s > sa_s
            b_is_upset = b_won and paper_diff < 0
            add_pair(team_a, a_won, a_is_upset, margin)
            add_pair(team_b, b_won, b_is_upset, margin)

    # ============ 第一部分：所有逆袭局 ============
    print(f"【第一部分】全场共 {len(upsets)} 局，逆袭局数统计：")
    total_upsets = sum(1 for u in upsets if u["is_upset"])
    print(f"  总逆袭局数：{total_upsets} / {len(upsets)} = {total_upsets / len(upsets) * 100:.1f}%")
    print()

    if total_upsets > 0:
        print("最精彩的逆袭TOP10（按纸面实力差距从大到小）：")
        print("-" * 90)
        print(f"{'轮次':<4}{'场地':<4}{'类型':<4}{'局':<3}{'获胜方':<22}{'胜纸面分':<8}{'败方':<22}{'败纸面分':<8}{'实力差':<6}{'比分'}")
        print("-" * 90)
        upset_sorted = sorted([u for u in upsets if u["is_upset"]], key=lambda x: x["paper_diff"], reverse=True)
        for u in upset_sorted[:10]:
            winner_str = "/".join(u["winner"])
            loser_str = "/".join(u["loser"])
            if u["upset_type"].startswith("A"):  # A赢
                w_paper = u["paper_a"]
                l_paper = u["paper_b"]
            else:
                w_paper = u["paper_b"]
                l_paper = u["paper_a"]
            print(f"{u['round']:<4}{u['court']:<4}{u['type']:<4}{u['set']:<3}{winner_str:<22}{w_paper:<8}{loser_str:<22}{l_paper:<8}{u['paper_diff']:<6}{u['score']}")
        print()

    # ============ 第二部分：选手个人逆袭能力 ============
    print("=" * 90)
    print("【第二部分】选手个人逆袭能力排名")
    print("指标说明：")
    print("  逆袭胜率 = 以弱胜强赢的局数 / (以弱胜强赢+以弱胜强输)")
    print("  被逆袭率 = 纸面强时被对手翻盘输的局数 / (纸面强赢+纸面强输)")
    print("  逆袭王：逆袭胜率高，且逆袭局数多")
    print("  被逆袭王：纸面强时经常被翻盘（说明自己发挥不稳/拖累队友）")
    print("=" * 90)
    print()

    player_results = []
    for p in players_sorted:
        d = player_upset[p]
        upset_total = d["upset_wins"] + d["upset_losses"]
        favored_total = d["favored_wins"] + d["favored_losses"]
        upset_rate = d["upset_wins"] / upset_total if upset_total else 0
        upset_loss_rate = d["favored_losses"] / favored_total if favored_total else 0

        player_results.append({
            "player": p,
            "rank": rank_score[p],
            "upset_wins": d["upset_wins"],
            "upset_losses": d["upset_losses"],
            "upset_rate": upset_rate,
            "upset_total": upset_total,
            "favored_wins": d["favored_wins"],
            "favored_losses": d["favored_losses"],
            "upset_loss_rate": upset_loss_rate,
            "favored_total": favored_total,
        })

    print("【逆袭王】（按逆袭胜率排序，逆袭局≥2的）：")
    print("-" * 90)
    print(f"{'排名':<4}{'选手':<6}{'个人排名':<7}{'逆袭胜':<5}{'逆袭败':<5}{'逆袭总数':<7}{'逆袭胜率':<9}{'强方胜':<6}{'强方败':<6}{'被逆袭率':<9}")
    print("-" * 90)
    pr_upset = sorted([x for x in player_results if x["upset_total"] >= 2],
                      key=lambda x: (x["upset_rate"], x["upset_wins"]), reverse=True)
    for i, r in enumerate(pr_upset):
        tag = ""
        if i == 0:
            tag = "👑 逆袭王"
        elif r["upset_rate"] >= 0.6:
            tag = "⭐ 强力逆袭"
        elif r["upset_rate"] <= 0.2:
            tag = "💀 从不逆袭"
        print(f"{i+1:<4}{r['player']:<6}{r['rank']:<7}{r['upset_wins']:<5}{r['upset_losses']:<5}{r['upset_total']:<7}{r['upset_rate']*100:<8.1f}%{r['favored_wins']:<6}{r['favored_losses']:<6}{r['upset_loss_rate']*100:<8.1f}% {tag}")
    print()

    print("【被逆袭王】（纸面强时被翻盘输掉的比例，≥2局纸面强的）：")
    print("-" * 90)
    print(f"{'排名':<4}{'选手':<6}{'个人排名':<7}{'强方胜':<6}{'强方败':<6}{'强方总数':<7}{'被逆袭率':<9}{'逆袭胜':<5}{'逆袭败':<5}")
    print("-" * 90)
    pr_upset_l = sorted([x for x in player_results if x["favored_total"] >= 2],
                        key=lambda x: x["upset_loss_rate"], reverse=True)
    for i, r in enumerate(pr_upset_l[:10]):
        tag = ""
        if i == 0:
            tag = "💀 最易被翻盘"
        elif r["upset_loss_rate"] >= 0.5:
            tag = "⚠️ 经常掉链子"
        print(f"{i+1:<4}{r['player']:<6}{r['rank']:<7}{r['favored_wins']:<6}{r['favored_losses']:<6}{r['favored_total']:<7}{r['upset_loss_rate']*100:<8.1f}%{r['upset_wins']:<5}{r['upset_losses']:<5} {tag}")
    print()

    # ============ 第三部分：搭档组合配合加成 ============
    print("=" * 90)
    print("【第三部分】搭档组合配合加成（化学反应最好的组合）")
    print("筛选：出赛≥4局的组合")
    print("配合好 = 逆袭胜多 + 逆袭胜率高 + 纸面差距大还能赢")
    print("=" * 90)
    print()

    pair_results = []
    for (p1, p2), d in pair_upset.items():
        if d["total_sets"] < 4:
            continue
        upset_total = d["upset_wins"] + d["upset_losses"]
        upset_rate = d["upset_wins"] / upset_total if upset_total else 0
        avg_upset_margin = d["upset_margin_sum"] / d["upset_wins"] if d["upset_wins"] else 0
        total_win = d["upset_wins"] + d["favored_wins"]
        total_rate = total_win / d["total_sets"] if d["total_sets"] else 0
        pair_results.append({
            "pair": f"{p1}/{p2}",
            "p1_rank": rank_score[p1],
            "p2_rank": rank_score[p2],
            "rank_sum": rank_score[p1] + rank_score[p2],
            "total_sets": d["total_sets"],
            "total_win": total_win,
            "total_rate": total_rate,
            "upset_wins": d["upset_wins"],
            "upset_losses": d["upset_losses"],
            "upset_rate": upset_rate,
            "favored_wins": d["favored_wins"],
            "favored_losses": d["favored_losses"],
            "avg_upset_margin": avg_upset_margin,
        })

    # 按逆袭胜数+逆袭胜率排序
    print("【最佳化学反应组合】（综合逆袭场次多 + 逆袭胜率高）：")
    print("-" * 100)
    print(f"{'排名':<4}{'组合':<18}{'组合分':<7}{'总局':<5}{'总胜':<5}{'总胜率':<8}{'逆袭胜':<6}{'逆袭败':<6}{'逆袭胜率':<9}{'平均逆转差':<10}")
    print("-" * 100)
    pair_sorted = sorted(pair_results, key=lambda x: (x["upset_wins"] * 100 + x["upset_rate"]), reverse=True)
    for i, r in enumerate(pair_sorted[:10]):
        tag = ""
        if r["upset_wins"] >= 3 and r["upset_rate"] >= 0.7:
            tag = "🔥 超强化学反应"
        elif r["upset_wins"] >= 2 and r["upset_rate"] >= 0.6:
            tag = "✨ 配合加成明显"
        elif r["upset_wins"] == 0 and r["total_rate"] < 0.4:
            tag = "💔 组合相克"
        avg_m = f"{r['avg_upset_margin']:.1f}" if r["avg_upset_margin"] else "-"
        print(f"{i+1:<4}{r['pair']:<18}{r['rank_sum']:<7}{r['total_sets']:<5}{r['total_win']:<5}{r['total_rate']*100:<7.1f}%{r['upset_wins']:<6}{r['upset_losses']:<6}{r['upset_rate']*100:<8.1f}%{avg_m:<10}{tag}")


if __name__ == "__main__":
    main()
