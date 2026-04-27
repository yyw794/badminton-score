#!/usr/bin/env python3
"""
混双大乱斗优先排阵功能测试
基于实际代码运行结果进行验证
"""

from mixed_doubles_chaos import generate_mixed_doubles_matches
import sys


def test_priority_player_continuous_play():
    """
    必须需求测试：优先排阵球员在前N轮连续上场（不休息）
    """
    print("=" * 80)
    print("测试1: 优先排阵球员连续上场（必须需求）")
    print("=" * 80)
    
    group_a_males = ["林锋", "王小波", "陈顺星", "罗琴荩", "苏大哲", "黄冬青"]
    group_b_females = ["田茜", "李祺祺", "高洁", "滕菲", "崔倩男", "李杏芝"]
    
    matches = generate_mixed_doubles_matches(
        group_a_males=group_a_males,
        group_b_females=group_b_females,
        court_count=2,
        mode="fair",
        priority_players=["崔倩男"]
    )
    
    # 统计崔倩男在哪些轮次上场
    cui_rounds = []
    for m in matches:
        match = m["match"]
        if "崔倩男" in match[0] or "崔倩男" in match[1]:
            cui_rounds.append(m["round"])
    
    cui_rounds_unique = sorted(set(cui_rounds))
    total_games = len(cui_rounds)
    
    print(f"\n崔倩男上场轮次: {cui_rounds_unique}")
    print(f"崔倩男总场次: {total_games}")
    
    # 必须需求：前6轮连续上场
    expected_rounds = [1, 2, 3, 4, 5, 6]
    is_continuous = cui_rounds_unique == expected_rounds
    
    print(f"\n期望轮次: {expected_rounds}")
    print(f"实际轮次: {cui_rounds_unique}")
    print(f"是否连续上场: {is_continuous}")
    
    if is_continuous:
        print("✅ 测试通过：崔倩男在前6轮连续上场，没有休息")
        return True
    else:
        print("❌ 测试失败：崔倩男未能在前6轮连续上场")
        print(f"   缺少的轮次: {set(expected_rounds) - set(cui_rounds_unique)}")
        return False


def test_priority_player_total_games():
    """
    必须需求测试：优先排阵球员总场次与其他人相同
    """
    print("\n" + "=" * 80)
    print("测试2: 优先排阵球员总场次均衡（必须需求）")
    print("=" * 80)
    
    group_a_males = ["林锋", "王小波", "陈顺星", "罗琴荩", "苏大哲", "黄冬青"]
    group_b_females = ["田茜", "李祺祺", "高洁", "滕菲", "崔倩男", "李杏芝"]
    
    matches = generate_mixed_doubles_matches(
        group_a_males=group_a_males,
        group_b_females=group_b_females,
        court_count=2,
        mode="fair",
        priority_players=["崔倩男"]
    )
    
    # 统计每个球员的参赛次数
    player_games = {}
    for m in matches:
        match = m["match"]
        for player in match[0] + match[1]:
            player_games[player] = player_games.get(player, 0) + 1
    
    # 获取崔倩男的场次
    cui_games = player_games.get("崔倩男", 0)
    
    # 获取所有人的场次
    all_games = list(player_games.values())
    expected_games = all_games[0] if all_games else 0
    
    print(f"\n球员参赛统计:")
    for player, games in sorted(player_games.items(), key=lambda x: -x[1]):
        marker = " <-- 优先球员" if player == "崔倩男" else ""
        print(f"  {player}: {games}场{marker}")
    
    # 必须需求：所有人场次相同
    all_equal = len(set(all_games)) == 1
    cui_equals_others = cui_games == expected_games
    
    print(f"\n期望每人场次: {expected_games}")
    print(f"崔倩男场次: {cui_games}")
    print(f"所有人场次相同: {all_equal}")
    print(f"崔倩男场次与他人相同: {cui_equals_others}")
    
    if all_equal and cui_equals_others:
        print("✅ 测试通过：所有球员场次均衡，崔倩男场次与他人相同")
        return True
    else:
        print("❌ 测试失败：球员场次不均衡")
        return False


