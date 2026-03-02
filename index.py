#!/usr/bin/env python3
"""
Vercel Serverless Function - 羽毛球比赛计分 API
部署：推送到 GitHub 后，在 Vercel 导入项目即可
"""

import json
import os
import mysql.connector
from mysql.connector import Error
from datetime import datetime
from typing import Optional
import uuid

# ==================== 数据库配置 ====================
DB_CONFIG = {
    'host': os.environ.get('TIDB_HOST', 'gateway01.ap-southeast-1.prod.aws.tidbcloud.com'),
    'port': int(os.environ.get('TIDB_PORT', '4000')),
    'user': os.environ.get('TIDB_USER', '8AXKPCJGEHG5Qqv.root'),
    'password': os.environ.get('TIDB_PASSWORD', ''),
    'database': os.environ.get('TIDB_DATABASE', 'test'),
    'ssl_ca': '/etc/ssl/cert.pem',
    'ssl_verify_cert': True,
}


def get_db_connection():
    """获取数据库连接"""
    return mysql.connector.connect(**DB_CONFIG)


def handler(request):
    """Vercel Serverless 入口函数"""
    
    # 设置 CORS
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
    }
    
    # 处理 OPTIONS 预检请求
    if request.method == 'OPTIONS':
        return {'statusCode': 200, 'headers': headers, 'body': ''}
    
    # 获取路径和方法
    path = request.path or '/'
    method = request.method or 'GET'
    
    # 读取请求体
    try:
        body = request.get_json() or {}
    except:
        body = {}
    
    # 路由处理
    response = route_request(path, method, body)
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps(response, ensure_ascii=False)
    }


def route_request(path: str, method: str, data: dict):
    """路由请求到对应处理函数"""
    path_parts = [p for p in path.split('/') if p]
    
    # GET /init - 初始化数据库
    if path == '/init' and method == 'GET':
        return init_db()
    
    # GET /events - 获取活动列表
    if path == '/events' and method == 'GET':
        return get_events()
    
    # POST /events - 创建活动
    if path == '/events' and method == 'POST':
        return create_event(data)
    
    # GET /events/{id} - 获取活动详情
    if len(path_parts) == 2 and path_parts[0] == 'events' and method == 'GET':
        return get_event(path_parts[1])
    
    # PUT /events/{id} - 更新活动
    if len(path_parts) == 2 and path_parts[0] == 'events' and method == 'PUT':
        return update_event(path_parts[1], data)
    
    # DELETE /events/{id} - 删除活动
    if len(path_parts) == 2 and path_parts[0] == 'events' and method == 'DELETE':
        return delete_event(path_parts[1])
    
    # GET /events/{id}/matches - 获取比赛列表
    if len(path_parts) == 3 and path_parts[0] == 'events' and path_parts[2] == 'matches' and method == 'GET':
        return get_matches(path_parts[1])
    
    # PUT /matches/{id} - 更新比赛比分
    if len(path_parts) == 2 and path_parts[0] == 'matches' and method == 'PUT':
        return update_match(path_parts[1], data)
    
    # GET /stats/{event_id} - 获取统计数据
    if len(path_parts) == 2 and path_parts[0] == 'stats' and method == 'GET':
        return get_stats(path_parts[1])
    
    return {"success": False, "error": "Not Found", "path": path}


# ==================== 业务逻辑 ====================

def init_db():
    """初始化数据库表结构"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id VARCHAR(36) PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            court_count INT DEFAULT 3,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            id VARCHAR(36) PRIMARY KEY,
            event_id VARCHAR(36) NOT NULL,
            round INT NOT NULL,
            court INT NOT NULL,
            type VARCHAR(20) NOT NULL,
            team_a JSON NOT NULL,
            team_b JSON NOT NULL,
            score_a1 INT DEFAULT 0,
            score_a2 INT DEFAULT 0,
            score_b1 INT DEFAULT 0,
            score_b2 INT DEFAULT 0,
            status VARCHAR(20) DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_event (event_id),
            INDEX idx_court (court),
            INDEX idx_round (round)
        )
    """)
    
    conn.commit()
    cursor.close()
    conn.close()
    return {"success": True, "message": "数据库表初始化完成"}


def get_events():
    """获取活动列表"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, name, court_count, created_at, updated_at FROM events ORDER BY created_at DESC")
    events = cursor.fetchall()
    cursor.close()
    conn.close()
    return {"success": True, "data": events}


def create_event(data: dict):
    """创建活动"""
    event_id = str(uuid.uuid4())
    name = data.get('name', '未命名活动')
    court_count = data.get('court_count', 3)
    matches = data.get('matches', [])
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("INSERT INTO events (id, name, court_count) VALUES (%s, %s, %s)", (event_id, name, court_count))
    
    if matches:
        for match in matches:
            score_a = match.get('scoreA', [0, 0])
            score_b = match.get('scoreB', [0, 0])
            match_id = match.get('id') or str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO matches 
                (id, event_id, round, court, type, team_a, team_b, score_a1, score_a2, score_b1, score_b2, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                match_id, event_id, match.get('round', 1), match.get('court', 1),
                match.get('type', ''), json.dumps(match.get('teamA', [])),
                json.dumps(match.get('teamB', [])),
                score_a[0] if len(score_a) > 0 else 0,
                score_a[1] if len(score_a) > 1 else 0,
                score_b[0] if len(score_b) > 0 else 0,
                score_b[1] if len(score_b) > 1 else 0,
                match.get('status', 'pending')
            ))
    
    conn.commit()
    cursor.close()
    conn.close()
    return {"success": True, "data": {"id": event_id}}


def get_event(event_id: str):
    """获取活动详情"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT id, name, court_count, created_at, updated_at FROM events WHERE id = %s", (event_id,))
    event = cursor.fetchone()
    
    if not event:
        cursor.close()
        conn.close()
        return {"success": False, "error": "活动不存在"}
    
    cursor.execute("""
        SELECT id, round, court, type, 
               JSON_EXTRACT(team_a, '$') as teamA,
               JSON_EXTRACT(team_b, '$') as teamB,
               score_a1, score_a2, score_b1, score_b2,
               status, created_at, updated_at
        FROM matches WHERE event_id = %s ORDER BY court, round
    """, (event_id,))
    
    matches = []
    for row in cursor.fetchall():
        matches.append({
            'id': row['id'],
            'round': row['round'],
            'court': row['court'],
            'type': row['type'],
            'teamA': json.loads(row['teamA']) if row['teamA'] else [],
            'teamB': json.loads(row['teamB']) if row['teamB'] else [],
            'scoreA': [row['score_a1'] or 0, row['score_a2'] or 0],
            'scoreB': [row['score_b1'] or 0, row['score_b2'] or 0],
            'status': row['status'] or 'pending',
        })
    
    cursor.close()
    conn.close()
    
    event['matches'] = matches
    return {"success": True, "data": event}


