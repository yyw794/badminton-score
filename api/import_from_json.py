#!/usr/bin/env python3
"""
从 data.json 导入活动数据到 TiDB 数据库
用于初始化活动数据
"""

import json
import sys
import os
import mysql.connector
from datetime import datetime
import uuid

# TiDB 配置
DB_CONFIG = {
    'host': 'gateway01.ap-southeast-1.prod.aws.tidbcloud.com',
    'port': 4000,
    'user': '8AXKPCJGEHG5Qqv.root',
    'password': '7iv93aerRyGckxqw',
    'database': 'test',
    'ssl_ca': '/etc/ssl/cert.pem',
    'ssl_verify_cert': True,
}


def get_db_connection():
    """获取数据库连接"""
    return mysql.connector.connect(**DB_CONFIG)


def init_db():
    """初始化数据库表"""
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
    print("✓ 数据库表初始化完成")


def import_from_json(json_path: str):
    """从 JSON 文件导入数据"""
    
    # 读取 JSON 文件
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    event_name = data.get('eventName', '未命名活动')
    court_count = data.get('courtCount', 3)
    matches = data.get('matches', [])
    
    print(f"活动名称：{event_name}")
    print(f"场地数：{court_count}")
    print(f"比赛数：{len(matches)}")
    
    # 初始化数据库
    init_db()
    
    # 生成活动 ID
    event_id = str(uuid.uuid4())
    print(f"\n生成活动 ID: {event_id}")
    
    # 保存活动
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO events (id, name, court_count)
        VALUES (%s, %s, %s)
    """, (event_id, event_name, court_count))
    
    # 保存比赛
    for match in matches:
        score_a = match.get('scoreA', [0, 0])
        score_b = match.get('scoreB', [0, 0])
        
        cursor.execute("""
            INSERT INTO matches 
            (id, event_id, round, court, type, team_a, team_b, score_a1, score_a2, score_b1, score_b2, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            match.get('id', str(uuid.uuid4())),
            event_id,
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
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print("\n✓ 数据导入成功！")
    print(f"\n请保存以下配置到 docs/app.js:")
    print(f"  const API_BASE_URL = 'https://your-api-url.fc.aliyuncs.com';")
    print(f"  const EVENT_ID = '{event_id}';")
    print(f"  const ENABLE_CLOUD_SYNC = true;")
    
    return event_id


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法：python import_from_json.py <json 文件路径>")
        print("示例：python import_from_json.py ../docs/data.json")
        sys.exit(1)
    
    json_path = sys.argv[1]
    if not os.path.exists(json_path):
        print(f"错误：文件不存在 - {json_path}")
        sys.exit(1)
    
    import_from_json(json_path)
