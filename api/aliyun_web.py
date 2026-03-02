# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
阿里云函数计算 Web 函数 - 羽毛球比赛计分 API
使用 Flask 作为 HTTP 服务器
"""

import json
import os
import mysql.connector
from datetime import datetime
import uuid
from flask import Flask, request, jsonify

app = Flask(__name__)

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


# ==================== API 路由 ====================

@app.route('/init', methods=['GET'])
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
    return jsonify({"success": True, "message": "数据库表初始化完成"})


@app.route('/events', methods=['GET'])
def get_events():
    """获取活动列表"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, name, court_count, created_at, updated_at FROM events ORDER BY created_at DESC")
    events = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify({"success": True, "data": events})


@app.route('/events', methods=['POST'])
def create_event():
    """创建活动"""
    data = request.get_json() or {}
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
    return jsonify({"success": True, "data": {"id": event_id}})


@app.route('/events/<event_id>', methods=['GET'])
def get_event(event_id):
    """获取活动详情"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT id, name, court_count, created_at, updated_at FROM events WHERE id = %s", (event_id,))
    event = cursor.fetchone()
    
    if not event:
        cursor.close()
        conn.close()
        return jsonify({"success": False, "error": "活动不存在"})
    
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
    return jsonify({"success": True, "data": event})


@app.route('/events/<event_id>', methods=['PUT'])
def update_event(event_id):
    """更新活动"""
    data = request.get_json() or {}
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
    return jsonify({"success": True})


@app.route('/events/<event_id>', methods=['DELETE'])
def delete_event(event_id):
    """删除活动"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM matches WHERE event_id = %s", (event_id,))
    cursor.execute("DELETE FROM events WHERE id = %s", (event_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"success": True})


@app.route('/events/<event_id>/matches', methods=['GET'])
def get_matches(event_id):
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
    return jsonify({"success": True, "data": matches})


@app.route('/matches/<match_id>', methods=['PUT'])
def update_match(match_id):
    """更新比赛比分"""
    data = request.get_json() or {}
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
    return jsonify({"success": True, "data": {"updated_at": datetime.now().isoformat()}})


@app.route('/stats/<event_id>', methods=['GET'])
def get_stats(event_id):
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
    
    return jsonify({"success": True, "data": player_stats})


@app.route('/', methods=['GET'])
def index():
    """首页"""
    return jsonify({"success": True, "message": "羽毛球计分 API 运行中"})


@app.after_request
def after_request(response):
    """添加 CORS 头"""
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    return response


if __name__ == '__main__':
    # 阿里云函数计算 Web 函数启动命令
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
