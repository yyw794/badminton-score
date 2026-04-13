#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
羽毛球比分统计程序 - 调试版本
从原始比分数据自动计算各项统计数据
"""

from collections import defaultdict

# 原始比分数据
MATCH_DATA = [
    # 第1轮
    {"round": 1, "court": 1, "type": "女双", "team_a": ["李祺祺", "田茜"], "team_b": ["滕菲", "崔倩男"], "score_a": "14:15", "score_b": "15:8"},
    {"round": 1, "court": 2, "type": "男双", "team_a": ["严勇文", "卢志辉"], "team_b": ["罗蒙", "陈顺星"], "score_a": "14:15", "score_b": "8:15"},
    {"round": 1, "court": 3, "type": "男双", "team_a": ["林锋", "罗琴荩"], "team_b": ["苏大哲", "刘继宇"], "score_a": "14:15", "score_b": "10:15"},
    
    # 第2轮
    {"round": 2, "court": 1, "type": "女双", "team_a": ["李祺祺", "崔倩男"], "team_b": ["滕菲", "田茜"], "score_a": "10:15", "score_b": "14:15"},
    {"round": 2, "court": 2, "type": "男双", "team_a": ["严勇文", "黄冬青"], "team_b": ["陈小洪", "王小波"], "score_a": "12:15", "score_b": "15:10"},
    {"round": 2, "court": 3, "type": "男双", "team_a": ["林锋", "罗琴荩"], "team_b": ["陈顺星", "苏大哲"], "score_a": "15:14", "score_b": "14:15"},
    
    # 第3轮
    {"round": 3, "court": 1, "type": "女双", "team_a": ["崔倩男", "田茜"], "team_b": ["李祺祺", "滕菲"], "score_a": "10:15", "score_b": "10:15"},
    {"round": 3, "court": 2, "type": "男双", "team_a": ["严勇文", "卢志辉"], "team_b": ["刘继宇", "王小波"], "score_a": "15:10", "score_b": "12:15"},
    {"round": 3, "court": 3, "type": "男双", "team_a": ["罗蒙", "黄冬青"], "team_b": ["陈顺星", "陈小洪"], "score_a": "15:10", "score_b": "15:13"},
    
    # 第4轮
    {"round": 4, "court": 1, "type": "女双", "team_a": ["滕菲", "田茜"], "team_b": ["李祺祺", "崔倩男"], "score_a": "10:15", "score_b": "10:15"},
    {"round": 4, "court": 2, "type": "男双", "team_a": ["严勇文", "罗蒙"], "team_b": ["苏大哲", "刘继宇"], "score_a": "10:15", "score_b": "9:15"},
    {"round": 4, "court": 3, "type": "男双", "team_a": ["林锋", "罗琴荩"], "team_b": ["陈小洪", "王小波"], "score_a": "15:12", "score_b": "15:7"},
    
    # 第5轮
    {"round": 5, "court": 1, "type": "混双", "team_a": ["陈顺星", "李祺祺"], "team_b": ["王小波", "崔倩男"], "score_a": "13:15", "score_b": "10:15"},
    {"round": 5, "court": 2, "type": "混双", "team_a": ["林锋", "滕菲"], "team_b": ["罗琴荩", "田茜"], "score_a": "15:14", "score_b": "15:12"},
    {"round": 5, "court": 3, "type": "男双", "team_a": ["严勇文", "黄冬青"], "team_b": ["罗蒙", "卢志辉"], "score_a": "15:11", "score_b": "15:12"},
    
    # 第6轮
    {"round": 6, "court": 1, "type": "混双", "team_a": ["罗蒙", "李祺祺"], "team_b": ["陈顺星", "田茜"], "score_a": "8:15", "score_b": "7:15"},
    {"round": 6, "court": 2, "type": "男双", "team_a": ["苏大哲", "陈小洪"], "team_b": ["刘继宇", "卢志辉"], "score_a": "15:10", "score_b": "12:15"},
    {"round": 6, "court": 3, "type": "男双", "team_a": ["罗琴荩", "黄冬青"], "team_b": ["林锋", "王小波"], "score_a": "15:12", "score_b": "12:15"},
    
    # 第7轮
    {"round": 7, "court": 1, "type": "混双", "team_a": ["罗蒙", "李祺祺"], "team_b": ["林锋", "滕菲"], "score_a": "6:15", "score_b": "8:15"},
    {"round": 7, "court": 2, "type": "男双", "team_a": ["苏大哲", "刘继宇"], "team_b": ["陈小洪", "卢志辉"], "score_a": "15:10", "score_b": "15:10"},
    {"round": 7, "court": 3, "type": "男双", "team_a": ["黄冬青", "王小波"], "team_b": ["陈顺星", "罗琴荩"], "score_a": "15:10", "score_b": "15:10"},
    
    # 第8轮
    {"round": 8, "court": 1, "type": "混双", "team_a": ["陈顺星", "滕菲"], "team_b": ["王小波", "田茜"], "score_a": "13:15", "score_b": "11:15"},
    {"round": 8, "court": 2, "type": "男双", "team_a": ["刘继宇", "卢志辉"], "team_b": ["苏大哲", "陈小洪"], "score_a": "12:15", "score_b": "12:15"},
    {"round": 8, "court": 3, "type": "男双", "team_a": ["罗蒙", "罗琴荩"], "team_b": ["林锋", "黄冬青"], "score_a": "12:15", "score_b": "10:15"},
]

def parse_score(score_str):
    """解析比分字符串，返回(对阵A得分, 对阵B得分)"""
    parts = score_str.split(":")
    return int(parts[0]), int(parts[1])

def determine_winner(score_str):
    """
    根据比分判断哪方获胜
    score_str格式: "对阵A得分:对阵B得分"
    返回: "A" 或 "B"
    """
    score_a, score_b = parse_score(score_str)
    
    # 达到15分的一方获胜
    if score_a == 15 and score_b < 15:
        return "A"
    elif score_b == 15 and score_a < 15:
        return "B"
    elif score_a > 15:
        return "A"
    elif score_b > 15:
        return "B"
    else:
        return "A" if score_a > score_b else "B"

def calculate_statistics():
    """计算所有统计数据"""
    player_stats = defaultdict(lambda: {"wins": 0, "losses": 0, "matches": []})
    
    for match in MATCH_DATA:
        match_type = match["type"]
        team_a = match["team_a"]
        team_b = match["team_b"]
        score_a = match["score_a"]
        score_b = match["score_b"]
        
        winner_game_a = determine_winner(score_a)
        winner_game_b = determine_winner(score_b)
        
        # 统计第一局
        if winner_game_a == "A":
            for player in team_a:
                player_stats[player]["wins"] += 1
                player_stats[player]["matches"].append(f"第{match['round']}轮场地{match['court']}局A胜({score_a})")
            for player in team_b:
                player_stats[player]["losses"] += 1
                player_stats[player]["matches"].append(f"第{match['round']}轮场地{match['court']}局A负({score_a})")
        else:
            for player in team_b:
                player_stats[player]["wins"] += 1
                player_stats[player]["matches"].append(f"第{match['round']}轮场地{match['court']}局A胜({score_a})")
            for player in team_a:
                player_stats[player]["losses"] += 1
                player_stats[player]["matches"].append(f"第{match['round']}轮场地{match['court']}局A负({score_a})")
        
        # 统计第二局
        if winner_game_b == "B":
            for player in team_b:
                player_stats[player]["wins"] += 1
                player_stats[player]["matches"].append(f"第{match['round']}轮场地{match['court']}局B胜({score_b})")
            for player in team_a:
                player_stats[player]["losses"] += 1
                player_stats[player]["matches"].append(f"第{match['round']}轮场地{match['court']}局B负({score_b})")
        else:
            for player in team_a:
                player_stats[player]["wins"] += 1
                player_stats[player]["matches"].append(f"第{match['round']}轮场地{match['court']}局B胜({score_b})")
            for player in team_b:
                player_stats[player]["losses"] += 1
                player_stats[player]["matches"].append(f"第{match['round']}轮场地{match['court']}局B负({score_b})")
    
    return player_stats

def main():
    print("开始统计...\n")
    player_stats = calculate_statistics()
    
    # 输出刘继宇的详细记录
    target_player = "刘继宇"
    print(f"【{target_player}详细比赛记录】")
    print("-" * 70)
    if target_player in player_stats:
        stats = player_stats[target_player]
        print(f"总胜局: {stats['wins']}")
        print(f"总负局: {stats['losses']}")
        print(f"总局数: {stats['wins'] + stats['losses']}")
        print(f"\n详细比赛:")
        for m in stats['matches']:
            print(f"  - {m}")
    else:
        print("未找到该球员")

if __name__ == "__main__":
    main()