def test_no_duplicate_in_same_round():
    """
    必须需求测试：同一轮次中球员不重复
    """
    print("\n" + "=" * 80)
    print("测试3: 同一轮次球员不重复（必须需求）")
    print("=" * 80)
    
    group_a_males = ["林锋", "王小波", "陈顺星", "罗琴荩", "苏大哲", "黄冬青"]
    group_b_females = ["田茜", "李祺祺", "高洁", "滕菲", "崔倩男", "李杏芝"]
    
    matches = generate_mixed_doubles_matches(
        group_a_males=group_a_males,
        group_b_females=group_b_females,
        court_count=2,
        mode="fair",
        priority_players=["崔倩男"]
    )
    
    # 按轮次分组
    rounds_dict = {}
    for m in matches:
        round_num = m["round"]
        if round_num not in rounds_dict:
            rounds_dict[round_num] = []
        rounds_dict[round_num].append(m)
    
    validation_passed = True
    duplicate_info = []
    
    for round_num, round_matches in sorted(rounds_dict.items()):
        round_players = set()
        for m in round_matches:
            players = set(m["match"][0] + m["match"][1])
            overlap = round_players & players
            if overlap:
                validation_passed = False
                duplicate_info.append((round_num, overlap))
            round_players.update(players)
    
    print(f"\n总轮数: {len(rounds_dict)}")
    print(f"总场次: {len(matches)}")
    
    if validation_passed:
        print("✅ 测试通过：所有轮次均无球员重复")
        return True
    else:
        print("❌ 测试失败：发现球员重复")
        for round_num, players in duplicate_info:
            print(f"   第{round_num}轮重复球员: {players}")
        return False


def test_rest_one_round_must_play():
    """
    必须需求测试：休息一轮后必须上场
    验证：如果某球员在第N轮休息，那么第N+1轮必须上场（除非已经打满6场）
    """
    print("\n" + "=" * 80)
    print("测试4: 休息一轮后必须上场（必须需求）")
    print("=" * 80)
    
    group_a_males = ["林锋", "王小波", "陈顺星", "罗琴荩", "苏大哲", "黄冬青"]
    group_b_females = ["田茜", "李祺祺", "高洁", "滕菲", "崔倩男", "李杏芝"]
    
    matches = generate_mixed_doubles_matches(
        group_a_males=group_a_males,
        group_b_females=group_b_females,
        court_count=2,
        mode="fair",
        priority_players=["崔倩男"]
    )
    
    # 按轮次分组，记录每轮上场的球员
    rounds_dict = {}
    for m in matches:
        round_num = m["round"]
        if round_num not in rounds_dict:
            rounds_dict[round_num] = set()
        match = m["match"]
        for player in match[0] + match[1]:
            rounds_dict[round_num].add(player)
    
    # 统计每个球员的参赛次数（用于判断是否已满6场）
    player_games = {}
    for m in matches:
        match = m["match"]
        for player in match[0] + match[1]:
            player_games[player] = player_games.get(player, 0) + 1
    
    all_players = set(group_a_males + group_b_females)
    max_rounds = max(rounds_dict.keys())
    
    violations = []  # 记录违规情况
    
    # 检查每一轮休息的球员，下一轮是否上场
    for round_num in range(1, max_rounds):
        if round_num not in rounds_dict or (round_num + 1) not in rounds_dict:
            continue
        
        current_round_players = rounds_dict[round_num]
        next_round_players = rounds_dict[round_num + 1]
        
        # 找出当前轮休息的球员
        rested_players = all_players - current_round_players
        
        # 检查这些休息的球员在下一轮是否上场（除非已满6场）
        for player in rested_players:
            # 如果该球员还没打满6场，下一轮必须上场
            if player_games.get(player, 0) < 6:
                if player not in next_round_players:
                    violations.append({
                        "player": player,
                        "rested_round": round_num,
                        "should_play_round": round_num + 1,
                        "current_games": player_games.get(player, 0)
                    })
    
    print(f"\n总轮数: {max_rounds}")
    print(f"总球员数: {len(all_players)}")
    print(f"违规次数: {len(violations)}")
    
    if violations:
        print("\n发现的违规情况（休息一轮后未上场）:")
        for v in violations[:10]:  # 最多显示10条
            print(f"  - {v['player']}: 第{v['rested_round']}轮休息，第{v['should_play_round']}轮未上场 "
                  f"(已打{v['current_games']}场)")
        if len(violations) > 10:
            print(f"  ... 还有 {len(violations) - 10} 条违规")
    
    if len(violations) == 0:
        print("✅ 测试通过：所有休息一轮的球员（未满6场）在下一轮都上场了")
        return True
    else:
        print(f"❌ 测试失败：发现 {len(violations)} 次违规")
        return False


