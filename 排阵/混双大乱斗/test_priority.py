#!/usr/bin/env python3
"""
测试崔倩男优先排阵效果
"""

from mixed_doubles_chaos import generate_mixed_doubles_matches

group_a_males = ["林锋", "王小波", "陈顺星", "罗琴荩", "苏大哲", "黄冬青"]
group_b_females = ["田茜", "李祺祺", "高洁", "滕菲", "崔倩男", "李杏芝"]

print("=" * 80)
print("测试1: 不使用优先排阵（普通模式）")
print("=" * 80)

matches_normal = generate_mixed_doubles_matches(
    group_a_males=group_a_males,
    group_b_females=group_b_females,
    court_count=2,
    mode="fair"
)

cui_rounds_normal = []
for m in matches_normal:
    match = m["match"]
    if "崔倩男" in match[0] or "崔倩男" in match[1]:
        cui_rounds_normal.append(m["round"])

print(f"\n崔倩男上场轮次: {sorted(set(cui_rounds_normal))}")
print(f"前6轮是否连续上场: {sorted(set(cui_rounds_normal)) == [1, 2, 3, 4, 5, 6]}")

print("\n" + "=" * 80)
print("测试2: 使用优先排阵（崔倩男优先）")
print("=" * 80)

matches_priority = generate_mixed_doubles_matches(
    group_a_males=group_a_males,
    group_b_females=group_b_females,
    court_count=2,
    mode="fair",
    priority_players=["崔倩男"]
)

cui_rounds_priority = []
for m in matches_priority:
    match = m["match"]
    if "崔倩男" in match[0] or "崔倩男" in match[1]:
        cui_rounds_priority.append(m["round"])

print(f"\n崔倩男上场轮次: {sorted(set(cui_rounds_priority))}")
print(f"前6轮是否连续上场: {sorted(set(cui_rounds_priority)) == [1, 2, 3, 4, 5, 6]}")

print("\n" + "=" * 80)
print("结论")
print("=" * 80)
if sorted(set(cui_rounds_priority)) == [1, 2, 3, 4, 5, 6]:
    print("✅ 优先排阵成功！崔倩男在前6轮连续上场，没有休息")
else:
    print("⚠️  优先排阵未完全达到预期")
