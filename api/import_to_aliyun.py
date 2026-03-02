#!/usr/bin/env python3
"""
导入 data.json 数据到阿里云函数计算 API
"""

import json
import urllib.request
import urllib.error

# API 地址
API_BASE = 'https://badminton-api-mafqsjtcjp.cn-hangzhou.fcapp.run'

# 读取 data.json
with open('docs/data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

event_name = data.get('eventName', '羽毛球活动')
court_count = data.get('courtCount', 3)
matches = data.get('matches', [])

print(f"活动名称：{event_name}")
print(f"场地数：{court_count}")
print(f"比赛数：{len(matches)}")

# 1. 初始化数据库
print("\n[1/3] 初始化数据库...")
try:
    req = urllib.request.Request(f'{API_BASE}/init')
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read().decode('utf-8'))
        print(f"      {result}")
except Exception as e:
    print(f"      失败：{e}")
    print("      提示：可能需要在浏览器中先访问一次 /init")

# 2. 创建活动
print("\n[2/3] 创建活动...")
event_data = {
    "name": event_name,
    "court_count": court_count,
    "matches": matches
}

try:
    data_bytes = json.dumps(event_data, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(f'{API_BASE}/events', data=data_bytes, method='POST')
    req.add_header('Content-Type', 'application/json')
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read().decode('utf-8'))
        if result.get('success'):
            event_id = result.get('data', {}).get('id')
            print(f"      活动已创建，ID: {event_id}")
            print(f"\n✅ 请保存以下配置到 docs/app.js:")
            print(f"   const EVENT_ID = '{event_id}';")
            print(f"   const ENABLE_CLOUD_SYNC = true;")
        else:
            print(f"      失败：{result}")
except Exception as e:
    print(f"      失败：{e}")

print("\n[3/3] 完成！")
