#!/usr/bin/env python3
"""
Badminton Lineup Scheduler
Generates balanced matchups for mixed doubles, men's doubles, and women's doubles.
Single sheet output optimized for A4 printing.
Supports player-specific constraints (fixed games, early departure) and fixed partners.
"""

import openpyxl
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
import itertools
from typing import List, Tuple, Dict, Optional
import random


# Player definitions
MALE_PLAYERS = [
    "苏大哲", "罗蒙", "江锐", "严勇文", "陈顺星", "陈小洪",
    "卢志辉", "林锋", "王小波", "刘继宇", "董广博", "林琪琛", "罗琴荩"
]

FEMALE_PLAYERS = [
    "田茜", "唐英武", "李祺祺", "高洁", "滕菲", "谢卓珊", "崔倩男", "林小连"
]

# Mixed doubles eligible male players
MIXED_DOUBLES_MALES = {"林锋", "王小波", "陈顺星", "罗琴荩"}

# Player-specific constraints
PLAYER_CONSTRAINTS = {
    "严勇文": {"fixed_games": 3, "early_departure": True},
    "崔倩男": {"fixed_games": 4, "early_departure": True},
    "林小连": {"only_womens_doubles": True},  # 只打女双
}

# Fixed partner pairs
FIXED_PARTNERS = {
    ("苏大哲", "罗蒙"): 5,
}

# Global config
MATCHES_PER_COURT = 6
MAX_GAMES_PER_PLAYER = 6  # 提高到 6，让球员更容易达到 5 场


def parse_signup(signup_text: str) -> Tuple[List[str], List[str]]:
    """Parse signup list and return male and female players."""
    males = []
    females = []

    for name in signup_text.strip().split("\n"):
        name = name.strip()
        if not name or name.startswith("#") or name.startswith("2026"):
            continue
        if "." in name or "," in name:
            name = name.split(".", 1)[-1].split(",", 1)[-1].strip()

        if name in MALE_PLAYERS:
            males.append(name)
        elif name in FEMALE_PLAYERS:
            females.append(name)

    return males, females


def get_court_count(total_players: int) -> int:
    """Determine number of courts based on player count."""
    if total_players <= 12:
        return 2
    return 3


def generate_mixed_doubles_matches(males: List[str], females: List[str]) -> List[Tuple[Tuple[str, str], Tuple[str, str]]]:
    """Generate mixed doubles matches."""
    mixed_males = [m for m in males if m in MIXED_DOUBLES_MALES]
    
    # 过滤只打女双的球员
    mixed_females = [f for f in females if not PLAYER_CONSTRAINTS.get(f, {}).get("only_womens_doubles")]
    
    matches = []

    for male_pair in itertools.combinations(mixed_males, 2):
        for female_pair in itertools.combinations(mixed_females, 2):
            match = ((male_pair[0], female_pair[0]), (male_pair[1], female_pair[1]))
            matches.append(match)

    return matches


def generate_mens_doubles_matches(males: List[str]) -> List[Tuple[Tuple[str, str], Tuple[str, str]]]:
    """Generate men's doubles matches."""
    matches = []
    for pair1 in itertools.combinations(males, 2):
        remaining = [m for m in males if m not in pair1]
        if len(remaining) < 2:
            continue
        for pair2 in itertools.combinations(remaining, 2):
            match = (pair1, pair2)
            matches.append(match)
    return matches


def generate_womens_doubles_matches(females: List[str]) -> List[Tuple[Tuple[str, str], Tuple[str, str]]]:
    """Generate women's doubles matches."""
    matches = []
    if len(females) < 4:
        return matches

    for pair1 in itertools.combinations(females, 2):
        remaining = [f for f in females if f not in pair1]
        if len(remaining) < 2:
            continue
        for pair2 in itertools.combinations(remaining, 2):
            match = (pair1, pair2)
            matches.append(match)
    return matches


def get_match_players(match: Tuple[Tuple[str, str], Tuple[str, str]]) -> set:
    """Get all players in a match."""
    players = set()
    for pair in match:
        players.update(pair)
    return players


def get_pair_key(p1: str, p2: str) -> tuple:
    """Get normalized pair key."""
    return tuple(sorted([p1, p2]))


