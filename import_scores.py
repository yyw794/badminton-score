#!/usr/bin/env python3
"""
将 Web 导出的比分数据导入数据库
使用方法：uv run python import_scores.py 导出的文件.json
"""

import json
import os
import sys
from datetime import datetime

# 导入数据库模块
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(script_dir))
from db import get_db_connection, init_db


def import_scores(json_path: str):
    """将导出的 JSON 文件中的比分导入数据库。
    
    Args:
        json_path: JSON 文件路径
    """
    # 读取 JSON 文件
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    event_name = data.get('eventName', '未知活动')
    matches = data.get('matches', [])
    
    if not matches:
        print("✗ 没有找到比赛数据")
        return
    
    # 查找或创建活动记录
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 尝试从 eventName 中提取日期
    import re
    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', event_name)
    event_date = date_match.group(1) if date_match else datetime.now().strftime('%Y-%m-%d')
    
    # 检查是否已存在该活动
    cursor.execute(
        "SELECT id FROM events WHERE event_name = ? OR (event_name LIKE ? AND event_date = ?)",
        (event_name, f"%{event_date}%", event_date)
    )
    row = cursor.fetchone()
    
    if row:
        event_id = row['id']
        print(f"📅 找到已有活动：{event_name} (ID={event_id})")
        
        # 询问是否更新
        response = input("是否更新该活动的比分数据？(y/n): ")
        if response.lower() != 'y':
            # 创建新活动
            event_name = f"{event_name} (更新)"
    else:
        print(f"📅 创建新活动：{event_name}")
    
    # 创建活动记录
    cursor.execute(
        "INSERT INTO events (event_name, event_date, court_count, total_matches) VALUES (?, ?, ?, ?)",
        (event_name, event_date, data.get('courtCount', 3), len(matches))
    )
    event_id = cursor.lastrowid
    
    # 获取或创建球员
    player_ids = {}
    all_players = set()
    for match in matches:
        for player in match.get('teamA', []) + match.get('teamB', []):
            all_players.add(player)
    
    for player in all_players:
        cursor.execute("SELECT id FROM players WHERE name = ?", (player,))
        row = cursor.fetchone()
        if row:
            player_ids[player] = row['id']
        else:
            # 简单判断性别
            female_names = ["田茜", "唐英武", "李祺祺", "高洁", "滕菲", "谢卓珊", "崔倩男", "林小连", "林小连"]
            gender = "F" if player in female_names else "M"
            cursor.execute("INSERT INTO players (name, gender) VALUES (?, ?)", (player, gender))
            player_ids[player] = cursor.lastrowid
    
    # 保存比赛数据
    updated_count = 0
    for match in matches:
        team_a = ",".join(match.get('teamA', []))
        team_b = ",".join(match.get('teamB', []))
        
        score_a = match.get('scoreA', [0, 0])
        score_b = match.get('scoreB', [0, 0])
        
        # 计算总分和胜负
        total_a = sum(score_a) if score_a else 0
        total_b = sum(score_b) if score_b else 0
        is_team_a_winner = total_a > total_b
        
        cursor.execute("""
            INSERT INTO matches 
            (event_id, match_round, court, match_type, team_a, team_b, 
             score_a1, score_b1, score_a2, score_b2, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event_id, match.get('round', 1), match.get('court', 1),
            match.get('type', ''), team_a, team_b,
            score_a[0] if score_a else 0, score_b[0] if score_b else 0,
            score_a[1] if len(score_a) > 1 else 0, score_b[1] if len(score_b) > 1 else 0,
            match.get('status', 'finished')
        ))
        match_id = cursor.lastrowid
        
        # 保存参赛记录
        for player in match.get('teamA', []):
            if player in player_ids:
                cursor.execute("""
                    INSERT INTO participations 
                    (event_id, player_id, match_id, match_type, team, score_team, score_opponent, is_winner)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event_id, player_ids[player], match_id, match.get('type', ''),
                    "A", total_a, total_b, 1 if is_team_a_winner else 0
                ))
        
        for player in match.get('teamB', []):
            if player in player_ids:
                cursor.execute("""
                    INSERT INTO participations 
                    (event_id, player_id, match_id, match_type, team, score_team, score_opponent, is_winner)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event_id, player_ids[player], match_id, match.get('type', ''),
                    "B", total_b, total_a, 0 if is_team_a_winner else 1
                ))
        
        if match.get('status') == 'finished':
            updated_count += 1
    
    conn.commit()
    conn.close()
    
    print(f"✓ 已导入 {updated_count} 场已完成的比赛")
    print(f"✓ 活动 ID: {event_id}")


def main():
    if len(sys.argv) < 2:
        print("使用方法：uv run python import_scores.py <导出的 JSON 文件>")
        print("")
        print("示例:")
        print("  uv run python import_scores.py 2026-03-02_活动_比分数据.json")
        return
    
    json_path = sys.argv[1]
    
    if not os.path.exists(json_path):
        print(f"✗ 文件不存在：{json_path}")
        return
    
    init_db()
    import_scores(json_path)


if __name__ == "__main__":
    main()
