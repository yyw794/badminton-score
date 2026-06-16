#!/usr/bin/env python3
"""羽毛球比赛统计脚本"""

import json
import os
from collections import defaultdict

# 选手名单纠正
CORRECTION = {
    "李棋棋": "李祺祺",
}

def correct_name(name):
    """纠正选手名字"""
    return CORRECTION.get(name, name)

def parse_score(score_str):
    """解析比分字符串，返回 (score_a, score_b) 元组"""
    if not score_str:
        return None, None
    parts = score_str.split(":")
    return int(parts[0]), int(parts[1])

def get_match_winner(match):
    """
    根据两局比分判断每队赢了多少局
    返回 (team_a_wins, team_b_wins)
    """
    score_a1, score_b1 = parse_score(match["score_a"])
    score_a2, score_b2 = parse_score(match["score_b"])
    
    team_a_sets = 0
    team_b_sets = 0
    
    if score_a1 is not None and score_b1 is not None:
        if score_a1 > score_b1:
            team_a_sets += 1
        else:
            team_b_sets += 1
    
    if score_a2 is not None and score_b2 is not None:
        if score_a2 > score_b2:
            team_a_sets += 1
        else:
            team_b_sets += 1
    
    return team_a_sets, team_b_sets

def calculate_stats(json_path):
    """计算统计数据"""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    matches = data["matches"]
    
    # 统计每个人的胜负（按局统计）+ 净胜分
    player_stats = defaultdict(lambda: {"wins": 0, "losses": 0, "net_score": 0, "matches": []})
    
    # 统计每种类型的胜负（按选手在该类型的表现，按局统计）+ 净胜分
    type_stats = defaultdict(lambda: defaultdict(lambda: {"wins": 0, "losses": 0, "net_score": 0, "matches": []}))
    
    print("=" * 60)
    print(f"比赛日期: {data['match_date']}")
    print(f"比赛描述: {data['description']}")
    print(f"赛制: {data['format']}")
    print("=" * 60)
    
    print(f"\n共 {len(matches)} 场比赛")
    
    # 比赛详情
    print("\n" + "=" * 60)
    print("比赛详情:")
    print("=" * 60)
    for match in matches:
        round_num = match["round"]
        court = match["court"]
        match_type = match["type"]
        team_a = " / ".join([correct_name(p) for p in match["team_a"]])
        team_b = " / ".join([correct_name(p) for p in match["team_b"]])
        score_a = match["score_a"] or "-"
        score_b = match["score_b"] or "-"
        notes = match.get("notes", "")
        
        print(f"\n第{round_num}轮 {court}号场地 [{match_type}]")
        print(f"  {team_a} vs {team_b}")
        print(f"  第1局: {score_a}, 第2局: {score_b}")
        if notes:
            print(f"  备注: {notes}")
    
    # 逐场比赛分析（按局统计）
    print("\n" + "=" * 60)
    print("选手胜负统计（按局统计）:")
    print("=" * 60)
    
    for match in matches:
        team_a = [correct_name(p) for p in match["team_a"]]
        team_b = [correct_name(p) for p in match["team_b"]]
        match_type = match["type"]
        
        # 解析两局比分
        score_a1, score_b1 = parse_score(match["score_a"])
        score_a2, score_b2 = parse_score(match["score_b"])
        
        # 第1局统计
        if score_a1 is not None and score_b1 is not None:
            if score_a1 > score_b1:
                first_winner = team_a
                first_loser = team_b
            else:
                first_winner = team_b
                first_loser = team_a
            
            # 计算第1局净胜分
            set1_net = score_a1 - score_b1  # 正值表示对阵A净胜，负值表示对阵B净胜
            
            for player in team_a:
                player_stats[player]["matches"].append({
                    "round": match["round"],
                    "court": match["court"],
                    "type": match_type,
                    "set": 1,
                    "score": match["score_a"],
                    "result": "win" if player in first_winner else "loss"
                })
                type_stats[match_type][player]["matches"].append({
                    "round": match["round"],
                    "court": match["court"],
                    "set": 1,
                    "score": match["score_a"],
                    "result": "win" if player in first_winner else "loss"
                })
                if player in first_winner:
                    player_stats[player]["wins"] += 1
                    type_stats[match_type][player]["wins"] += 1
                else:
                    player_stats[player]["losses"] += 1
                    type_stats[match_type][player]["losses"] += 1
                # 净胜分：对阵A方获得 set1_net
                player_stats[player]["net_score"] += set1_net
                type_stats[match_type][player]["net_score"] += set1_net
            
            for player in team_b:
                player_stats[player]["matches"].append({
                    "round": match["round"],
                    "court": match["court"],
                    "type": match_type,
                    "set": 1,
                    "score": match["score_a"],
                    "result": "win" if player in first_winner else "loss"
                })
                type_stats[match_type][player]["matches"].append({
                    "round": match["round"],
                    "court": match["court"],
                    "set": 1,
                    "score": match["score_a"],
                    "result": "win" if player in first_winner else "loss"
                })
                if player in first_winner:
                    player_stats[player]["wins"] += 1
                    type_stats[match_type][player]["wins"] += 1
                else:
                    player_stats[player]["losses"] += 1
                    type_stats[match_type][player]["losses"] += 1
                # 净胜分：对阵B方获得 -set1_net
                player_stats[player]["net_score"] -= set1_net
                type_stats[match_type][player]["net_score"] -= set1_net
        
        # 第2局统计
        if score_a2 is not None and score_b2 is not None:
            if score_a2 > score_b2:
                second_winner = team_a
                second_loser = team_b
            else:
                second_winner = team_b
                second_loser = team_a
            
            # 计算第2局净胜分
            set2_net = score_a2 - score_b2
            
            for player in team_a:
                player_stats[player]["matches"].append({
                    "round": match["round"],
                    "court": match["court"],
                    "type": match_type,
                    "set": 2,
                    "score": match["score_b"],
                    "result": "win" if player in second_winner else "loss"
                })
                type_stats[match_type][player]["matches"].append({
                    "round": match["round"],
                    "court": match["court"],
                    "set": 2,
                    "score": match["score_b"],
                    "result": "win" if player in second_winner else "loss"
                })
                if player in second_winner:
                    player_stats[player]["wins"] += 1
                    type_stats[match_type][player]["wins"] += 1
                else:
                    player_stats[player]["losses"] += 1
                    type_stats[match_type][player]["losses"] += 1
                player_stats[player]["net_score"] += set2_net
                type_stats[match_type][player]["net_score"] += set2_net
            
            for player in team_b:
                player_stats[player]["matches"].append({
                    "round": match["round"],
                    "court": match["court"],
                    "type": match_type,
                    "set": 2,
                    "score": match["score_b"],
                    "result": "win" if player in second_winner else "loss"
                })
                type_stats[match_type][player]["matches"].append({
                    "round": match["round"],
                    "court": match["court"],
                    "set": 2,
                    "score": match["score_b"],
                    "result": "win" if player in second_winner else "loss"
                })
                if player in second_winner:
                    player_stats[player]["wins"] += 1
                    type_stats[match_type][player]["wins"] += 1
                else:
                    player_stats[player]["losses"] += 1
                    type_stats[match_type][player]["losses"] += 1
                player_stats[player]["net_score"] -= set2_net
                type_stats[match_type][player]["net_score"] -= set2_net
    
    # 计算胜率并排名
    print("\n" + "=" * 60)
    print("选手排名（按胜率）:")
    print("=" * 60)
    
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
    
    # 按胜率降序，胜场数降序，净胜分降序，总场次降序
    rank_list.sort(key=lambda x: (-x["win_rate"], -x["wins"], -x["net_score"], -x["total"]))
    
    print(f"\n{'排名':<4}{'选手':<10}{'胜':<6}{'负':<6}{'总':<6}{'胜率':<8}{'净胜分':<8}")
    print("-" * 48)
    for i, item in enumerate(rank_list, 1):
        print(f"{i:<4}{item['name']:<10}{item['wins']:<6}{item['losses']:<6}{item['total']:<6}{item['win_rate']:.1%}{item['net_score']:<+8}")
    
    # 按类型统计胜率（每个类型内按胜率排名选手）
    print("\n" + "=" * 60)
    print("各类型胜率统计（按类型排名选手）:")
    print("=" * 60)
    
    for match_type, players in type_stats.items():
        type_rank = []
        for player, stats in players.items():
            total = stats["wins"] + stats["losses"]
            win_rate = stats["wins"] / total if total > 0 else 0
            type_rank.append({
                "name": player,
                "wins": stats["wins"],
                "losses": stats["losses"],
                "net_score": stats["net_score"],
                "total": total,
                "win_rate": win_rate
            })
        
        type_rank.sort(key=lambda x: (-x["win_rate"], -x["wins"], -x["net_score"], -x["total"]))
        
        print(f"\n[{match_type}]")
        print(f"{'排名':<4}{'选手':<10}{'胜':<6}{'负':<6}{'总':<6}{'胜率':<8}{'净胜分':<8}")
        print("-" * 48)
        for i, item in enumerate(type_rank, 1):
            print(f"{i:<4}{item['name']:<10}{item['wins']:<6}{item['losses']:<6}{item['total']:<6}{item['win_rate']:.1%}{item['net_score']:<+8}")
    
    return rank_list, type_rank