def test_priority_vs_normal_comparison():
    """
    可选需求测试：对比优先排阵与普通模式的差异
    """
    print("\n" + "=" * 80)
    print("测试5: 优先排阵 vs 普通模式对比（可选需求）")
    print("=" * 80)
    
    group_a_males = ["林锋", "王小波", "陈顺星", "罗琴荩", "苏大哲", "黄冬青"]
    group_b_females = ["田茜", "李祺祺", "高洁", "滕菲", "崔倩男", "李杏芝"]
    
    # 普通模式
    matches_normal = generate_mixed_doubles_matches(
        group_a_males=group_a_males,
        group_b_females=group_b_females,
        court_count=2,
        mode="fair"
    )
    
    # 优先模式
    matches_priority = generate_mixed_doubles_matches(
        group_a_males=group_a_males,
        group_b_females=group_b_females,
        court_count=2,
        mode="fair",
        priority_players=["崔倩男"]
    )
    
    # 统计崔倩男的上场轮次
    def get_player_rounds(matches, player_name):
        rounds = []
        for m in matches:
            match = m["match"]
            if player_name in match[0] or player_name in match[1]:
                rounds.append(m["round"])
        return sorted(set(rounds))
    
    cui_rounds_normal = get_player_rounds(matches_normal, "崔倩男")
    cui_rounds_priority = get_player_rounds(matches_priority, "崔倩男")
    
    print(f"\n普通模式 - 崔倩男上场轮次: {cui_rounds_normal}")
    print(f"优先模式 - 崔倩男上场轮次: {cui_rounds_priority}")
    
    # 检查优先模式是否更早开始上场
    starts_earlier = min(cui_rounds_priority) <= min(cui_rounds_normal)
    # 检查优先模式前几轮是否连续
    is_continuous_priority = cui_rounds_priority == list(range(1, len(cui_rounds_priority) + 1))
    
    print(f"\n对比分析:")
    print(f"  优先模式是否更早开始: {starts_earlier} (优先:{min(cui_rounds_priority)}, 普通:{min(cui_rounds_normal)})")
    print(f"  优先模式前N轮连续: {is_continuous_priority}")
    
    if starts_earlier and is_continuous_priority:
        print("\n✅ 优先排阵效果明显：崔倩男更早开始且连续上场")
    else:
        print("\n⚠️  优先排阵效果不明显或未达到预期")
    
    return True  # 这是可选需求，总是返回True


def test_multiple_priority_players():
    """
    可选需求测试：多个球员同时优先排阵
    """
    print("\n" + "=" * 80)
    print("测试6: 多个球员同时优先排阵（可选需求）")
    print("=" * 80)
    
    group_a_males = ["林锋", "王小波", "陈顺星", "罗琴荩", "苏大哲", "黄冬青"]
    group_b_females = ["田茜", "李祺祺", "高洁", "滕菲", "崔倩男", "李杏芝"]
    
    matches = generate_mixed_doubles_matches(
        group_a_males=group_a_males,
        group_b_females=group_b_females,
        court_count=2,
        mode="fair",
        priority_players=["崔倩男", "李杏芝"]
    )
    
    # 统计两个优先球员的上场轮次
    def get_player_rounds(matches, player_name):
        rounds = []
        for m in matches:
            match = m["match"]
            if player_name in match[0] or player_name in match[1]:
                rounds.append(m["round"])
        return sorted(set(rounds))
    
    cui_rounds = get_player_rounds(matches, "崔倩男")
    li_rounds = get_player_rounds(matches, "李杏芝")
    
    print(f"\n崔倩男上场轮次: {cui_rounds}")
    print(f"李杏芝上场轮次: {li_rounds}")
    
    # 检查是否都在前面的轮次上场
    cui_starts_early = min(cui_rounds) <= 2
    li_starts_early = min(li_rounds) <= 2
    
    print(f"\n分析:")
    print(f"  崔倩男是否早期上场: {cui_starts_early} (最早第{min(cui_rounds)}轮)")
    print(f"  李杏芝是否早期上场: {li_starts_early} (最早第{min(li_rounds)}轮)")
    
    if cui_starts_early and li_starts_early:
        print("\n✅ 多个优先球员都能早期上场")
    else:
        print("\n⚠️  部分优先球员未能早期上场")
    
    return True  # 这是可选需求


