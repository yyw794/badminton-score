#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
解析老格式比分图片脚本（2026-06-01 等）

老格式特点：
- 16 局比赛，每局 3 个场地并行
- 每场地 1 场比赛，每场只记 1 个比分（不是 2 局制）
- 表格布局：局数 | 队员 A1 | 队员 A2 | 比分 | 队员 B1 | 队员 B2

使用方式：
  python3 scores/parse_old_format.py

解析步骤：
  1. 先用 paddleocr_vl.py 生成 OCR 结果
  2. 手动修正 OCR 错误（比分、队员名字）
  3. 运行本脚本生成 match_data.json
"""
import json
from collections import defaultdict

# 选手名字列表（用于识别性别）
FEMALE_NAMES = {"唐英武", "李杏芝", "项小英", "李祺祺", "罗琴荩"}


def get_match_type(a_team, b_team):
    """判断比赛类型"""
    team_a_count = len(a_team)
    team_b_count = len(b_team)

    if team_a_count == 1 and team_b_count == 1:
        return "单打"

    # 判断是否混双
    is_mixed = any(p in FEMALE_NAMES for p in a_team + b_team)
    if is_mixed:
        return "混双"
    return "男双"


def parse_and_save(date_str, matches_by_court, description="比赛"):
    """
    解析并保存比赛数据

    Args:
        date_str: 比赛日期，如 "20260601"
        description: 比赛描述
        matches_by_court: dict, key 为场地号 (1,2,3), value 为比赛列表
            每场比赛格式：
            {
                "game": int,  # 局数
                "a": list,     # 队员 A（列表）
                "score": str,  # 比分（如 "15:8"）
                "b": list      # 队员 B（列表）
            }
    """
    all_matches = []

    for court, matches in matches_by_court.items():
        for match in matches:
            score = match["score"]
            if score is None:
                continue

            a_team = match["a"]
            b_team = match["b"]

            all_matches.append({
                "game": match["game"],
                "court": court,
                "type": get_match_type(a_team, b_team),
                "team_a": a_team,
                "team_b": b_team,
                "score": score
            })

    # 按局数和场地排序
    all_matches.sort(key=lambda x: (x["game"], x["court"]))

    result = {
        "match_date": f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}",
        "description": description,
        "format": "15分制，每局1个比分",
        "matches": all_matches
    }

    # 保存到对应目录
    output_path = f"scores/{date_str}/match_data_old_format_parsed.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"已解析 {len(all_matches)} 场比赛")
    print(f"结果已保存到 {output_path}")

    # 打印详细数据
    print("\n" + "=" * 60)
    print("比赛详情:")
    print("=" * 60)
    for match in all_matches:
        a_str = " / ".join(match["team_a"])
        b_str = " / ".join(match["team_b"])
        print(f"第{match['game']}局 场地{match['court']} [{match['type']}] {a_str} vs {b_str} {match['score']}")

    # 统计
    print("\n" + "=" * 60)
    print("选手统计:")
    print("=" * 60)

    wins = defaultdict(int)
    losses = defaultdict(int)
    total_games = defaultdict(int)

    for match in all_matches:
        score = match["score"].split(":")
        if len(score) != 2:
            continue
        score_a, score_b = int(score[0]), int(score[1])

        for player in match["team_a"]:
            total_games[player] += 1
        for player in match["team_b"]:
            total_games[player] += 1

        if score_a > score_b:
            for player in match["team_a"]:
                wins[player] += 1
            for player in match["team_b"]:
                losses[player] += 1
        else:
            for player in match["team_b"]:
                wins[player] += 1
            for player in match["team_a"]:
                losses[player] += 1

    # 按胜率排序
    player_stats = []
    for player in total_games:
        win = wins.get(player, 0)
        loss = losses.get(player, 0)
        rate = win / total_games[player] if total_games[player] > 0 else 0
        player_stats.append((player, win, loss, total_games[player], rate))

    player_stats.sort(key=lambda x: (-x[4], -x[1]))

    print(f"{'排名':<5}{'选手':<10}{'胜':<5}{'负':<5}{'总局数':<8}{'胜率':<10}")
    print("-" * 50)
    for i, (name, win, loss, total, rate) in enumerate(player_stats, 1):
        print(f"{i:<5}{name:<10}{win:<5}{loss:<5}{total:<8}{rate:.1%}")


if __name__ == "__main__":
    # ========== 示例：2026-06-01 比赛数据 ==========
    # 在这里填入修正后的数据
    # 每场比赛格式：{"game": 局数, "a": [队员 A], "score": "比分", "b": [队员 B]}

    court1_data = [
        {"game": 1, "a": ["陈小洪", "卢志辉"], "score": "11:15", "b": ["罗蒙", "罗琴荩"]},
        {"game": 2, "a": ["陈小洪", "卢志辉"], "score": "10:15", "b": ["罗蒙", "罗琴荩"]},
        {"game": 3, "a": ["李祺祺", "唐英武"], "score": "5:15", "b": ["李杏芝", "项小英"]},
        {"game": 4, "a": ["李祺祺", "唐英武"], "score": "10:15", "b": ["李杏芝", "项小英"]},
        {"game": 5, "a": ["程建兴", "罗蒙"], "score": "15:7", "b": ["罗琴荩", "王小波"]},
        {"game": 6, "a": ["程建兴", "罗蒙"], "score": "15:8", "b": ["罗琴荩", "王小波"]},
        {"game": 7, "a": ["陈顺星", "李杏芝"], "score": "11:15", "b": ["罗琴荩", "李祺祺"]},
        {"game": 8, "a": ["陈顺星", "李杏芝"], "score": "14:15", "b": ["罗琴荩", "李祺祺"]},
        {"game": 9, "a": ["陈顺星"], "score": "14:15", "b": ["罗琴荩"]},
        {"game": 10, "a": ["陈顺星"], "score": "14:15", "b": ["罗琴荩"]},
        {"game": 11, "a": ["陈小洪", "罗琴荩"], "score": "8:15", "b": ["卢志辉", "苏大哲"]},
        {"game": 12, "a": ["陈小洪", "罗琴荩"], "score": "15:10", "b": ["卢志辉", "苏大哲"]},
        {"game": 13, "a": ["陈小洪", "卢志辉"], "score": "11:15", "b": ["刘继宇", "严勇文"]},
        {"game": 14, "a": ["陈小洪", "卢志辉"], "score": "9:15", "b": ["刘继宇", "严勇文"]},
        {"game": 15, "a": ["程建兴"], "score": "14:15", "b": ["罗琴荩"]},
        {"game": 16, "a": ["程建兴"], "score": "15:11", "b": ["罗琴荩"]},
    ]

    court2_data = [
        {"game": 1, "a": ["王小波", "唐英武"], "score": "15:8", "b": ["程建兴", "李杏芝"]},
        {"game": 2, "a": ["王小波", "唐英武"], "score": "15:9", "b": ["程建兴", "李杏芝"]},
        {"game": 3, "a": ["刘继宇", "苏大哲"], "score": "15:8", "b": ["卢志辉", "严勇文"]},
        {"game": 4, "a": ["刘继宇", "苏大哲"], "score": "15:9", "b": ["卢志辉", "严勇文"]},
        {"game": 5, "a": ["李祺祺", "唐英武"], "score": "14:15", "b": ["李杏芝", "项小英"]},
        {"game": 6, "a": ["李祺祺", "唐英武"], "score": "9:15", "b": ["李杏芝", "项小英"]},
        {"game": 7, "a": ["刘继宇", "严勇文"], "score": "15:11", "b": ["陈小洪", "苏大哲"]},
        {"game": 8, "a": ["刘继宇", "严勇文"], "score": "15:9", "b": ["陈小洪", "苏大哲"]},
        {"game": 9, "a": ["卢志辉", "项小英"], "score": "15:10", "b": ["王小波", "唐英武"]},
        {"game": 10, "a": ["卢志辉", "项小英"], "score": "15:10", "b": ["王小波", "唐英武"]},
        {"game": 11, "a": ["王小波", "李祺祺"], "score": "13:15", "b": ["陈顺星", "李杏芝"]},
        {"game": 12, "a": ["王小波", "李祺祺"], "score": "13:15", "b": ["陈顺星", "李杏芝"]},
        {"game": 13, "a": ["程建兴"], "score": "15:12", "b": ["陈顺星"]},
        {"game": 14, "a": ["程建兴"], "score": "12:15", "b": ["陈顺星"]},
        {"game": 15, "a": ["陈小洪", "卢志辉"], "score": "11:15", "b": ["苏大哲", "严勇文"]},
        {"game": 16, "a": ["陈小洪", "卢志辉"], "score": "14:15", "b": ["苏大哲", "严勇文"]},
    ]

    court3_data = [
        {"game": 1, "a": ["苏大哲", "项小英"], "score": "15:11", "b": ["陈顺星", "李祺祺"]},
        {"game": 2, "a": ["苏大哲", "项小英"], "score": "15:9", "b": ["陈顺星", "李祺祺"]},
        {"game": 3, "a": ["陈顺星", "陈小洪"], "score": "10:15", "b": ["程建兴", "罗蒙"]},
        {"game": 4, "a": ["陈顺星", "陈小洪"], "score": "8:15", "b": ["程建兴", "罗蒙"]},
        {"game": 5, "a": ["刘继宇", "严勇文"], "score": "13:15", "b": ["卢志辉", "苏大哲"]},
        {"game": 6, "a": ["刘继宇", "严勇文"], "score": "15:14", "b": ["卢志辉", "苏大哲"]},
        {"game": 7, "a": ["王小波", "唐英武"], "score": "15:13", "b": ["程建兴", "项小英"]},
        {"game": 8, "a": ["王小波", "唐英武"], "score": "13:15", "b": ["程建兴", "项小英"]},
        {"game": 9, "a": ["刘继宇", "苏大哲"], "score": "15:8", "b": ["陈小洪", "严勇文"]},
        {"game": 10, "a": ["刘继宇", "苏大哲"], "score": "15:7", "b": ["陈小洪", "严勇文"]},
        {"game": 11, "a": ["程建兴", "罗蒙"], "score": "15:14", "b": ["刘继宇", "严勇文"]},
        {"game": 12, "a": ["程建兴", "罗蒙"], "score": "15:11", "b": ["刘继宇", "严勇文"]},
        {"game": 13, "a": ["王小波", "唐英武"], "score": "15:7", "b": ["罗蒙", "李祺祺"]},
        {"game": 14, "a": ["王小波", "唐英武"], "score": "15:14", "b": ["罗蒙", "李祺祺"]},
        {"game": 15, "a": ["陈顺星", "刘继宇"], "score": "15:13", "b": ["罗蒙", "王小波"]},
        {"game": 16, "a": ["陈顺星", "刘继宇"], "score": "15:12", "b": ["罗蒙", "王小波"]},
    ]

    # 运行解析
    parse_and_save(
        date_str="20260601",
        matches_by_court={
            1: court1_data,
            2: court2_data,
            3: court3_data,
        },
        description="科技球队日常训练活动"
    )
