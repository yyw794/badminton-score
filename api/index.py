#!/usr/bin/env python3
"""
阿里云函数计算 FC - 羽毛球比赛计分 API
部署说明：https://help.aliyun.com/zh/functioncompute/
"""

import json
import os
import mysql.connector
from mysql.connector import Error
from datetime import datetime
from typing import Optional

# ==================== 数据库配置 ====================
# 从环境变量读取（阿里云函数计算控制台配置）
DB_CONFIG = {
    'host': os.environ.get('TIDB_HOST', 'gateway01.ap-southeast-1.prod.aws.tidbcloud.com'),
    'port': int(os.environ.get('TIDB_PORT', '4000')),
    'user': os.environ.get('TIDB_USER', '8AXKPCJGEHG5Qqv.root'),
    'password': os.environ.get('TIDB_PASSWORD', ''),
    'database': os.environ.get('TIDB_DATABASE', 'test'),
    'ssl_ca': os.environ.get('TIDB_SSL_CA', '/etc/ssl/cert.pem'),
    'ssl_verify_cert': True,
}


def get_db_connection():
    """获取数据库连接"""
    return mysql.connector.connect(**DB_CONFIG)


def init_db():
    """初始化数据库表结构"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 创建活动表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id VARCHAR(36) PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            court_count INT DEFAULT 3,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )
    """)
    
    # 创建比赛表
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


# ==================== API 处理函数 ====================

def handler(environ, start_response):
    """
    阿里云函数计算入口函数
    文档：https://help.aliyun.com/zh/functioncompute/developer-reference/python-function
    """
    context = environ.get('fc_context')
    
    # 获取请求路径和方法
    path = environ.get('PATH_INFO', '/')
    method = environ.get('REQUEST_METHOD', 'GET')
    
    # 读取请求体
    try:
        request_body_size = int(environ.get('CONTENT_LENGTH', 0))
    except (ValueError):
        request_body_size = 0
    
    if request_body_size > 0:
        request_body = environ['wsgi.input'].read(request_body_size)
        try:
            data = json.loads(request_body.decode('utf-8'))
        except:
            data = {}
    else:
        data = {}
    
    # 路由处理
    response = route_request(path, method, data)
    
    # 返回响应
    status = '200 OK'
    headers = [
        ('Content-Type', 'application/json'),
        ('Access-Control-Allow-Origin', '*'),
        ('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS'),
        ('Access-Control-Allow-Headers', 'Content-Type'),
    ]
    
    start_response(status, headers)
    return [json.dumps(response, ensure_ascii=False).encode('utf-8')]


def route_request(path: str, method: str, data: dict):
    """路由请求到对应处理函数"""
    
    # 解析路径参数
    path_parts = [p for p in path.split('/') if p]
    
    # OPTIONS 预检请求
    if method == 'OPTIONS':
        return {"success": True}
    
    # ==================== 路由规则 ====================
    
    # GET /init - 初始化数据库
    if path == '/init' and method == 'GET':
        return init_db()
    
    # GET /events - 获取活动列表
    if path == '/events' and method == 'GET':
        return get_events()
    
    # POST /events - 创建活动
    if path == '/events' and method == 'POST':
        return create_event(data)
    
    # GET /events/{id} - 获取活动详情（包含比赛列表）
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
    
    # 未找到路由
    return {"success": False, "error": "Not Found", "path": path, "method": method}


# ==================== 业务逻辑 ====================

def generate_id():
    """生成唯一 ID"""
    import uuid
    return str(uuid.uuid4())


def get_events():
    """获取活动列表"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT id, name, court_count, created_at, updated_at 
        FROM events 
        ORDER BY created_at DESC
    """)
    
    events = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return {"success": True, "data": events}


def create_event(data: dict):
    """创建活动"""
    event_id = generate_id()
    name = data.get('name', '未命名活动')
    court_count = data.get('court_count', 3)
    matches = data.get('matches', [])
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 创建活动
    cursor.execute("""
        INSERT INTO events (id, name, court_count)
        VALUES (%s, %s, %s)
    """, (event_id, name, court_count))
    
    # 批量插入比赛
    if matches:
        insert_matches(cursor, event_id, matches)
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return {"success": True, "data": {"id": event_id}}


