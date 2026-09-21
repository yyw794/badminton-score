#!/usr/bin/env python3
"""羽毛球历史比分综合统计 - 合并所有match_data.json并统计"""

import json
import os
import glob
from collections import defaultdict

HISTORY_DIR = "/Users/yanyongwen712/Documents/pingan_tech_badminton_team/scores/history"
CORRECTION = {"李棋棋": "李祺祺"}

def correct_name(name):
    return CORRECTION.get(name, name)

def parse_score(score_str):
    if not score_str:
        return None, None
    parts = score_str.split(":")
    return int(parts[0]), int(parts[1])

def main():
    # Find all match_data JSON files
    json_files = sorted(glob.glob(os.path.join(HISTORY_DIR, "match_data_*.json")))

    if not json_files:
        print("未找到 match_data JSON 文件")
        return

    print(f"找到 {len(json_files)} 个 match_data 文件\n")

    # Collect all matches
    all_matches = []
    for json_file in json_files:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        matches = data.get("matches", [])
        all_matches.extend(matches)

    print(f"总计 {len(all_matches)} 场比赛\n")

    # Calculate stats
    player_stats = defaultdict(lambda: {"wins": 0, "losses": 0, "net_score": 0})

    for match in all_matches:
        team_a = [correct_name(p) for p in match["team_a"]]
        team_b = [correct_name(p) for p in match["team_b"]]
        score_a = match.get("score_a", "") or ""
        score_b = match.get("score_b", "") or ""

        # Parse scores
        score_a1, score_b1 = parse_score(score_a)
        score_a2, score_b2 = parse_score(score_b)

        # Set 1
        if score_a1 is not None and score_b1 is not None:
            winner = team_a if score_a1 > score_b1 else team_b
            loser = team_b if score_a1 > score_b1 else team_a
            net = score_a1 - score_b1

            for p in team_a:
                player_stats[p]["wins" if p in winner else "losses"] += 1
                player_stats[p]["net_score"] += (net if p in team_a else -net)
            for p in team_b:
                player_stats[p]["wins" if p in winner else "losses"] += 1
                player_stats[p]["net_score"] += (net if p in team_b else -net)

        # Set 2
        if score_a2 is not None and score_b2 is not None:
            winner = team_a if score_a2 > score_b2 else team_b
            loser = team_b if score_a2 > score_b2 else team_a
            net = score_a2 - score_b2

            for p in team_a:
                player_stats[p]["wins" if p in winner else "losses"] += 1
                player_stats[p]["net_score"] += (net if p in team_a else -net)
            for p in team_b:
                player_stats[p]["wins" if p in winner else "losses"] += 1
                player_stats[p]["net_score"] += (net if p in team_b else -net)

    # Build rank list
    rank_list = []
    for player, stats in player_stats.items():
        total = stats["wins"] + stats["losses"]
        win_rate = stats["wins"] / total if total > 0 else 0
        rank_list.append({
            "name": player,
            "wins": stats["wins"],
            "losses": stats["losses"],
            "total": total,
            "net_score": stats["net_score"],
            "win_rate": win_rate
        })

    # Sort by win rate, wins, net score, total
    rank_list.sort(key=lambda x: (-x["win_rate"], -x["wins"], -x["net_score"], -x["total"]))

    # Print ranking
    print("=" * 50)
    print("历史比分综合排名（按胜率）")
    print("=" * 50)
    print(f"\n{'排名':<4}{'选手':<10}{'胜':<6}{'负':<6}{'总':<6}{'胜率':<8}{'净胜分':<8}")
    print("-" * 48)
    for i, item in enumerate(rank_list, 1):
        print(f"{i:<4}{item['name']:<10}{item['wins']:<6}{item['losses']:<6}{item['total']:<6}{item['win_rate']:.1%}{item['net_score']:<+8}")

    # Print summary stats
    total_games = sum(m["wins"] + m["losses"] for m in rank_list)
    total_wins = sum(m["wins"] for m in rank_list)
    print(f"\n总计: {total_games} 局, {total_wins} 胜 {total_games - total_wins} 负")
    print(f"选手总数: {len(rank_list)}")

if __name__ == '__main__':
    main()
