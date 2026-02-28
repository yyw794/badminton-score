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
}

# Fixed partner pairs
FIXED_PARTNERS = {
    ("苏大哲", "罗蒙"): 5,
}

# Global config
MATCHES_PER_COURT = 10  # 增加到 10 场，确保更多人能达到 5 场
MAX_GAMES_PER_PLAYER = 5


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
    matches = []

    for male_pair in itertools.combinations(mixed_males, 2):
        for female_pair in itertools.combinations(females, 2):
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
        for player in get_match_players(match):
            if not can_player_play(player, current_round_matches, round_num, total_rounds):
                return False
        return True

    def get_match_score(match, round_num):
        """评分越低越优先被选中。
        
        评分规则：
        1. 有固定场次要求的球员：未完成时大幅减分（优先）
        2. 出场次数少的球员：大幅减分（优先）
        3. 出场次数多的球员：加分（靠后）
        4. 固定搭档组合：减分（优先）
        """
        match_players = get_match_players(match)
        scores = []
        active_games = [g for p, g in player_games.items() if g > 0]
        avg_games = sum(active_games) / len(active_games) if active_games else 0

        for player in match_players:
            constraint = get_constraint(player)
            games = player_games[player]
            fixed_games = constraint.get("fixed_games")
            score = 0
            
            # 固定场次要求：未完成时大幅减分（最高优先级之一）
            if fixed_games is not None:
                remaining = fixed_games - games
                if remaining > 0:
                    score -= remaining * 500  # 大幅提高权重
            
            # 出场次数少的球员优先：与平均值差距越大，越优先
            if active_games:
                diff_from_avg = avg_games - games
                if diff_from_avg > 0:
                    # 低于平均值的减分，差距越大减分越多
                    score -= diff_from_avg * 300
                    # 额外奖励：如果远低于平均值，再减分
                    if diff_from_avg >= 2:
                        score -= 500
                else:
                    # 高于平均值的加分
                    score += diff_from_avg * 150
            
            # 接近最大场次的球员：大幅加分（靠后）
            if MAX_GAMES_PER_PLAYER and games >= MAX_GAMES_PER_PLAYER - 1:
                score += 2000  # 接近上限的靠后
            
            scores.append(score)

        pair_a, pair_b = match
        for pair in [pair_a, pair_b]:
            pair_key = get_pair_key(pair[0], pair[1])
            if pair_key in FIXED_PARTNERS:
                weight = FIXED_PARTNERS[pair_key]
                scores.append(-weight * 50)  # 提高固定搭档权重

        return sum(scores) / len(scores) if scores else float('inf')

    mixed_pool = list(mixed_matches)
    mens_pool = list(mens_matches)
    womens_pool = list(womens_matches)

    random.shuffle(mixed_pool)
    random.shuffle(mens_pool)
    random.shuffle(womens_pool)

    mixed_count = total_matches // 2
    mens_count = total_matches // 3
    womens_count = total_matches - mixed_count - mens_count
    match_types = ["mixed"] * mixed_count + ["mens"] * mens_count + ["womens"] * womens_count
    random.shuffle(match_types)

    rounds = []
    current_round = []
    total_rounds = (total_matches + court_count - 1) // court_count

    for match_idx, match_type in enumerate(match_types):
        pool = {"mixed": mixed_pool, "mens": mens_pool, "womens": womens_pool}[match_type]
        current_round_num = len(rounds) + 1

        best_match = None
        best_score = float('inf')

        for match in pool:
            if not can_add_match(match, current_round, current_round_num, total_rounds):
                continue
            score = get_match_score(match, current_round_num)
            if score < best_score:
                best_score = score
                best_match = match

        if best_match:
            current_round.append({
                "type": {"mixed": "混双", "mens": "男双", "womens": "女双"}[match_type],
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

            if len(current_round) >= court_count:
                rounds.append(current_round)
                current_round = []
        else:
            if current_round:
                rounds.append(current_round)
                current_round = []

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
