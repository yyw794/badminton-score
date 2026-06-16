#!/usr/bin/env python3
"""验证 PaddleOCR 解析结果，检查比分逻辑和选手名字"""
import argparse
import json
import os
import re
import sys
from html.parser import HTMLParser


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

# 选手名单
KNOWN_PLAYERS = {
    "苏大哲", "罗蒙", "江锐", "严勇文", "陈顺星", "陈小洪", "卢志辉",
    "林锋", "王小波", "刘继宇", "董广博", "林琪琛", "罗琴荩",
    "田茜", "唐英武", "李祺祺", "高洁", "滕菲", "谢卓珊", "崔倩男", "林小连",
    "张欣欣", "黄冬青", "程建兴", "陈宇霆", "卢子龙", "吴煜",
    "张燕红", "李杏芝", "项小英",
}

NAME_CORRECTIONS = {
    "李棋棋": "李祺祺",
    "陈小兵": "陈小洪",
}


class TableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.matches = []
        self.current_match = None
        self.current_row = False
        self.current_cell = False
        self.cell_text = ""
        self.cell_index = 0
    
    def handle_starttag(self, tag, attrs):
        if tag == 'tr':
            self.current_row = True
            self.cell_index = 0
            self.current_match = {}
        elif tag == 'td' and self.current_row:
            self.current_cell = True
            self.cell_text = ""
            attrs_dict = dict(attrs)
            colspan = int(attrs_dict.get('colspan', 1))
            if colspan > 1:
                self.cell_index += colspan
                self.current_cell = False
    
    def handle_data(self, data):
        if self.current_cell:
            self.cell_text += data.strip()
    
    def handle_endtag(self, tag):
        if tag == 'td' and self.current_row and self.current_cell:
            if self.cell_index == 0:
                try:
                    self.current_match['round'] = int(self.cell_text)
                except ValueError:
                    pass
            elif self.cell_index == 1:
                match = re.search(r'(\d+)', self.cell_text)
                if match:
                    self.current_match['court'] = int(match.group(1))
            elif self.cell_index == 2:
                self.current_match['type'] = self.cell_text
            elif self.cell_index == 3:
                self.current_match['team_a'] = self.cell_text
            elif self.cell_index == 4:
                self.current_match['score_a'] = self.cell_text
            elif self.cell_index == 5:
                self.current_match['score_b'] = self.cell_text
            elif self.cell_index == 6:
                self.current_match['team_b'] = self.cell_text
            self.current_cell = False
            self.cell_index += 1
        elif tag == 'tr' and self.current_row:
            if 'round' in self.current_match and 'score_a' in self.current_match:
                self.matches.append(self.current_match)
            self.current_row = False
            self.current_match = None


def parse_players(team_str):
    return [p.strip() for p in team_str.split('/') if p.strip()]


def check_score(score_str):
    if not score_str:
        return None, None, False, "比分为空"
    
    match = re.match(r'(\d+):(\d+)', score_str)
    if not match:
        return None, None, False, f"比分格式错误: {score_str}"
    
    a, b = int(match.group(1)), int(match.group(2))
    
    if a < 15 and b < 15:
        return a, b, False, f"双方都未达到 15 分: {score_str}"
    if a == 15 and b > 15:
        return a, b, False, f"对阵 A 达到 15 分但比分少于对方: {score_str}"
    if b == 15 and a > 15:
        return a, b, False, f"对阵 B 达到 15 分但比分少于对方: {score_str}"
    
    return a, b, True, None


def find_md_file(md_path):
    """Find doc_0.md relative to scores directory or current directory"""
    scores_dir = find_scores_dir()
    
    # If absolute path, return as-is
    if os.path.isabs(md_path):
        return md_path if os.path.exists(md_path) else None
    
    # Try relative to scores dir
    if scores_dir:
        full_path = os.path.join(scores_dir, md_path)
        if os.path.exists(full_path):
            return full_path
        # Try without leading scores/
        if md_path.startswith("scores/"):
            md_path = md_path[7:]
        full_path = os.path.join(scores_dir, md_path)
        if os.path.exists(full_path):
            return full_path
    
    # Try relative to current directory
    if os.path.exists(md_path):
        return os.path.abspath(md_path)
    
    # Try looking for doc_0.md in the same directory as md_path
    parent = os.path.dirname(md_path)
    if parent and os.path.exists(os.path.join(parent, "doc_0.md")):
        return os.path.join(parent, "doc_0.md")
    
    # Try default location
    if scores_dir:
        for d in os.listdir(scores_dir):
            if d.startswith("output_") and os.path.exists(os.path.join(scores_dir, d, "doc_0.md")):
                return os.path.join(scores_dir, d, "doc_0.md")
    
    return None


def verify_ocr(md_path):
    resolved_path = find_md_file(md_path)
    if not resolved_path or not os.path.exists(resolved_path):
        print(f"错误：未找到 {md_path}")
        print(f"用法: python3 verify_ocr.py <doc_0.md路径或output_目录名>")
        print(f"  例如: python3 verify_ocr.py output_20260622/doc_0.md")
        print(f"        python3 verify_ocr.py 20260622")
        sys.exit(1)
    
    with open(resolved_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    parser = TableParser()
    parser.feed(content)
    
    if not parser.matches:
        print("错误：未解析到比赛数据")
        sys.exit(1)
    
    print("=" * 60)
    print(f"OCR 解析结果验证")
    print(f"共解析到 {len(parser.matches)} 场比赛")
    print("=" * 60)
    
    warnings = []
    errors = []
    
    for match in parser.matches:
        round_num = match.get('round', '?')
        court = match.get('court', '?')
        
        for score_key, label in [('score_a', '第1局'), ('score_b', '第2局')]:
            score_str = match.get(score_key, '')
            if not score_str:
                continue
            
            score_a, score_b, valid, error = check_score(score_str)
            if not valid:
                issue = f"R{round_num}C{court} {label}: {score_str} - {error}"
                if "都未达到" in error or "比分少于对方" in error:
                    warnings.append(issue)
                else:
                    errors.append(issue)
        
        for team_key, label in [('team_a', '对阵A'), ('team_b', '对阵B')]:
            team_str = match.get(team_key, '')
            if not team_str:
                continue
            
            players = parse_players(team_str)
            for player in players:
                if player in NAME_CORRECTIONS:
                    warnings.append(f"R{round_num}C{court} {label}: '{player}' 应纠正为 '{NAME_CORRECTIONS[player]}'")
                elif player not in KNOWN_PLAYERS and len(player) > 0:
                    warnings.append(f"R{round_num}C{court} {label}: 选手 '{player}' 不在已知名单中")
    
    print(f"\n解析比赛: {len(parser.matches)} 场")
    
    if warnings:
        print(f"\n⚠️  发现 {len(warnings)} 处需要确认:")
        for w in warnings:
            print(f"  - {w}")
    
    if errors:
        print(f"\n❌ 发现 {len(errors)} 处明显错误:")
        for e in errors:
            print(f"  - {e}")
    
    if not warnings and not errors:
        print(f"\n✅ 全部 {len(parser.matches)} 场比赛验证通过，无需确认")
    
    print("\n" + "=" * 60)
    return len(warnings) > 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="验证 PaddleOCR 解析结果")
    parser.add_argument("md_path", help="doc_0.md 路径 (例如: output_20260622/doc_0.md)")
    args = parser.parse_args()
    
    verify_ocr(args.md_path)
