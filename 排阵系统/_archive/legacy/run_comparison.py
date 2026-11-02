#!/usr/bin/env python3
"""
Badminton Lineup Scheduler - Comparison Runner
Runs both traditional and LLM-based schedulers and compares results.
"""

import sys
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from excel_exporter import (
    create_lineup_excel,
    calculate_player_stats, MALE_PLAYERS, FEMALE_PLAYERS,
    INTERNAL_MALE_PLAYERS, GUEST_MALE_PLAYERS,
    INTERNAL_FEMALE_PLAYERS, GUEST_FEMALE_PLAYERS,
    parse_activity_date
)
from llm_scheduler import LLMLineupScheduler, PLAYER_CONSTRAINTS, parse_signup, get_court_count


def run_traditional_scheduler(males, females, court_count):
    """Run the traditional algorithm scheduler."""
    print("\n" + "=" * 60)
    print("传统算法排阵")
    print("=" * 60)

    import lineup_scheduler as traditional

    all_players = males + females
    
    # Calculate actual available player-games (same as main())
    total_available_games = 0
    for p in all_players:
        constraint = traditional.PLAYER_CONSTRAINTS.get(p, {})
        fixed_games = constraint.get("fixed_games")
        if fixed_games is not None:
            total_available_games += fixed_games
        else:
            total_available_games += traditional.get_max_games_for_player(p)
    
    # Each match requires 4 player-games
    max_possible_matches = total_available_games // 4
    target_matches = traditional.MATCHES_PER_COURT * court_count
    total_matches = min(max_possible_matches, target_matches)

    mixed_matches = traditional.generate_mixed_doubles_matches(males, females)
    mens_matches = traditional.generate_mens_doubles_matches(males)
    womens_matches = traditional.generate_womens_doubles_matches(females)

    start_time = time.time()
    selected_matches = traditional.select_balanced_matches(
        mixed_matches, mens_matches, womens_matches,
        total_matches, court_count, all_players, males, females
    )
    elapsed = time.time() - start_time

    print(f"\n执行时间：{elapsed:.3f}秒")

    return selected_matches, elapsed


def run_llm_scheduler(males, females, court_count):
    """Run the LLM-based scheduler."""
    print("\n" + "=" * 60)
    print("LLM 推理排阵")
    print("=" * 60)

    start_time = time.time()
    
    total_players = len(males) + len(females)
    scheduler = LLMLineupScheduler(males, females, court_count, total_players)
    matches = scheduler.schedule()

    elapsed = time.time() - start_time

    print(f"\n执行时间：{elapsed:.3f}秒")

    return matches, elapsed


def analyze_schedule(matches, name):
    """Analyze a schedule and return statistics."""
    from collections import Counter, defaultdict
    
    stats = {
        'total_matches': len(matches),
        'type_distribution': Counter(),
        'player_games': defaultdict(int),
        'player_types': defaultdict(lambda: {'男双': 0, '女双': 0, '混双': 0}),
        'rounds': set(),
        'courts_used': set(),
    }
    
    for m in matches:
        match_type = m["type"]
        base_type = match_type.split(" ")[0]
        stats['type_distribution'][base_type] += 1
        
        for player in traditional.get_match_players(m["match"]):
            stats['player_games'][player] += 1
            stats['player_types'][player][base_type] += 1
        
        stats['rounds'].add(m.get('round', 1))
        stats['courts_used'].add(m.get('court', 1))
    
    return stats