def test_match_validity():
    """
    必须需求测试：每场比赛的配对有效性（无相同男队员或女队员）
    """
    print("\n" + "=" * 80)
    print("测试7: 比赛配对有效性（必须需求）")
    print("=" * 80)
    
    group_a_males = ["林锋", "王小波", "陈顺星", "罗琴荩", "苏大哲", "黄冬青"]
    group_b_females = ["田茜", "李祺祺", "高洁", "滕菲", "崔倩男", "李杏芝"]
    
    matches = generate_mixed_doubles_matches(
        group_a_males=group_a_males,
        group_b_females=group_b_females,
        court_count=2,
        mode="fair",
        priority_players=["崔倩男"]
    )
    
    invalid_matches = []
    
    for idx, m in enumerate(matches):
        match = m["match"]
        male1, female1 = match[0]
        male2, female2 = match[1]
        
        # 检查是否有相同的男队员或女队员
        if male1 == male2 or female1 == female2:
            invalid_matches.append({
                "index": idx + 1,
                "round": m["round"],
                "court": m["court"],
                "match": match,
                "reason": f"男队员相同:{male1}" if male1 == male2 else f"女队员相同:{female1}"
            })
    
    print(f"\n总比赛场次: {len(matches)}")
    print(f"无效比赛数量: {len(invalid_matches)}")
    
    if invalid_matches:
        print("\n发现的无效比赛:")
        for inv in invalid_matches:
            print(f"  第{inv['round']}轮 {inv['court']}号场地: {inv['match']} - {inv['reason']}")
    
    if len(invalid_matches) == 0:
        print("✅ 测试通过：所有比赛配对有效，无相同男队员或女队员")
        return True
    else:
        print("❌ 测试失败：发现无效的比赛配对")
        return False


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 80)
    print("混双大乱斗优先排阵功能 - 完整测试套件")
    print("=" * 80)
    
    results = {
        "必须需求": [],
        "可选需求": []
    }
    
    # 必须需求测试
    print("\n【必须需求测试】\n")
    
    test1 = test_priority_player_continuous_play()
    results["必须需求"].append(("优先球员连续上场", test1))
    
    test2 = test_priority_player_total_games()
    results["必须需求"].append(("优先球员场次均衡", test2))
    
    test3 = test_no_duplicate_in_same_round()
    results["必须需求"].append(("同轮次无重复球员", test3))
    
    test4 = test_rest_one_round_must_play()
    results["必须需求"].append(("休息一轮后必须上场", test4))
    
    test7 = test_match_validity()
    results["必须需求"].append(("比赛配对有效性", test7))
    
    # 可选需求测试
    print("\n【可选需求测试】\n")
    
    test5 = test_priority_vs_normal_comparison()
    results["可选需求"].append(("优先vs普通对比", test5))
    
    test6 = test_multiple_priority_players()
    results["可选需求"].append(("多球员优先排阵", test6))
    
    # 汇总结果
    print("\n" + "=" * 80)
    print("测试结果汇总")
    print("=" * 80)
    
    print("\n【必须需求】")
    must_pass_count = 0
    must_total = len(results["必须需求"])
    for name, passed in results["必须需求"]:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {status} - {name}")
        if passed:
            must_pass_count += 1
    
    print(f"\n必须需求通过率: {must_pass_count}/{must_total}")
    
    print("\n【可选需求】")
    for name, _ in results["可选需求"]:
        print(f"  ℹ️  已执行 - {name} (输出见上方)")
    
    print("\n" + "=" * 80)
    
    # 最终判断
    if must_pass_count == must_total:
        print("🎉 所有必须需求测试通过！")
        print("=" * 80)
        return 0
    else:
        print(f"⚠️  有 {must_total - must_pass_count} 个必须需求测试失败")
        print("=" * 80)
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