def find_scores_dir():
    """Find scores directory from current working directory"""
    pwd = os.getcwd()
    if os.path.isdir(os.path.join(pwd, "scores")):
        return os.path.join(pwd, "scores")
    for _ in range(5):
        parent = os.path.dirname(pwd)
        if parent == pwd:
            break
        if os.path.isdir(os.path.join(parent, "scores")):
            return os.path.join(parent, "scores")
        pwd = parent
    return None


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="羽毛球比赛统计脚本")
    parser.add_argument("json_path", nargs="?", default=None, help="match_data.json 路径（默认：自动查找）")
    args = parser.parse_args()
    
    if args.json_path:
        json_path = args.json_path
    else:
        # 自动查找：当前目录 > scores 目录 > scores/日期目录
        scores_dir = find_scores_dir()
        if scores_dir and os.path.exists(os.path.join(scores_dir, "match_data.json")):
            json_path = os.path.join(scores_dir, "match_data.json")
        elif os.path.exists("match_data.json"):
            json_path = "match_data.json"
        else:
            # 查找最近的日期目录
            if scores_dir:
                for d in sorted(os.listdir(scores_dir), reverse=True):
                    if os.path.isdir(os.path.join(scores_dir, d)) and os.path.exists(os.path.join(scores_dir, d, "match_data.json")):
                        json_path = os.path.join(scores_dir, d, "match_data.json")
                        break
                else:
                    print(f"错误：未找到 match_data.json")
                    print(f"用法: python3 calculate_stats.py [match_data.json路径]")
                    sys.exit(1)
            else:
                print(f"错误：未找到 match_data.json")
                print(f"用法: python3 calculate_stats.py [match_data.json路径]")
                sys.exit(1)
    
    if not os.path.exists(json_path):
        print(f"错误：未找到 {json_path}")
        sys.exit(1)
    
    calculate_stats(json_path)