def get_event(event_id: str):
    """获取活动详情"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 获取活动信息
    cursor.execute("""
        SELECT id, name, court_count, created_at, updated_at 
        FROM events 
        WHERE id = %s
    """, (event_id,))
    
    event = cursor.fetchone()
    if not event:
        cursor.close()
        conn.close()
        return {"success": False, "error": "活动不存在"}
    
    # 获取比赛列表
    matches = get_matches_raw(cursor, event_id)
    
    cursor.close()
    conn.close()
    
    event['matches'] = matches
    return {"success": True, "data": event}


def update_event(event_id: str, data: dict):
    """更新活动"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 更新活动信息
    if 'name' in data:
        cursor.execute("""
            UPDATE events SET name = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (data['name'], event_id))
    
    if 'court_count' in data:
        cursor.execute("""
            UPDATE events SET court_count = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (data['court_count'], event_id))
    
    # 更新比赛列表
    if 'matches' in data:
        # 删除旧比赛
        cursor.execute("DELETE FROM matches WHERE event_id = %s", (event_id,))
        # 插入新比赛
        insert_matches(cursor, event_id, data['matches'])
    
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
    
    matches = get_matches_raw(cursor, event_id)
    
    cursor.close()
    conn.close()
    
    return {"success": True, "data": matches}


def get_matches_raw(cursor, event_id: str):
    """获取比赛列表（内部函数）"""
    cursor.execute("""
        SELECT id, round, court, type, 
               JSON_EXTRACT(team_a, '$') as teamA,
               JSON_EXTRACT(team_b, '$') as teamB,
               score_a1, score_a2, score_b1, score_b2,
               status, created_at, updated_at
        FROM matches
        WHERE event_id = %s
        ORDER BY court, round
    """, (event_id,))
    
    matches = []
    for row in cursor.fetchall():
        match = {
            'id': row['id'],
            'round': row['round'],
            'court': row['court'],
            'type': row['type'],
            'teamA': json.loads(row['teamA']) if row['teamA'] else [],
            'teamB': json.loads(row['teamB']) if row['teamB'] else [],
            'scoreA': [row['score_a1'] or 0, row['score_a2'] or 0],
            'scoreB': [row['score_b1'] or 0, row['score_b2'] or 0],
            'status': row['status'] or 'pending',
        }
        matches.append(match)
    
    return matches


def update_match(match_id: str, data: dict):
    """更新比赛比分"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 获取当前比赛数据
    cursor.execute("SELECT * FROM matches WHERE id = %s", (match_id,))
    match = cursor.fetchone()
    if not match:
        cursor.close()
        conn.close()
        return {"success": False, "error": "比赛不存在"}
    
    # 更新比分
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
    
    # 获取所有已完成的比赛
    cursor.execute("""
        SELECT team_a, team_b, score_a1, score_a2, score_b1, score_b2, type
        FROM matches
        WHERE event_id = %s AND status = 'finished'
    """, (event_id,))
    
    matches = cursor.fetchall()
    cursor.close()
    conn.close()
    
    # 统计每个球员的数据
    player_stats = {}
    
    for match in matches:
        team_a = json.loads(match['team_a']) if match['team_a'] else []
        team_b = json.loads(match['team_b']) if match['team_b'] else []
        
        score_a_total = (match['score_a1'] or 0) + (match['score_a2'] or 0)
        score_b_total = (match['score_b1'] or 0) + (match['score_b2'] or 0)
        
        team_a_won = score_a_total > score_b_total
        
        # 统计队伍 A
        for player in team_a:
            if player not in player_stats:
                player_stats[player] = {'total': 0, '男双': 0, '女双': 0, '混双': 0, 'wins': 0}
            player_stats[player]['total'] += 1
            player_stats[player][match['type']] += 1
            if team_a_won:
                player_stats[player]['wins'] += 1
        
        # 统计队伍 B
        for player in team_b:
            if player not in player_stats:
                player_stats[player] = {'total': 0, '男双': 0, '女双': 0, '混双': 0, 'wins': 0}
            player_stats[player]['total'] += 1
            player_stats[player][match['type']] += 1
            if not team_a_won:
                player_stats[player]['wins'] += 1
    
    return {"success": True, "data": player_stats}


def insert_matches(cursor, event_id: str, matches: list):
    """批量插入比赛记录"""
    for match in matches:
        match_id = match.get('id') or generate_id()
        score_a = match.get('scoreA', [0, 0])
        score_b = match.get('scoreB', [0, 0])
        
        cursor.execute("""
            INSERT INTO matches 
            (id, event_id, round, court, type, team_a, team_b, score_a1, score_a2, score_b1, score_b2, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            match_id, event_id,
            match.get('round', 1),
            match.get('court', 1),
            match.get('type', ''),
            json.dumps(match.get('teamA', [])),
            json.dumps(match.get('teamB', [])),
            score_a[0] if len(score_a) > 0 else 0,
            score_a[1] if len(score_a) > 1 else 0,
            score_b[0] if len(score_b) > 0 else 0,
            score_b[1] if len(score_b) > 1 else 0,
            match.get('status', 'pending')
        ))
