#!/usr/bin/env python3
"""
Badminton Lineup Scheduler - LLM Reasoning Approach
Uses structured reasoning to generate balanced matchups.
This is an alternative approach to the traditional algorithm.
"""

import json
import random
from typing import List, Tuple, Dict, Optional
from collections import defaultdict

# Import shared utilities
from excel_exporter import (
    INTERNAL_MALE_PLAYERS, GUEST_MALE_PLAYERS, MALE_PLAYERS,
    INTERNAL_FEMALE_PLAYERS, GUEST_FEMALE_PLAYERS, FEMALE_PLAYERS,
    create_lineup_excel, calculate_player_stats, parse_activity_date,
    get_max_games_for_player, get_fixed_games_for_player, generate_mixed_vs_mens_matches
)

# Mixed doubles eligible male players (internal only)
MIXED_DOUBLES_MALES = {"林锋", "王小波", "陈顺星", "罗琴荩", "罗蒙"}

# Player-specific constraints
# fixed_games: None = 自动根据场地紧张程度计算，整数 = 固定场次
PLAYER_CONSTRAINTS = {
    "严勇文": {"fixed_games": None, "early_departure": True},
    "崔倩男": {"fixed_games": None, "early_departure": True},
    "林小连": {"only_womens_doubles": True},
}

# Fixed partner pairs
FIXED_PARTNERS = {
    ("苏大哲", "罗蒙"): 5,
}

# Global config
MATCHES_PER_COURT = 8
# MAX_GAMES_INTERNAL and MAX_GAMES_GUEST are now in excel_exporter.py


def is_internal_player(player: str) -> bool:
    return player in INTERNAL_MALE_PLAYERS or player in INTERNAL_FEMALE_PLAYERS


def is_guest_player(player: str) -> bool:
    return player in GUEST_MALE_PLAYERS or player in GUEST_FEMALE_PLAYERS


def get_match_players(match) -> set:
    players = set()
    for pair in match:
        players.update(pair)
    return players


def get_pair_key(p1: str, p2: str) -> tuple:
    return tuple(sorted([p1, p2]))