def compare_schedules(traditional_matches, llm_matches):
    """Compare two schedules and print analysis."""
    print("\n" + "=" * 60)
    print("对比分析")
    print("=" * 60)
    
    # Import traditional module for utility functions
    global traditional
    import lineup_scheduler as traditional
    
    # Type distribution
    from collections import Counter
    trad_types = Counter(m["type"].split(" ")[0] for m in traditional_matches)
    llm_types = Counter(m["type"].split(" ")[0] for m in llm_matches)
    
    print("\n比赛类型分布对比:")
    print(f"  {'类型':<8} {'传统算法':<12} {'LLM 推理':<12}")
    print(f"  {'-'*32}")
    all_types = set(trad_types.keys()) | set(llm_types.keys())
    for t in sorted(all_types):
        trad_count = trad_types.get(t, 0)
        llm_count = llm_types.get(t, 0)
        print(f"  {t:<8} {trad_count:<12} {llm_count:<12}")
    
    # Player game distribution
    trad_player_games = Counter()
    llm_player_games = Counter()
    
    for m in traditional_matches:
        for p in traditional.get_match_players(m["match"]):
            trad_player_games[p] += 1
    
    for m in llm_matches:
        for p in traditional.get_match_players(m["match"]):
            llm_player_games[p] += 1
    
    print("\n球员场次对比 (传统 vs LLM):")
    all_players = set(trad_player_games.keys()) | set(llm_player_games.keys())
    for player in sorted(all_players):
        trad = trad_player_games.get(player, 0)
        llm = llm_player_games.get(player, 0)
        diff = llm - trad
        diff_str = f"{diff:+d}" if diff != 0 else "0"
        print(f"  {player:<10} {trad:<3} vs {llm:<3} ({diff_str})")
    
    # Statistics summary
    trad_games = list(trad_player_games.values())
    llm_games = list(llm_player_games.values())
    
    print("\n场次均衡性对比:")
    print(f"  传统算法：平均 {sum(trad_games)/len(trad_games):.2f}场，范围 [{min(trad_games)}, {max(trad_games)}]")
    print(f"  LLM 推理：平均 {sum(llm_games)/len(llm_games):.2f}场，范围 [{min(llm_games)}, {max(llm_games)}]")


def main():
    """Main comparison runner."""
    # Try multiple paths for flexibility
    possible_paths = [
        "微信接龙.txt",
        "排阵/微信接龙.txt",
    ]
    
    signup_text = None
    for signup_file in possible_paths:
        try:
            with open(signup_file, "r", encoding="utf-8") as f:
                signup_text = f.read()
            break
        except FileNotFoundError:
            continue
    
    if signup_text is None:
        print(f"错误：找不到报名文件，请在以下路径之一创建文件:")
        for path in possible_paths:
            print(f"  - {path}")
        return

    # Parse activity date
    activity_date = parse_activity_date(signup_text)

    males, females = parse_signup(signup_text)
    all_players = males + females
    total_players = len(all_players)

    print("=" * 60)
    print("羽毛球排阵系统 - 双算法对比")
    print("=" * 60)
    print(f"\n报名信息:")
    print(f"  男性球员 ({len(males)}人): {', '.join(males)}")
    print(f"  女性球员 ({len(females)}人): {', '.join(females)}")
    print(f"  总人数：{total_players}人")
    if activity_date:
        print(f"  活动日期：{activity_date}")

    court_count = get_court_count(total_players)
    print(f"  场地数：{court_count}个")
    
    # Run both schedulers
    traditional_matches, trad_time = run_traditional_scheduler(males, females, court_count)
    llm_matches, llm_time = run_llm_scheduler(males, females, court_count)
    
    # Compare results
    compare_schedules(traditional_matches, llm_matches)
    
    # Export both to Excel
    player_stats_trad = calculate_player_stats(traditional_matches, all_players)
    player_stats_llm = calculate_player_stats(llm_matches, all_players)
    
    # Try multiple paths for flexibility
    possible_output_paths = [
        ".",  # Current directory
        "排阵",  # 排阵 subdirectory
    ]
    
    # Find a writable directory
    output_dir = possible_output_paths[0]
    for path in possible_output_paths:
        try:
            test_file = f"{path}/test_write.tmp"
            with open(test_file, 'wb') as f:
                f.close()
            import os
            os.remove(test_file)
            output_dir = path
            break
        except (IOError, OSError):
            continue
    
    trad_output = f"{output_dir}/对阵表_传统.xlsx"
    llm_output = f"{output_dir}/对阵表_LLM.xlsx"
    
    create_lineup_excel(
        traditional_matches, court_count, trad_output, player_stats_trad,
        schedule_method="传统算法",
        activity_date=activity_date
    )

    create_lineup_excel(
        llm_matches, court_count, llm_output, player_stats_llm,
        schedule_method="LLM 推理",
        activity_date=activity_date
    )
    
    print("\n" + "=" * 60)
    print("输出文件:")
    print(f"  传统算法：{trad_output}")
    print(f"  LLM 推理：{llm_output}")
    print("=" * 60)
    
    # Summary
    print("\n总结:")
    print(f"  - 传统算法用时：{trad_time:.3f}秒")
    print(f"  - LLM 推理用时：{llm_time:.3f}秒")
    print(f"  - 传统算法生成 {len(traditional_matches)} 场比赛")
    print(f"  - LLM 推理生成 {len(llm_matches)} 场比赛")
    print("\n✓ 对比完成！可以打开两个 Excel 文件查看详细排阵结果")


if __name__ == "__main__":
    main()