def update_event(event_id: str, data: dict):
    """更新活动"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if 'name' in data:
        cursor.execute("UPDATE events SET name = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s", (data['name'], event_id))
    if 'court_count' in data:
        cursor.execute("UPDATE events SET court_count = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s", (data['court_count'], event_id))
    if 'matches' in data:
        cursor.execute("DELETE FROM matches WHERE event_id = %s", (event_id,))
        for match in data['matches']:
            score_a = match.get('scoreA', [0, 0])
            score_b = match.get('scoreB', [0, 0])
            match_id = match.get('id') or str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO matches 
                (id, event_id, round, court, type, team_a, team_b, score_a1, score_a2, score_b1, score_b2, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                match_id, event_id, match.get('round', 1), match.get('court', 1),
                match.get('type', ''), json.dumps(match.get('teamA', [])),
                json.dumps(match.get('teamB', [])),
                score_a[0], score_a[1], score_b[0], score_b[1],
                match.get('status', 'pending')
            ))
    
    conn.commit()
    cursor.close()
    conn.close()
    return {"success": True}


def delete_event(event_id: str):
    """删除活动"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM matches WHERE event_id = %s", (event_id,))
    cursor.execute("DELETE FROM events WHERE id = %s", (event_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return {"success": True}


def get_matches(event_id: str):
    """获取比赛列表"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT id, round, court, type, 
               JSON_EXTRACT(team_a, '$') as teamA,
               JSON_EXTRACT(team_b, '$') as teamB,
               score_a1, score_a2, score_b1, score_b2,
               status
        FROM matches WHERE event_id = %s ORDER BY court, round
    """, (event_id,))
    
    matches = []
    for row in cursor.fetchall():
        matches.append({
            'id': row['id'],
            'round': row['round'],
            'court': row['court'],
            'type': row['type'],
            'teamA': json.loads(row['teamA']) if row['teamA'] else [],
            'teamB': json.loads(row['teamB']) if row['teamB'] else [],
            'scoreA': [row['score_a1'] or 0, row['score_a2'] or 0],
            'scoreB': [row['score_b1'] or 0, row['score_b2'] or 0],
            'status': row['status'] or 'pending',
        })
    
    cursor.close()
    conn.close()
    return {"success": True, "data": matches}


def update_match(match_id: str, data: dict):
    """更新比赛比分"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    score_a = data.get('scoreA', [0, 0])
    score_b = data.get('scoreB', [0, 0])
    status = data.get('status', 'pending')
    
    cursor.execute("""
        UPDATE matches 
        SET score_a1 = %s, score_a2 = %s, score_b1 = %s, score_b2 = %s,
            status = %s, updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
    """, (score_a[0], score_a[1], score_b[0], score_b[1], status, match_id))
    
    conn.commit()
    cursor.close()
    conn.close()
    return {"success": True, "data": {"updated_at": datetime.now().isoformat()}}


def get_stats(event_id: str):
    """获取球员统计数据"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT team_a, team_b, score_a1, score_a2, score_b1, score_b2, type
        FROM matches WHERE event_id = %s AND status = 'finished'
    """, (event_id,))
    
    matches = cursor.fetchall()
    cursor.close()
    conn.close()
    
    player_stats = {}
    for match in matches:
        team_a = json.loads(match['team_a']) if match['team_a'] else []
        team_b = json.loads(match['team_b']) if match['team_b'] else []
        score_a_total = (match['score_a1'] or 0) + (match['score_a2'] or 0)
        score_b_total = (match['score_b1'] or 0) + (match['score_b2'] or 0)
        team_a_won = score_a_total > score_b_total
        
        for player in team_a:
            if player not in player_stats:
                player_stats[player] = {'total': 0, '男双': 0, '女双': 0, '混双': 0, 'wins': 0}
            player_stats[player]['total'] += 1
            player_stats[player][match['type']] += 1
            if team_a_won:
                player_stats[player]['wins'] += 1
        
        for player in team_b:
            if player not in player_stats:
                player_stats[player] = {'total': 0, '男双': 0, '女双': 0, '混双': 0, 'wins': 0}
            player_stats[player]['total'] += 1
            player_stats[player][match['type']] += 1
            if not team_a_won:
                player_stats[player]['wins'] += 1
    
    return {"success": True, "data": player_stats}
