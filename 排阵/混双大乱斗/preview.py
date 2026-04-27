#!/usr/bin/env python3
"""快速预览对阵表（不生成Excel）"""

from mixed_doubles_chaos import generate_mixed_doubles_matches, print_schedule_summary

# 示例数据
group_a_males = ["林锋", "王小波", "陈顺星", "罗琴荩", "苏大哲", "黄冬青"]
group_b_females = ["田茜", "李祺祺", "高洁", "滕菲", "崔倩男", "李杏芝"]

print("=" * 70)
print("混双大乱斗 - 对阵表预览")
print("=" * 70)
print(f"\nA组男队员: {', '.join(group_a_males)}")
print(f"B组女队员: {', '.join(group_b_females)}\n")

matches = generate_mixed_doubles_matches(
    group_a_males=group_a_males,
    group_b_females=group_b_females,
    court_count=2,
    mode="fair"  # 公平模式：每人6场
)

if matches:
    # 打印表格预览
    print(f"{'轮次':<6} {'场地':<8} {'类型':<6} {'对阵A':<25} {'对阵B':<25}")
    print("-" * 70)
    
    for m in matches[:10]:  # 显示前10场
        round_num = m['round']
        court = m['court']
        match_type = m['type']
        pair_a = f"{m['match'][0][0]}/{m['match'][0][1]}"
        pair_b = f"{m['match'][1][0]}/{m['match'][1][1]}"
        print(f"{round_num:<6} {court}号     {match_type:<6} {pair_a:<25} {pair_b:<25}")
    
    print(f"\n... 共 {len(matches)} 场比赛 ...\n")
    
    # 打印完整统计
    print_schedule_summary(matches)