def select_balanced_matches(
    mixed_matches: List, mens_matches: List, womens_matches: List,
    total_matches: int, court_count: int, players: List[str],
    males: List[str], females: List[str]
) -> List[Dict]:
    """Select balanced matches with all constraints."""
    selected = []
    player_games = {p: 0 for p in players}
    partner_games = {pair: 0 for pair in FIXED_PARTNERS}

    def get_constraint(player):
        return PLAYER_CONSTRAINTS.get(player, {})

    def can_player_play(player, current_round_matches, round_num, total_rounds):
        constraint = get_constraint(player)
        fixed_games = constraint.get("fixed_games")

        if fixed_games is not None and player_games[player] >= fixed_games:
            return False
        if MAX_GAMES_PER_PLAYER is not None and player_games[player] >= MAX_GAMES_PER_PLAYER:
            return False
        for m in current_round_matches:
            if player in get_match_players(m["match"]):
                return False
        return True

    def can_add_match(match, current_round_matches, round_num, total_rounds):
        match_type = None
        for m in current_round_matches:
            if m.get("type"):
                match_type = m["type"]
                break
        
        for player in get_match_players(match):
            # 检查特殊约束：只打女双的球员不能参加混双
            constraint = get_constraint(player)
            if constraint.get("only_womens_doubles"):
                # 如果当前比赛不是女双，该球员不能参加
                if match_type and match_type != "女双":
                    # 检查当前轮次是否有女双比赛可以安排
                    pass  # 在 try_add_match 中处理
            
            if not can_player_play(player, current_round_matches, round_num, total_rounds):
                return False
        return True

    def get_match_score(match, round_num):
        """评分越低越优先被选中。
        
        评分规则：
        1. 有固定场次要求的球员：未完成时大幅减分（最优先）
        2. 未达到 5 场的球员：减分（优先）
        3. 达到 5 场的球员：小幅加分（靠后）
        4. 达到 6 场的球员：大幅加分（最后）
        5. 固定搭档组合：减分（优先）
        """
        match_players = get_match_players(match)
        scores = []
        active_games = [g for p, g in player_games.items() if g > 0]
        avg_games = sum(active_games) / len(active_games) if active_games else 0

        TARGET_GAMES = 5  # 目标场次
        
        for player in match_players:
            constraint = get_constraint(player)
            games = player_games[player]
            fixed_games = constraint.get("fixed_games")
            score = 0
            
            # 固定场次要求：未完成时大幅减分（最优先）
            if fixed_games is not None:
                remaining = fixed_games - games
                if remaining > 0:
                    score -= remaining * 1000
            
            # 未达到目标场次的球员优先
            if games < TARGET_GAMES:
                score -= (TARGET_GAMES - games) * 200
            elif games >= MAX_GAMES_PER_PLAYER:
                # 达到最大场次，大幅加分（靠后）
                score += 2000
            else:
                # 达到 5 场但未到 6 场，小幅加分
                score += (games - TARGET_GAMES) * 100
            
            scores.append(score)

        pair_a, pair_b = match
        for pair in [pair_a, pair_b]:
            pair_key = get_pair_key(pair[0], pair[1])
            if pair_key in FIXED_PARTNERS:
                weight = FIXED_PARTNERS[pair_key]
                scores.append(-weight * 30)

        return sum(scores) / len(scores) if scores else float('inf')

    mixed_pool = list(mixed_matches)
    mens_pool = list(mens_matches)
    womens_pool = list(womens_matches)

    random.shuffle(mixed_pool)
    random.shuffle(mens_pool)
    random.shuffle(womens_pool)

    # 预设比赛类型比例和目标数量
    mixed_target = total_matches // 2  # 混双约 50%
    mens_target = total_matches // 3   # 男双约 33%
    womens_target = total_matches - mixed_target - mens_target  # 女双剩余
    
    mixed_used = 0
    mens_used = 0
    womens_used = 0

    rounds = []
    current_round = []
    total_rounds = (total_matches + court_count - 1) // court_count

    def try_add_match(pool, match_type_name, current_count, target_count):
        """尝试添加一场比赛到当前轮次，返回是否成功。"""
        nonlocal current_round, mixed_used, mens_used, womens_used

        # 如果已达到目标数量，跳过（除非其他类型都无法添加）
        if current_count >= target_count + 2:  # 允许稍微超出
            return False, current_count

        current_round_num = len(rounds) + 1
        best_match = None
        best_score = float('inf')

        for match in pool:
            # 检查是否有球员不能参加该类型的比赛
            can_play = True
            for player in get_match_players(match):
                constraint = get_constraint(player)
                if constraint.get("only_womens_doubles") and match_type_name != "womens":
                    can_play = False
                    break
            
            if not can_play:
                continue
                
            if not can_add_match(match, current_round, current_round_num, total_rounds):
                continue
            score = get_match_score(match, current_round_num)
            if score < best_score:
                best_score = score
                best_match = match

        if best_match:
            current_round.append({
                "type": {"mixed": "混双", "mens": "男双", "womens": "女双"}[match_type_name],
                "match": best_match
            })
            for player in get_match_players(best_match):
                player_games[player] += 1
            pair_a, pair_b = best_match
            for pair in [pair_a, pair_b]:
                pair_key = get_pair_key(pair[0], pair[1])
                if pair_key in partner_games:
                    partner_games[pair_key] += 1
            pool.remove(best_match)

            # 更新计数
            if match_type_name == "mixed":
                mixed_used += 1
            elif match_type_name == "mens":
                mens_used += 1
            else:
                womens_used += 1

            return True, current_count + 1
        return False, current_count

    # 多轮填充：每轮尝试填满所有场地
    # 优先级：女双 > 混双 > 男双（确保女性球员先安排女双）
    type_priorities = [
        ("womens", lambda: womens_used, lambda: womens_target + 2, womens_pool),  # 女双最优先
        ("mixed", lambda: mixed_used, lambda: mixed_target, mixed_pool),
        ("mens", lambda: mens_used, lambda: mens_target, mens_pool),
    ]
    
    for round_num in range(total_rounds):
        current_round = []
        
        # 尝试填满当前轮次的所有场地
        for court_slot in range(court_count):
            added = False
            
            # 按优先级尝试每种比赛类型
            for match_type, get_used, get_target, pool in type_priorities:
                if not pool:
                    continue
                success, new_count = try_add_match(pool, match_type, get_used(), get_target())
                if success:
                    added = True
                    # 更新计数
                    if match_type == "mixed":
                        mixed_used = new_count
                    elif match_type == "womens":
                        womens_used = new_count
                    else:
                        mens_used = new_count
                    break
            
            # 如果优先级类型都无法添加，尝试所有类型
            if not added:
                for match_type, get_used, get_target, pool in type_priorities:
                    if not pool:
                        continue
                    # 放宽限制
                    success, new_count = try_add_match(pool, match_type, 0, 999)
                    if success:
                        added = True
                        if match_type == "mixed":
                            mixed_used = new_count
                        elif match_type == "womens":
                            womens_used = new_count
                        else:
                            mens_used = new_count
                        break
            
            if not added:
                break
        
        if current_round:
            rounds.append(current_round)

    all_matches = []
    for round_matches in rounds:
        for match_info in round_matches:
            all_matches.append(match_info)

    final_rounds = []
    match_idx = 0
    while match_idx < len(all_matches):
        round_matches = []
        for court_idx in range(court_count):
            if match_idx < len(all_matches):
                all_matches[match_idx]["court"] = court_idx + 1
                round_matches.append(all_matches[match_idx])
                match_idx += 1
        if round_matches:
            final_rounds.append(round_matches)

    rounds = final_rounds
    selected = []
    for round_idx, round_matches in enumerate(rounds):
        for court_idx, match_info in enumerate(round_matches):
            match_info["court"] = court_idx + 1
            match_info["round"] = round_idx + 1
            selected.append(match_info)

    return selected


