#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统计2026年上半年球员出勤率
"""

import json
from collections import defaultdict
from datetime import datetime

def load_match_data(file_path):
    """加载比赛数据"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def extract_players_from_match(match):
    """从一场比赛中提取所有球员"""
    players = set()
    if 'team_a' in match:
        players.update(match['team_a'])
    if 'team_b' in match:
        players.update(match['team_b'])
    
    # 名字修正映射（OCR识别错误修正）
    name_corrections = {
        '罗琴苡': '罗琴荩',  # OCR错误识别
        '江俊': '江锐',      # 可能是OCR错误识别
        '江镜': '江锐',      # 可能是OCR错误识别
    }
    
    # 应用名字修正
    corrected_players = set()
    for player in players:
        corrected_players.add(name_corrections.get(player, player))
    
    return corrected_players

def analyze_attendance():
    """分析出勤情况"""
    # 2026年上半年的比赛文件
    match_files = [
        'scores/20260413/match_data.json',
        'scores/20260601/match_data_old_format_parsed.json',
        'scores/20260608/match_data.json',
        'scores/20260615/match_data.json',
        'scores/20260622/match_data.json',
    ]
    
    # 添加history文件夹里的数据
    import glob
    history_files = glob.glob('scores/history/match_data_output*.json')
    match_files.extend(history_files)
    
    # 统计每个球员出现在多少个JSON文件中（参加了多少次活动）
    player_activity_count = defaultdict(int)
    total_activities = len(match_files)
    
    for file_path in match_files:
        try:
            data = load_match_data(file_path)
            
            # 提取本次活动中所有出现的球员
            players_in_this_activity = set()
            for match in data.get('matches', []):
                players = extract_players_from_match(match)
                players_in_this_activity.update(players)
            
            # 为每个出现在本次活动中的球员计数
            for player in players_in_this_activity:
                player_activity_count[player] += 1
                    
        except Exception as e:
            print(f"读取文件 {file_path} 出错: {e}")
    
    # 按参加活动次数排序
    sorted_players = sorted(
        player_activity_count.items(),
        key=lambda x: x[1],
        reverse=True
    )
    
    print(f"\n{'='*60}")
    print(f"2026年上半年羽毛球活动出勤统计")
    print(f"{'='*60}")
    print(f"统计维度：参加活动次数（每个JSON文件为一次活动）")
    print(f"总活动次数: {total_activities} 次")
    print(f"{'='*60}\n")
    
    print(f"{'排名':<6}{'姓名':<12}{'参加次数':<12}{'出勤率':<10}")
    print(f"{'-'*60}")
    
    for rank, (player, activity_count) in enumerate(sorted_players, 1):
        attendance_rate = (activity_count / total_activities) * 100
        print(f"{rank:<6}{player:<12}{activity_count:<12}{attendance_rate:.1f}%")
    
    print(f"\n{'='*60}")
    print(f"统计完成！共 {len(sorted_players)} 位球员参加活动")
    print(f"{'='*60}\n")

if __name__ == '__main__':
    analyze_attendance()