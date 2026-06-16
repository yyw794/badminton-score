#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
羽毛球比分统计程序
从 JSON 数据文件读取比分，自动计算统计数据
每局1个比分，15分制
"""

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

def load_match_data(file_path):
    """从 JSON 文件加载比赛数据"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data

def validate_score_format(score_str):
    """验证比分格式是否正确"""
    if not score_str or score_str.strip() == '':
        return True, "空比分"  # 空比分表示跳过
    
    if ':' not in score_str:
        return False, f"比分格式错误：'{score_str}'，应为 'A:B' 格式"
    
    parts = score_str.split(':')
    if len(parts) != 2:
        return False, f"比分格式错误：'{score_str}'，应只有一个冒号"
    
    try:
        score_a = int(parts[0])
        score_b = int(parts[1])
    except ValueError:
        return False, f"比分不是数字：'{score_str}'"
    
    if score_a < 0 or score_b < 0:
        return False, f"比分不能为负数：'{score_str}'"
    
    return True, None

def validate_all_data(matches):
    """验证所有比赛数据"""
    report = {
        "total_matches": len(matches),
        "errors": [],
        "warnings": [],
        "has_notes": [],
        "valid": True
    }
    
    for i, match in enumerate(matches):
        match_id = f"第{match['game']}局-场地{match['court']}"
        
        # 检查必填字段
        required_fields = ['game', 'court', 'type', 'team_a', 'team_b', 'score']
        for field in required_fields:
            if field not in match:
                report["errors"].append(f"{match_id}: 缺少必填字段 '{field}'")
                report["valid"] = False
        
        # 验证比分
        score = match.get('score', '')
        is_valid, error = validate_score_format(score)
        if error == "空比分":
            report["warnings"].append(f"{match_id}: 比分未记录，已跳过")
            matches[i]['skip'] = True
            continue
        
        if not is_valid:
            report["errors"].append(f"{match_id}: {error}")
            report["valid"] = False
    
    return report

def print_validation_report(report):
    """打印验证报告"""
    print("=" * 80)
    print("数据验证报告")
    print("=" * 80)
    
    print(f"\n总比赛场次: {report['total_matches']}")
    
    if report['errors']:
        print(f"\n❌ 错误 ({len(report['errors'])}个):")
        for error in report['errors']:
            print(f"  - {error}")
    
    if report['warnings']:
        print(f"\n⚠️  警告 ({len(report['warnings'])}个):")
        for warning in report['warnings']:
            print(f"  - {warning}")
    
    if report['has_notes']:
        print(f"\n📝 需要确认的备注 ({len(report['has_notes'])}个):")
        for note in report['has_notes']:
            print(f"  - {note['match_id']}: {note['notes']}")
    
    if report['valid']:
        print("\n✅ 数据验证通过！")
    else:
        print("\n❌ 数据验证失败，请修正错误后重新运行")
    
    print("=" * 80)

def parse_score(score_str):
    """解析比分字符串"""
    parts = score_str.split(':')
    return int(parts[0]), int(parts[1])

def determine_winner(score_str):
    """根据比分判断哪方获胜"""
    score_a, score_b = parse_score(score_str)
    return "A" if score_a > score_b else "B"

def calculate_statistics(matches):
    """计算统计数据"""
    player_stats = defaultdict(lambda: {"wins": 0, "losses": 0})
    
    stats_by_type = {
        "男双": defaultdict(lambda: {"wins": 0, "losses": 0}),
        "女双": defaultdict(lambda: {"wins": 0, "losses": 0}),
        "混双": defaultdict(lambda: {"wins": 0, "losses": 0}),
        "单打": defaultdict(lambda: {"wins": 0, "losses": 0}),
    }
    
    for match in matches:
        if match.get('skip'):
            continue
        
        match_type = match["type"]
        team_a = match["team_a"]
        team_b = match["team_b"]
        score = match["score"]
        
        winner = determine_winner(score)
        
        # 统计这一局
        if winner == "A":
            for player in team_a:
                player_stats[player]["wins"] += 1
                stats_by_type[match_type][player]["wins"] += 1
            for player in team_b:
                player_stats[player]["losses"] += 1
                stats_by_type[match_type][player]["losses"] += 1
        else:
            for player in team_b:
                player_stats[player]["wins"] += 1
                stats_by_type[match_type][player]["wins"] += 1
            for player in team_a:
                player_stats[player]["losses"] += 1
                stats_by_type[match_type][player]["losses"] += 1
    
    return player_stats, stats_by_type

def format_rankings(rankings):
    """格式化排名表格"""
    lines = []
    lines.append("| 排名 | 球员 | 胜局数 | 负局数 | 总局数 | 胜率 |")
    lines.append("|------|------|--------|--------|--------|------|")
    
    current_rank = 1
    for i, r in enumerate(rankings):
        if i > 0 and r["win_rate"] == rankings[i-1]["win_rate"]:
            pass
        else:
            current_rank = i + 1
        
        lines.append(f"| {current_rank} | {r['player']} | {r['wins']} | {r['losses']} | {r['total']} | {r['win_rate']:.1f}% |")
    
    return "\n".join(lines)