def create_lineup_excel(matches: List[Dict], court_count: int, output_path: str, player_stats: Dict = None):
    """Create Excel file with lineup schedule."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "对阵表"

    font_title = Font(name="微软雅黑", size=18, bold=True)
    font_header = Font(name="微软雅黑", size=11, bold=True)
    font_content = Font(name="微软雅黑", size=10)
    alignment_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    border = Border(left=Side(style="thin"), right=Side(style="thin"), top=Side(style="thin"), bottom=Side(style="thin"))
    header_fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")

    ws.merge_cells("A1:G1")
    ws["A1"] = "科技球队日常训练活动 - 对阵表"
    ws["A1"].font = font_title
    ws["A1"].alignment = alignment_center
    ws["A1"].border = border

    ws.merge_cells("A2:G2")
    ws["A2"] = f"场地数：{court_count}个 | 时长：2 小时 | 赛制：15 分/局，2 局 | 项目：男双、女双、混双"
    ws["A2"].font = Font(name="微软雅黑", size=10)
    ws["A2"].alignment = alignment_center

    headers = ["轮次", "场地", "类型", "对阵 A", "比分 A", "比分 B", "对阵 B"]
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=3, column=col, value=header)
        cell.font = font_header
        cell.alignment = alignment_center
        cell.border = border
        cell.fill = header_fill

    for row_idx, match_info in enumerate(matches, 4):
        match_type = match_info["type"]
        match = match_info["match"]
        court = match_info["court"]
        round_num = match_info.get("round", 1)
        display_round = (row_idx - 4) // court_count + 1

        ws.cell(row=row_idx, column=1, value=display_round).font = font_content
        ws.cell(row=row_idx, column=2, value=f"{court}号").font = font_content
        ws.cell(row=row_idx, column=3, value=match_type).font = font_content
        ws.cell(row=row_idx, column=4, value="/".join(match[0])).font = font_content
        ws.cell(row=row_idx, column=5, value="").font = font_content
        ws.cell(row=row_idx, column=6, value="").font = font_content
        ws.cell(row=row_idx, column=7, value="/".join(match[1])).font = font_content

        for col in range(1, 8):
            ws.cell(row=row_idx, column=col).alignment = alignment_center
            ws.cell(row=row_idx, column=col).border = border

    ws.column_dimensions["A"].width = 7
    ws.column_dimensions["B"].width = 9
    ws.column_dimensions["C"].width = 9
    ws.column_dimensions["D"].width = 22
    ws.column_dimensions["E"].width = 12
    ws.column_dimensions["F"].width = 12
    ws.column_dimensions["G"].width = 22

    max_row = len(matches) + 3
    for row in ws.iter_rows(min_row=1, max_row=max_row if max_row > 3 else 20):
        ws.row_dimensions[row[0].row].height = 32

    ws.page_setup.paperSize = 9
    ws.page_setup.orientation = "landscape"
    ws.page_margins.left = 0.3
    ws.page_margins.right = 0.3
    ws.page_margins.top = 0.5
    ws.page_margins.bottom = 0.5

    if player_stats:
        ws_stats = wb.create_sheet(title="球员统计")
        font_title = Font(name="微软雅黑", size=14, bold=True)
        font_header = Font(name="微软雅黑", size=11, bold=True)
        font_content = Font(name="微软雅黑", size=10)
        alignment_center = Alignment(horizontal="center", vertical="center")
        border = Border(left=Side(style="thin"), right=Side(style="thin"), top=Side(style="thin"), bottom=Side(style="thin"))
        header_fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")

        ws_stats.merge_cells("A1:E1")
        ws_stats["A1"] = "球员参赛场次统计"
        ws_stats["A1"].font = font_title
        ws_stats["A1"].alignment = alignment_center
        ws_stats["A1"].border = border

        headers = ["姓名", "总场次", "男双", "女双", "混双"]
        for col, header in enumerate(headers, 1):
            cell = ws_stats.cell(row=2, column=col, value=header)
            cell.font = font_header
            cell.alignment = alignment_center
            cell.border = border
            cell.fill = header_fill

        row = 3
        male_players = [p for p in player_stats.keys() if p in MALE_PLAYERS]
        female_players = [p for p in player_stats.keys() if p in FEMALE_PLAYERS]

        for player in sorted(male_players):
            stats = player_stats[player]
            ws_stats.cell(row=row, column=1, value=player).font = font_content
            ws_stats.cell(row=row, column=2, value=stats["total"]).font = font_content
            ws_stats.cell(row=row, column=3, value=stats.get("男双", 0)).font = font_content
            ws_stats.cell(row=row, column=4, value=stats.get("女双", 0)).font = font_content
            ws_stats.cell(row=row, column=5, value=stats.get("混双", 0)).font = font_content
            for col in range(1, 6):
                ws_stats.cell(row=row, column=col).alignment = alignment_center
                ws_stats.cell(row=row, column=col).border = border
            row += 1

        for player in sorted(female_players):
            stats = player_stats[player]
            ws_stats.cell(row=row, column=1, value=player).font = font_content
            ws_stats.cell(row=row, column=2, value=stats["total"]).font = font_content
            ws_stats.cell(row=row, column=3, value=stats.get("男双", 0)).font = font_content
            ws_stats.cell(row=row, column=4, value=stats.get("女双", 0)).font = font_content
            ws_stats.cell(row=row, column=5, value=stats.get("混双", 0)).font = font_content
            for col in range(1, 6):
                ws_stats.cell(row=row, column=col).alignment = alignment_center
                ws_stats.cell(row=row, column=col).border = border
            row += 1

        ws_stats.column_dimensions["A"].width = 12
        ws_stats.column_dimensions["B"].width = 10
        ws_stats.column_dimensions["C"].width = 10
        ws_stats.column_dimensions["D"].width = 10
        ws_stats.column_dimensions["E"].width = 10

    wb.save(output_path)
    print(f"对阵表已生成：{output_path}")


def main():
    signup_file = "排阵/微信接龙.txt"
    with open(signup_file, "r", encoding="utf-8") as f:
        signup_text = f.read()

    males, females = parse_signup(signup_text)
    all_players = males + females
    total_players = len(all_players)

    print(f"报名男性 ({len(males)}人): {', '.join(males)}")
    print(f"报名女性 ({len(females)}人): {', '.join(females)}")
    print(f"总人数：{total_players}人")

    court_count = get_court_count(total_players)
    print(f"场地数量：{court_count}个")

    mixed_matches = generate_mixed_doubles_matches(males, females)
    mens_matches = generate_mens_doubles_matches(males)
    womens_matches = generate_womens_doubles_matches(females)

    print(f"\n配置参数:")
    print(f"  - 每场地比赛数：{MATCHES_PER_COURT}场")
    print(f"  - 总比赛数：{MATCHES_PER_COURT * court_count}场")
    print(f"  - 球员最大场次：{MAX_GAMES_PER_PLAYER if MAX_GAMES_PER_PLAYER else '不限制'}")

    matches_per_court = MATCHES_PER_COURT
    total_matches = matches_per_court * court_count

    selected_matches = select_balanced_matches(
        mixed_matches, mens_matches, womens_matches, total_matches, court_count, all_players, males, females
    )

    from collections import Counter
    match_type_counts = Counter()
    court_counts = Counter()
    for m in selected_matches:
        match_type_counts[m["type"]] += 1
        court_counts[m["court"]] += 1

    print(f"\n比赛类型分布:")
    for t, c in sorted(match_type_counts.items()):
        print(f"  - {t}: {c}场")

    print(f"\n场地分布:")
    for court, c in sorted(court_counts.items()):
        print(f"  - {court}号场地：{c}场")

    print(f"\n球员参赛场次统计:")
    player_games = {}
    player_type_games = {}
    for m in selected_matches:
        match_type = m["type"]
        for player in get_match_players(m["match"]):
            player_games[player] = player_games.get(player, 0) + 1
            if player not in player_type_games:
                player_type_games[player] = {"男双": 0, "女双": 0, "混双": 0}
            player_type_games[player][match_type] += 1

    for player in sorted(all_players):
        games = player_games.get(player, 0)
        constraint = PLAYER_CONSTRAINTS.get(player, {})
        note = ""
        fixed_games = constraint.get("fixed_games")
        if fixed_games is not None:
            if games == fixed_games:
                note = f" (已完成{fixed_games}场)"
            elif games < fixed_games:
                note = f" (目标{fixed_games}场，还差{fixed_games - games}场)"
        if constraint.get("early_departure"):
            note += " [需提前离场]"
        type_stats = player_type_games.get(player, {"男双": 0, "女双": 0, "混双": 0})
        type_str = f"(男{type_stats['男双']}/女{type_stats['女双']}/混{type_stats['混双']})"
        print(f"  - {player}: {games}场 {type_str}{note}")

    player_stats = {}
    for player in all_players:
        type_stats = player_type_games.get(player, {"男双": 0, "女双": 0, "混双": 0})
        player_stats[player] = {
            "total": player_games.get(player, 0),
            "男双": type_stats["男双"],
            "女双": type_stats["女双"],
            "混双": type_stats["混双"]
        }

    output_path = "排阵/对阵表.xlsx"
    create_lineup_excel(selected_matches, court_count, output_path, player_stats)


if __name__ == "__main__":
    main()
