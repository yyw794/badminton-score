#!/usr/bin/env python3
"""
活动数据存档到 SQLite 数据库
每次活动后自动保存，支持历史查询和统计
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict, Optional


DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data.db")


def get_db_connection():
    """获取数据库连接。"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库表结构。"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 活动表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_name TEXT NOT NULL,
            event_date TEXT NOT NULL,
            court_count INTEGER DEFAULT 3,
            total_matches INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 比赛表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            match_round INTEGER NOT NULL,
            court INTEGER NOT NULL,
            match_type TEXT NOT NULL,
            team_a TEXT NOT NULL,
            team_b TEXT NOT NULL,
            score_a1 INTEGER DEFAULT 0,
            score_b1 INTEGER DEFAULT 0,
            score_a2 INTEGER DEFAULT 0,
            score_b2 INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending',
            FOREIGN KEY (event_id) REFERENCES events (id)
        )
    """)
    
    # 球员表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            gender TEXT DEFAULT 'M',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 参赛记录表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS participations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            player_id INTEGER NOT NULL,
            match_id INTEGER NOT NULL,
            match_type TEXT NOT NULL,
            team TEXT NOT NULL,
            score_team INTEGER DEFAULT 0,
            score_opponent INTEGER DEFAULT 0,
            is_winner BOOLEAN DEFAULT 0,
            FOREIGN KEY (event_id) REFERENCES events (id),
            FOREIGN KEY (player_id) REFERENCES players (id),
            FOREIGN KEY (match_id) REFERENCES matches (id)
        )
    """)
    
    conn.commit()
    conn.close()
    print("✓ 数据库表初始化完成")


def save_event_data(event_name: str, matches: List[Dict], court_count: int = 3) -> int:
    """保存活动数据到数据库。
    
    Args:
        event_name: 活动名称
        matches: 比赛列表
        court_count: 场地数量
    
    Returns:
        event_id: 活动 ID
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 获取或创建球员
    player_ids = {}
    all_players = set()
    for match in matches:
        for player in match.get("teamA", []) + match.get("teamB", []):
            all_players.add(player)
    
    for player in all_players:
        cursor.execute("SELECT id FROM players WHERE name = ?", (player,))
        row = cursor.fetchone()
        if row:
            player_ids[player] = row["id"]
        else:
            # 简单判断性别（根据名字或单独配置）
            gender = "F" if player in ["田茜", "唐英武", "李祺祺", "高洁", "滕菲", "谢卓珊", "崔倩男", "林小连"] else "M"
            cursor.execute("INSERT INTO players (name, gender) VALUES (?, ?)", (player, gender))
            player_ids[player] = cursor.lastrowid
    
    # 创建活动记录
    event_date = datetime.now().strftime("%Y-%m-%d")
    cursor.execute(
        "INSERT INTO events (event_name, event_date, court_count, total_matches) VALUES (?, ?, ?, ?)",
        (event_name, event_date, court_count, len(matches))
    )
    event_id = cursor.lastrowid
    
    # 保存比赛数据
    for match in matches:
        team_a = ",".join(match.get("teamA", []))
        team_b = ",".join(match.get("teamB", []))
        
        score_a = match.get("scoreA", [0, 0])
        score_b = match.get("scoreB", [0, 0])
        
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
            event_id, match.get("round", 1), match.get("court", 1),
            match.get("type", ""), team_a, team_b,
            score_a[0] if score_a else 0, score_b[0] if score_b else 0,
            score_a[1] if len(score_a) > 1 else 0, score_b[1] if len(score_b) > 1 else 0,
            match.get("status", "pending")
        ))
        match_id = cursor.lastrowid
        
        # 保存参赛记录
        for player in match.get("teamA", []):
            if player in player_ids:
                cursor.execute("""
                    INSERT INTO participations 
                    (event_id, player_id, match_id, match_type, team, score_team, score_opponent, is_winner)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event_id, player_ids[player], match_id, match.get("type", ""),
                    "A", total_a, total_b, 1 if is_team_a_winner else 0
                ))
        
        for player in match.get("teamB", []):
            if player in player_ids:
                cursor.execute("""
                    INSERT INTO participations 
                    (event_id, player_id, match_id, match_type, team, score_team, score_opponent, is_winner)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event_id, player_ids[player], match_id, match.get("type", ""),
                    "B", total_b, total_a, 0 if is_team_a_winner else 1
                ))
    
    conn.commit()
    conn.close()
    print(f"✓ 活动数据已保存到数据库 (event_id={event_id})")
    return event_id


def get_event_history(limit: int = 10) -> List[Dict]:
    """获取历史活动列表。
    
    Args:
        limit: 返回数量限制
    
    Returns:
        活动列表
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, event_name, event_date, court_count, total_matches, created_at
        FROM events
        ORDER BY event_date DESC
        LIMIT ?
    """, (limit,))
    
    events = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return events


def get_player_stats(player_name: Optional[str] = None) -> List[Dict]:
    """获取球员统计数据。
    
    Args:
        player_name: 球员姓名，为空则返回所有球员
    
    Returns:
        统计数据列表
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if player_name:
        cursor.execute("""
            SELECT 
                p.name,
                p.gender,
                COUNT(DISTINCT pa.event_id) as events,
                COUNT(pa.id) as total_matches,
                SUM(pa.is_winner) as wins,
                SUM(CASE WHEN pa.match_type = '混双' THEN 1 ELSE 0 END) as mixed,
                SUM(CASE WHEN pa.match_type = '男双' THEN 1 ELSE 0 END) as mens,
                SUM(CASE WHEN pa.match_type = '女双' THEN 1 ELSE 0 END) as womens
            FROM players p
            LEFT JOIN participations pa ON p.id = pa.player_id
            WHERE p.name = ?
            GROUP BY p.id
        """, (player_name,))
    else:
        cursor.execute("""
            SELECT 
                p.name,
                p.gender,
                COUNT(DISTINCT pa.event_id) as events,
                COUNT(pa.id) as total_matches,
                SUM(pa.is_winner) as wins,
                SUM(CASE WHEN pa.match_type = '混双' THEN 1 ELSE 0 END) as mixed,
                SUM(CASE WHEN pa.match_type = '男双' THEN 1 ELSE 0 END) as mens,
                SUM(CASE WHEN pa.match_type = '女双' THEN 1 ELSE 0 END) as womens
            FROM players p
            LEFT JOIN participations pa ON p.id = pa.player_id
            GROUP BY p.id
            ORDER BY total_matches DESC
        """)
    
    stats = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return stats


def get_event_details(event_id: int) -> Optional[Dict]:
    """获取活动详细信息。
    
    Args:
        event_id: 活动 ID
    
    Returns:
        活动详情
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 获取活动基本信息
    cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,))
    event = cursor.fetchone()
    if not event:
        conn.close()
        return None
    
    # 获取比赛列表
    cursor.execute("SELECT * FROM matches WHERE event_id = ? ORDER BY match_round, court", (event_id,))
    matches = [dict(row) for row in cursor.fetchall()]
    
    # 获取参赛球员
    cursor.execute("""
        SELECT DISTINCT p.name, p.gender
        FROM players p
        JOIN participations pa ON p.id = pa.player_id
        WHERE pa.event_id = ?
    """, (event_id,))
    players = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return {
        "event": dict(event),
        "matches": matches,
        "players": players
    }


def export_to_json(output_path: str = None) -> str:
    """导出所有数据为 JSON。
    
    Args:
        output_path: 输出路径，默认在数据库同目录
    
    Returns:
        输出文件路径
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 导出所有活动
    cursor.execute("SELECT * FROM events ORDER BY event_date DESC")
    events = [dict(row) for row in cursor.fetchall()]
    
    # 导出所有比赛
    cursor.execute("SELECT * FROM matches")
    matches = [dict(row) for row in cursor.fetchall()]
    
    # 导出所有球员
    cursor.execute("SELECT * FROM players")
    players = [dict(row) for row in cursor.fetchall()]
    
    # 导出所有参赛记录
    cursor.execute("SELECT * FROM participations")
    participations = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    data = {
        "export_time": datetime.now().isoformat(),
        "events": events,
        "matches": matches,
        "players": players,
        "participations": participations
    }
    
    if output_path is None:
        output_path = os.path.join(os.path.dirname(DB_PATH), "data_archive.json")
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"✓ 数据已导出到 {output_path}")
    return output_path