def generate_report(player_stats, stats_by_type, validation_report):
    """生成 Markdown 报告"""
    lines = []
    
    lines.append("# 2026年06月01日 球员胜负统计排名")
    lines.append("")
    lines.append("> **数据来源**: 代码自动统计，确保准确性")
    lines.append(f"> **生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"> **数据验证**: {'✅ 通过' if validation_report['valid'] else '❌ 未通过'}")
    lines.append("")
    
    # 验证信息
    if validation_report['warnings']:
        lines.append("## ⚠️  数据警告")
        lines.append("")
        for warning in validation_report['warnings']:
            lines.append(f"- {warning}")
        lines.append("")
    
    # 统一排名
    lines.append("## 统一排名（按胜率从高到低）")
    lines.append("")
    
    rankings = []
    for player, stats in player_stats.items():
        total = stats["wins"] + stats["losses"]
        win_rate = stats["wins"] / total * 100 if total > 0 else 0
        rankings.append({
            "player": player,
            "wins": stats["wins"],
            "losses": stats["losses"],
            "total": total,
            "win_rate": win_rate
        })
    
    rankings.sort(key=lambda x: (-x["win_rate"], -x["wins"]))
    lines.append(format_rankings(rankings))
    lines.append("")
    
    # 按项目排名
    for match_type in ["男双", "女双", "混双", "单打"]:
        if not stats_by_type[match_type]:
            continue
        lines.append(f"### {match_type}胜率排名（按胜率从高到低）")
        lines.append("")
        
        type_rankings = []
        for player, stats in stats_by_type[match_type].items():
            total = stats["wins"] + stats["losses"]
            win_rate = stats["wins"] / total * 100 if total > 0 else 0
            type_rankings.append({
                "player": player,
                "wins": stats["wins"],
                "losses": stats["losses"],
                "total": total,
                "win_rate": win_rate
            })
        
        type_rankings.sort(key=lambda x: (-x["win_rate"], -x["wins"]))
        lines.append(format_rankings(type_rankings))
        lines.append("")
    
    # 统计说明
    lines.append("---")
    lines.append("")
    lines.append("## 统计说明")
    lines.append("")
    lines.append("- **比赛日期**: 2026年06月01日")
    lines.append("- **赛制**: 15分/局，每局1个比分")
    lines.append(f"- **总比赛场次**: {validation_report['total_matches']}场")
    lines.append(f"- **有效比赛场次**: {validation_report['total_matches'] - len([w for w in validation_report['warnings'] if '跳过' in w])}场")
    lines.append(f"- **参赛人数**: {len(player_stats)}人")
    lines.append("- **排名规则**: 按胜率从高到低排序，胜率相同者排名并列")
    lines.append("- **数据验证**: 已进行比分格式验证")
    lines.append("")
    lines.append("## 备注")
    lines.append("")
    lines.append("- 数据通过代码自动统计，避免人为错误")
    lines.append("- 如有疑问，请检查 match_data.json 中的原始数据")
    lines.append("")
    
    return "\n".join(lines)

def main():
    # 确定文件路径
    base_dir = Path(__file__).parent
    data_file = base_dir / "match_data.json"
    output_file = base_dir / "排名统计.md"
    
    print("开始处理...")
    print(f"数据文件: {data_file}")
    print()
    
    # 加载数据
    try:
        data = load_match_data(data_file)
        matches = data["matches"]
    except FileNotFoundError:
        print(f"❌ 错误：找不到数据文件 {data_file}")
        return
    except json.JSONDecodeError as e:
        print(f"❌ 错误：JSON 格式错误 {e}")
        return
    
    # 验证数据
    print("步骤 1/3: 验证数据...")
    validation_report = validate_all_data(matches)
    print_validation_report(validation_report)
    print()
    
    if not validation_report['valid']:
        print("❌ 数据验证失败，请修正后重新运行")
        return
    
    # 计算统计
    print("步骤 2/3: 计算统计数据...")
    player_stats, stats_by_type = calculate_statistics(matches)
    print(f"✅ 统计完成，共 {len(player_stats)} 名球员")
    print()
    
    # 生成报告
    print("步骤 3/3: 生成报告...")
    report = generate_report(player_stats, stats_by_type, validation_report)
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(report)
    
    print(f"✅ 报告已保存到: {output_file}")
    print()
    
    # 打印前5名
    rankings = []
    for player, stats in player_stats.items():
        total = stats["wins"] + stats["losses"]
        win_rate = stats["wins"] / total * 100 if total > 0 else 0
        rankings.append({"player": player, "wins": stats["wins"], "losses": stats["losses"], "total": total, "win_rate": win_rate})
    
    rankings.sort(key=lambda x: (-x["win_rate"], -x["wins"]))
    
    print("【统一排名 TOP 5】")
    print("-" * 40)
    current_rank = 1
    for i, r in enumerate(rankings[:5]):
        if i > 0 and r["win_rate"] != rankings[i-1]["win_rate"]:
            current_rank = i + 1
        print(f"{current_rank}. {r['player']} - {r['win_rate']:.1f}% ({r['wins']}胜{r['losses']}负/{r['total']}局)")

if __name__ == "__main__":
    main()