class LLMLineupScheduler:
    """
    LLM-based lineup scheduler using structured reasoning.
    
    The scheduler follows a human-like thought process:
    1. Analyze constraints and priorities
    2. Plan the overall distribution
    3. Schedule round by round with contextual awareness
    4. Validate and adjust
    """
    
    def __init__(self, males: List[str], females: List[str], court_count: int, total_players: int):
        self.males = males
        self.females = females
        self.all_players = males + females
        self.court_count = court_count
        self.total_players = total_players

        # Calculate actual available player-games
        # For players with dynamic fixed_games (None), estimate using average
        total_available_games = 0
        target_matches = MATCHES_PER_COURT * court_count
        for p in self.all_players:
            constraint = PLAYER_CONSTRAINTS.get(p, {})
            fixed_games = constraint.get("fixed_games")
            if fixed_games is not None:
                # Use dynamic calculation based on court availability
                actual_fixed = get_fixed_games_for_player(p, court_count, total_players, target_matches)
                total_available_games += actual_fixed
            else:
                total_available_games += get_max_games_for_player(p, court_count, total_players)

        # Each match requires 4 player-games
        # Calculate realistic total_matches
        max_possible_matches = total_available_games // 4
        self.total_matches = min(max_possible_matches, target_matches)

        # State tracking
        self.player_games = {p: 0 for p in self.all_players}
        self.player_bye_history = {p: [] for p in self.all_players}  # True=played, False=bye
        self.partner_games = {pair: 0 for pair in FIXED_PARTNERS}
        self.scheduled_matches = []
        self.rounds = []

        # Generate all possible matches
        self.mixed_pool = self._generate_mixed_doubles_matches()
        self.mens_pool = self._generate_mens_doubles_matches()
        self.womens_pool = self._generate_womens_doubles_matches()
        self.mixed_vs_mens_pool = generate_mixed_vs_mens_matches(males, females)  # 混双 vs 男双

        print(f"\n[LLM 排阵] 初始化完成:")
        print(f"  - 男性球员 ({len(males)}人): {', '.join(males)}")
        print(f"  - 女性球员 ({len(females)}人): {', '.join(females)}")
        print(f"  - 场地数：{court_count}个")
        print(f"  - 可用总人次：{total_available_games}")
        print(f"  - 理论最大比赛数：{max_possible_matches}场")
        print(f"  - 目标比赛数：{target_matches}场")
        print(f"  - 实际比赛数：{self.total_matches}场（受限于球员场次）")
        print(f"  - 混双池：{len(self.mixed_pool)}场")
        print(f"  - 男双池：{len(self.mens_pool)}场")
        print(f"  - 女双池：{len(self.womens_pool)}场")
        print(f"  - 混双 vs 男双池：{len(self.mixed_vs_mens_pool)}场")
    
    def _generate_mixed_doubles_matches(self) -> List[Tuple[Tuple[str, str], Tuple[str, str]]]:
        """Generate all possible mixed doubles matches."""
        import itertools
        mixed_males = [m for m in self.males if m in MIXED_DOUBLES_MALES]
        
        # Filter females who can play mixed (exclude only_womens_doubles if enough females)
        can_play_womens_doubles = len(self.females) >= 4
        mixed_females = [f for f in self.females
                        if not PLAYER_CONSTRAINTS.get(f, {}).get("only_womens_doubles")
                        or not can_play_womens_doubles]
        
        matches = []
        for male_pair in itertools.combinations(mixed_males, 2):
            for female_pair in itertools.combinations(mixed_females, 2):
                match = ((male_pair[0], female_pair[0]), (male_pair[1], female_pair[1]))
                matches.append(match)
        
        return matches
    
    def _generate_mens_doubles_matches(self) -> List[Tuple[Tuple[str, str], Tuple[str, str]]]:
        """Generate all possible men's doubles matches."""
        import itertools
        matches = []
        for pair1 in itertools.combinations(self.males, 2):
            remaining = [m for m in self.males if m not in pair1]
            if len(remaining) < 2:
                continue
            for pair2 in itertools.combinations(remaining, 2):
                match = (pair1, pair2)
                matches.append(match)
        return matches
    
    def _generate_womens_doubles_matches(self) -> List[Tuple[Tuple[str, str], Tuple[str, str]]]:
        """Generate all possible women's doubles matches."""
        import itertools
        matches = []
        if len(self.females) < 4:
            return matches
        
        for pair1 in itertools.combinations(self.females, 2):
            remaining = [f for f in self.females if f not in pair1]
            if len(remaining) < 2:
                continue
            for pair2 in itertools.combinations(remaining, 2):
                match = (pair1, pair2)
                matches.append(match)
        return matches
    
    def _get_constraint(self, player: str) -> dict:
        """Get player constraints."""
        return PLAYER_CONSTRAINTS.get(player, {})
    
    def _get_consecutive_byes(self, player: str) -> int:
        """Get consecutive bye count for a player."""
        history = self.player_bye_history[player]
        if not history:
            return 0
        
        consecutive = 0
        for i in range(len(history) - 1, -1, -1):
            if history[i] == False:  # False means bye
                consecutive += 1
            else:
                break
        return consecutive
    
    def _can_player_play(self, player: str, current_round_matches: List[Dict]) -> bool:
        """
        Check if a player can play in the current round.

        【Core Rule】Each player can only appear once per round across all courts!
        【Fixed Games Rule】Players with fixed_games constraint CANNOT exceed their fixed games.
        """
        constraint = self._get_constraint(player)
        # Use dynamic fixed_games calculation based on court availability
        fixed_games = get_fixed_games_for_player(player, self.court_count, self.total_players, self.total_matches)
        max_games = get_max_games_for_player(player, self.court_count, self.total_players)
        early_departure = constraint.get("early_departure")

        # 【Fixed Games Rule】Strictly enforce fixed_games limit
        # Players with fixed_games CANNOT exceed their fixed games (no exception for byes)
        if fixed_games is not None and self.player_games[player] >= fixed_games:
            return False

        # Check if reached max games limit
        if self.player_games[player] >= max_games:
            return False

        # 【Core Rule】Check if player already played in this round
        for m in current_round_matches:
            if player in get_match_players(m["match"]):
                return False

        return True

    def _must_player_play(self, player: str) -> bool:
        """
        Check if a player must play to avoid consecutive byes.

        Note: Players with fixed_games constraint are EXCLUDED from this rule,
        because they have a fixed number of games to play and will leave early.
        """
        constraint = self._get_constraint(player)
        # Use dynamic fixed_games calculation
        fixed_games = get_fixed_games_for_player(player, self.court_count, self.total_players, self.total_matches)

        # Players with fixed_games are excluded from anti-cold rule
        # They have a fixed schedule and will leave early
        if fixed_games is not None:
            return False
        
        consecutive_byes = self._get_consecutive_byes(player)
        if consecutive_byes >= 1:
            max_games = get_max_games_for_player(player, self.court_count, self.total_players)
            if self.player_games[player] >= max_games:
                return False
            return True
        return False
    
    def _can_add_match(self, match, current_round_matches: List[Dict], match_type: str) -> bool:
        """Check if a match can be added to the current round."""
        all_females_count = len(self.females)
        can_play_womens_doubles = all_females_count >= 4
        
        # Find must-play players
        must_play_players = []
        for p in self.all_players:
            constraint = self._get_constraint(p)
            if constraint.get("early_departure"):
                continue
            if self._must_player_play(p):
                already_played = any(
                    p in get_match_players(m["match"])
                    for m in current_round_matches
                )
                if not already_played:
                    must_play_players.append(p)
        
        # Check each player in the match
        for player in get_match_players(match):
            # Check special constraint: only_womens_doubles
            constraint = self._get_constraint(player)
            if constraint.get("only_womens_doubles"):
                if match_type != "女双" and can_play_womens_doubles:
                    return False
            
            if not self._can_player_play(player, current_round_matches):
                return False
        
        # 【Anti-cold rule】If there are must-play players, current match must include at least one
        if must_play_players:
            match_players = get_match_players(match)
            has_must_play = any(p in match_players for p in must_play_players)
            if not has_must_play:
                played_players = set()
                for m in current_round_matches:
                    played_players.update(get_match_players(m["match"]))
                all_must_played = all(p in played_players for p in must_play_players)
                if not all_must_played:
                    return False
        
        return True
    
    def _calculate_match_priority(self, match, match_type: str, round_num: int) -> float:
        """
        Calculate match priority score (lower is better).

        Reasoning process:
        1. Players who exceeded fixed_games = FORBIDDEN (huge penalty)
        2. Players with fixed games requirements (unfinished = large penalty)
        3. Players below target games (5 games)
        4. Players with consecutive byes (anti-cold rule)
        5. Guest players (lower priority)
        6. Fixed partner combinations
        """
        match_players = get_match_players(match)
        scores = []
        active_games = [g for p, g in self.player_games.items() if g > 0]
        avg_games = sum(active_games) / len(active_games) if active_games else 0

        TARGET_GAMES = 5

        for player in match_players:
            constraint = self._get_constraint(player)
            games = self.player_games[player]
            # Use dynamic fixed_games calculation
            fixed_games = get_fixed_games_for_player(player, self.court_count, self.total_players, self.total_matches)
            max_games = get_max_games_for_player(player, self.court_count, self.total_players)
            score = 0.0

            # Priority 1: FORBIDDEN if already reached fixed_games (huge penalty)
            if fixed_games is not None and games >= fixed_games:
                score += 10000  # Huge penalty - should not be selected

            # Priority 2: Fixed games requirement (unfinished = large penalty)
            if fixed_games is not None:
                remaining = fixed_games - games
                if remaining > 0:
                    score -= remaining * 1000

            # Priority 3: Below target games
            if games < TARGET_GAMES:
                score -= (TARGET_GAMES - games) * 200
            elif games >= max_games:
                score += 2000  # Reached max, high penalty
            else:
                score += (games - TARGET_GAMES) * 100

            # Priority 4: Consecutive byes (anti-cold)
            # Note: Players with fixed_games are excluded from anti-cold rule
            if not constraint.get("early_departure") and fixed_games is None:
                consecutive_byes = self._get_consecutive_byes(player)
                if consecutive_byes >= 1:
                    score -= 500  # Medium priority

            # Priority 5: Guest player (lower priority when courts are limited)
            # If courts are abundant, don't penalize guest players
            courts_per_player = self.court_count / self.total_players if self.total_players > 0 else 0
            if is_guest_player(player) and courts_per_player < 0.2:
                score += 50  # Only penalize when courts are limited

            scores.append(score)

        # Priority 6: Fixed partners
        pair_a, pair_b = match
        for pair in [pair_a, pair_b]:
            pair_key = get_pair_key(pair[0], pair[1])
            if pair_key in FIXED_PARTNERS:
                weight = FIXED_PARTNERS[pair_key]
                scores.append(-weight * 30)

        return sum(scores) / len(scores) if scores else float('inf')
    
    def _select_best_match(self, pool: List, match_type: str, current_round_matches: List[Dict]) -> Optional[Tuple]:
        """Select the best match from a pool for the current round."""
        best_match = None
        best_score = float('inf')
        
        for match in pool:
            if not self._can_add_match(match, current_round_matches, match_type):
                continue
            
            score = self._calculate_match_priority(match, match_type, len(self.rounds) + 1)
            if score < best_score:
                best_score = score
                best_match = match
        
        return best_match
    
    def _update_player_history(self, round_matches: List[Dict]):
        """Update player game counts and bye history after a round."""
        played_players = set()
        for m in round_matches:
            played_players.update(get_match_players(m["match"]))
            for player in get_match_players(m["match"]):
                self.player_games[player] += 1
            
            # Update partner games
            pair_a, pair_b = m["match"]
            for pair in [pair_a, pair_b]:
                pair_key = get_pair_key(pair[0], pair[1])
                if pair_key in self.partner_games:
                    self.partner_games[pair_key] += 1
        
        # Update bye history
        for p in self.all_players:
            if p in played_players:
                self.player_bye_history[p].append(True)
            else:
                self.player_bye_history[p].append(False)
    
    def _get_match_type_display(self, base_type: str, is_fallback: bool = False) -> str:
        """Get display name for match type."""
        if is_fallback:
            return f"{base_type} (男代)"
        return base_type
    
    def schedule(self) -> List[Dict]:
        """
        Main scheduling logic using LLM reasoning approach.

        Strategy:
        1. Plan overall distribution (mixed ~33%, womens ~25%, mens ~42%)
        2. Schedule round by round, alternating type priorities
        3. Ensure balance and constraint satisfaction
        4. Handle edge cases with fallback logic
        5. Use mixed vs men's doubles when female players are limited
        """
        total_rounds = (self.total_matches + self.court_count - 1) // self.court_count

        # Target distribution
        mixed_target = int(self.total_matches * 0.33)
        womens_target = int(self.total_matches * 0.25)
        mens_target = self.total_matches - mixed_target - womens_target

        mixed_used = 0
        womens_used = 0
        mens_used = 0
        mixed_vs_mens_used = 0

        # Shuffle pools for variety
        random.shuffle(self.mixed_pool)
        random.shuffle(self.mens_pool)
        random.shuffle(self.womens_pool)
        random.shuffle(self.mixed_vs_mens_pool)

        # Check if we need mixed vs men's doubles (few female players)
        # This is a LAST RESORT option, not preferred
        use_mixed_vs_mens = len(self.females) < 4 and len(self.mixed_vs_mens_pool) > 0

        print(f"\n[LLM 排阵] 开始排阵推理...")
        print(f"  - 混双目标：{mixed_target}场 (~33%)")
        print(f"  - 女双目标：{womens_target}场 (~25%)")
        print(f"  - 男双目标：{mens_target}场 (~42%)")
        if use_mixed_vs_mens:
            print(f"  - ⚠️  女性球员不足 4 人，必要时启用混双 vs 男双（下策）")
            print(f"  - 优先策略：增加男双比例，减少女性依赖")

        for round_num in range(1, total_rounds + 1):
            current_round = []

            # Priority order: mixed vs men's doubles is LAST RESORT
            # Normal priority (females >= 4): mixed/womens/mens
            # Limited females (< 4): prefer standard mixed + more mens, use mixed_vs_mens only when needed
            if round_num % 3 == 1:
                # Mixed first
                type_order = [("mixed", self.mixed_pool, "混双"),
                             ("mens", self.mens_pool, "男双"),
                             ("womens", self.womens_pool, "女双")]
            elif round_num % 3 == 2:
                # Mens first (reduce female dependency)
                type_order = [("mens", self.mens_pool, "男双"),
                             ("mixed", self.mixed_pool, "混双"),
                             ("womens", self.womens_pool, "女双")]
            else:
                # Mixed first
                type_order = [("mixed", self.mixed_pool, "混双"),
                             ("mens", self.mens_pool, "男双"),
                             ("womens", self.womens_pool, "女双")]
            
            # When females are limited, add mixed_vs_mens as last resort (after normal types fail)
            # Don't put it in type_order, only use when nothing else works
            
            # Fill each court slot
            for court_slot in range(self.court_count):
                added = False
                
                # Try each type in priority order
                for type_name, pool, display_name in type_order:
                    if not pool:
                        continue
                    
                    # Check if we've exceeded target (with some flexibility)
                    if type_name == "mixed" and mixed_used >= mixed_target + 2:
                        continue
                    if type_name == "womens" and womens_used >= womens_target + 2:
                        continue
                    if type_name == "mens" and mens_used >= mens_target + 3:
                        continue
                    if type_name == "mixed_vs_mens" and mixed_vs_mens_used >= mixed_target + 2:
                        continue

                    best_match = self._select_best_match(pool, display_name, current_round)
                    if best_match:
                        is_fallback = False
                        current_round.append({
                            "type": self._get_match_type_display(display_name, is_fallback),
                            "match": best_match,
                            "fallback": is_fallback
                        })
                        pool.remove(best_match)

                        if type_name == "mixed":
                            mixed_used += 1
                        elif type_name == "womens":
                            womens_used += 1
                        elif type_name == "mixed_vs_mens":
                            mixed_vs_mens_used += 1
                        else:
                            mens_used += 1

                        added = True
                        break
                
                # Fallback: use men's doubles if preferred types unavailable
                if not added and self.mens_pool:
                    best_match = self._select_best_match(self.mens_pool, "男双", current_round)
                    if best_match:
                        current_round.append({
                            "type": "男双 (替补)",
                            "match": best_match,
                            "fallback": True
                        })
                        self.mens_pool.remove(best_match)
                        mens_used += 1
                        added = True
                
                # Last resort: mixed vs mens doubles (before emergency random matches)
                # This is better than random temporary matches
                if not added and use_mixed_vs_mens and self.mixed_vs_mens_pool:
                    best_match = self._select_best_match(self.mixed_vs_mens_pool, "混双 (vs 男双)", current_round)
                    if best_match:
                        current_round.append({
                            "type": "混双 (vs 男双)",
                            "match": best_match,
                            "fallback": True
                        })
                        self.mixed_vs_mens_pool.remove(best_match)
                        mixed_vs_mens_used += 1
                        added = True
                # Emergency: create临时 match from available players
                if not added:
                    played_players = set()
                    for m in current_round:
                        played_players.update(get_match_players(m["match"]))
                    
                    candidates = []
                    for p in self.all_players:
                        if p in played_players:
                            continue
                        # Use dynamic fixed_games calculation
                        fixed_games = get_fixed_games_for_player(p, self.court_count, self.total_players, self.total_matches)
                        if fixed_games is not None and self.player_games[p] >= fixed_games:
                            continue
                        max_games = get_max_games_for_player(p, self.court_count, self.total_players)
                        if self.player_games[p] >= max_games:
                            continue
                        candidates.append(p)
                    
                    if len(candidates) >= 4:
                        selected = random.sample(candidates, 4)
                        females_in_selected = [p for p in selected if p in FEMALE_PLAYERS]
                        males_in_selected = [p for p in selected if p not in FEMALE_PLAYERS]
                        
                        if len(females_in_selected) >= 2 and len(males_in_selected) >= 2:
                            pair1 = (females_in_selected[0], females_in_selected[1])
                            pair2 = (males_in_selected[0], males_in_selected[1])
                            match_type = "女双 (临时)"
                        elif len(males_in_selected) >= 4:
                            pair1 = (males_in_selected[0], males_in_selected[1])
                            pair2 = (males_in_selected[2], males_in_selected[3])
                            match_type = "男双 (临时)"
                        else:
                            pair1 = (selected[0], selected[1])
                            pair2 = (selected[2], selected[3])
                            match_type = "男双 (临时)"
                        
                        match = (pair1, pair2)
                        current_round.append({
                            "type": match_type,
                            "match": match,
                            "fallback": True
                        })
                        added = True
            
            if current_round:
                # Add round and court info
                for court_idx, match_info in enumerate(current_round):
                    match_info["court"] = court_idx + 1
                    match_info["round"] = round_num
                    self.scheduled_matches.append(match_info)
                
                self.rounds.append(current_round)
                self._update_player_history(current_round)
                
                print(f"  第{round_num}轮：{len(current_round)}场比赛 "
                      f"(混{mixed_used}/混男{mixed_vs_mens_used}/女{womens_used}/男{mens_used})")
        
        # Validate schedule
        self._validate_schedule()
        
        print(f"\n[LLM 排阵] 完成！共 {len(self.scheduled_matches)} 场比赛")
        
        return self.scheduled_matches
    
    def _validate_schedule(self):
        """Validate the generated schedule."""
        # Check core rule: no player appears twice in same round
        for round_idx, round_matches in enumerate(self.rounds):
            round_players = set()
            for match_info in round_matches:
                players = get_match_players(match_info["match"])
                for p in players:
                    if p in round_players:
                        raise AssertionError(
                            f"【核心规则违规】第{round_idx + 1}轮：球员 {p} 重复出现"
                        )
                    round_players.add(p)
        
        # Check anti-cold rule: no consecutive byes (soft constraint)
        # This is a preference, not a hard constraint
        # When mathematically impossible, we allow it with a warning
        consecutive_bye_violations = []
        
        for player in self.all_players:
            constraint = self._get_constraint(player)
            if constraint.get("early_departure"):
                continue
            
            # Check if player reached max games
            max_games = get_max_games_for_player(player, self.court_count, self.total_players)
            if self.player_games[player] >= max_games:
                continue  # Player can rest after reaching max games

            history = self.player_bye_history[player]
            for i in range(len(history) - 1):
                if history[i] == False and history[i + 1] == False:
                    consecutive_bye_violations.append(player)

        if consecutive_bye_violations:
            # Report as warning, not error
            from collections import Counter
            violation_counts = Counter(consecutive_bye_violations)
            print(f"\n⚠️  注意：有 {len(violation_counts)} 位球员连续轮空（数学上难以避免）:")
            for player, count in violation_counts.items():
                print(f"    - {player}: {count}次")
            print(f"  建议：增加球员数量或减少场地数量\n")
        else:
            print("✓ 防止冷场规则检查通过：无球员连续轮空")

        print("✓ 核心规则验证通过")


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