def main():
    """主函数：初始化数据库并显示统计信息。"""
    print("🏸 羽毛球活动数据管理")
    print("=" * 40)
    
    # 初始化数据库
    init_db()
    
    # 显示历史活动
    events = get_event_history()
    if events:
        print(f"\n📅 最近 {len(events)} 次活动:")
        for event in events:
            print(f"  - {event['event_date']}: {event['event_name']} ({event['total_matches']}场比赛)")
    else:
        print("\n暂无活动记录")
    
    # 显示球员统计
    stats = get_player_stats()
    if stats:
        print(f"\n👤 球员统计 (共{len(stats)}人):")
        for s in stats[:10]:  # 显示前 10 名
            win_rate = s['wins'] / s['total_matches'] * 100 if s['total_matches'] > 0 else 0
            print(f"  - {s['name']}: {s['total_matches']}场 | 胜{s['wins']} | 胜率{win_rate:.1f}%")
    
    print("\n" + "=" * 40)
    print("使用方法:")
    print("  python db.py init          # 初始化数据库")
    print("  python db.py export        # 导出数据为 JSON")
    print("  python db.py stats [姓名]  # 查看统计数据")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "init":
            init_db()
        elif command == "export":
            export_to_json()
        elif command == "stats":
            player_name = sys.argv[2] if len(sys.argv) > 2 else None
            stats = get_player_stats(player_name)
            if stats:
                for s in stats:
                    win_rate = s['wins'] / s['total_matches'] * 100 if s['total_matches'] > 0 else 0
                    print(f"{s['name']}: {s['total_matches']}场 | 胜{s['wins']} | 胜率{win_rate:.1f}%")
                    print(f"  混双:{s['mixed']} 男双:{s['mens']} 女双:{s['womens']}")
        else:
            main()
    else:
        main()