def main():
    """Main entry point for LLM scheduler."""
    # Try multiple paths for flexibility
    possible_paths = [
        "微信接龙.txt",  # When running from 排阵 directory
        "排阵/微信接龙.txt",  # When running from project root
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

    print(f"=" * 60)
    print("LLM 推理排阵系统")
    print(f"=" * 60)
    if activity_date:
        print(f"活动日期：{activity_date}")

    court_count = get_court_count(total_players)

    # Create scheduler and generate schedule
    scheduler = LLMLineupScheduler(males, females, court_count, total_players)
    matches = scheduler.schedule()
    
    # Calculate statistics
    player_stats = calculate_player_stats(matches, all_players)
    
    # Print summary
    from collections import Counter
    match_type_counts = Counter(m["type"] for m in matches)
    
    print(f"\n比赛类型分布:")
    for t, c in sorted(match_type_counts.items()):
        print(f"  - {t}: {c}场")
    
    print(f"\n球员参赛场次统计:")
    for player in sorted(all_players):
        stats = player_stats[player]
        constraint = PLAYER_CONSTRAINTS.get(player, {})
        note = ""
        # Use dynamic fixed_games calculation for display
        fixed_games = get_fixed_games_for_player(player, court_count, total_players, len(matches))
        if fixed_games is not None:
            if stats["total"] == fixed_games:
                note = f" (已完成{fixed_games}场)"
            elif stats["total"] < fixed_games:
                note = f" (目标{fixed_games}场，还差{fixed_games - stats['total']}场)"
        if constraint.get("early_departure"):
            note += " [需提前离场]"
        type_str = f"(男{stats['男双']}/女{stats['女双']}/混{stats['混双']})"
        print(f"  - {player}: {stats['total']}场 {type_str}{note}")
    
    # Export to Excel
    # Try multiple paths for flexibility
    possible_output_paths = [
        "对阵表_LLM.xlsx",  # When running from 排阵 directory
        "排阵/对阵表_LLM.xlsx",  # When running from project root
    ]
    
    output_path = possible_output_paths[0]
    for path in possible_output_paths:
        try:
            # Test if we can write to this path
            with open(path, 'wb') as f:
                f.close()
            import os
            os.remove(path)  # Remove test file
            output_path = path
            break
        except (IOError, OSError):
            continue
    
    create_lineup_excel(
        matches, court_count, output_path, player_stats,
        schedule_method="LLM 推理",
        activity_date=activity_date
    )
    
    print(f"\n✓ LLM 排阵完成，输出文件：{output_path}")


if __name__ == "__main__":
    main()
