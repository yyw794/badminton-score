#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""2026-10-12 对阵表 v11（均衡加强版）：极差=2，消灭所有3
目标能量分布：6×4(罗/范/徐越/李佳琳) + 5×8 + 4×5(王波/林小连/高洁/张欣欣/林锋)
结构：5人男双大循环 + 男单后置 + 王波4场混'(含混v男) + 女双4场(李佳琳+林小连主力)
约束：王小波只混双；严勇文不打混双；林小连/高洁只女双；王苏丹男双+混双都打"""
from collections import defaultdict

MALE_I = {"苏大哲","陈财贵","严勇文","罗琴荩","刘继宇","王小波","林锋","范智强","王苏丹","陈小洪"}
MALE_F = {"黄冬青","张欣欣"}
FEM_I = {"林小连","李祺祺","高洁","徐越","李佳琳"}
COURTS = [8, 17, 18]
FOREIGN = MALE_F

ROUNDS = {
    1: [
        ("男双", ["严勇文","罗琴荩"], ["刘继宇","范智强"]),   # PK1 严罗 vs 刘范 (王苏丹轮休)
        ("男双", ["苏大哲","陈财贵"], ["黄冬青","林锋"]),     # 用户指定：黄林 vs 苏陈锚点
        ("混双", ["王苏丹","徐越"], ["王小波","李佳琳"]),
    ],
    2: [
        ("男双", ["严勇文","刘继宇"], ["罗琴荩","王苏丹"]),   # PK2 严刘 vs 罗王 (范智强轮休)
        ("混v男", ["王小波","徐越"], ["陈小洪","张欣欣"]),    # 王波第4场混'(混双vs男双)
        ("女双", ["李佳琳","林小连"], ["高洁","李祺祺"]),
    ],
    3: [
        ("男双", ["严勇文","范智强"], ["刘继宇","王苏丹"]),   # PK3 严范 vs 刘王 (罗琴荩轮休)
        ("混双", ["林锋","徐越"], ["王小波","李佳琳"]),       # 林锋正赛模拟
        ("男双", ["苏大哲","陈财贵"], ["陈小洪","黄冬青"]),
    ],
    4: [
        ("男双", ["刘继宇","罗琴荩"], ["范智强","王苏丹"]),   # PK4 刘罗 vs 范王 (严勇文轮休)
        ("男双", ["苏大哲","陈财贵"], ["陈小洪","黄冬青"]),
        ("女双", ["李佳琳","高洁"], ["林小连","李祺祺"]),     # 女双轮转1：李佳琳换配高洁
    ],
    5: [
        ("男双", ["严勇文","王苏丹"], ["罗琴荩","范智强"]),   # PK5 严王 vs 罗范 (刘继宇轮休)
        ("混双", ["刘继宇","徐越"], ["王小波","李祺祺"]),     # 混双男二PK
        ("男双", ["苏大哲","陈财贵"], ["黄冬青","张欣欣"]),
    ],
    6: [
        ("混v男", ["林锋","徐越"], ["王小波","陈小洪"]),      # 用户指定：王波替严勇文，多打一局 (王波+陈小洪同队=本次例外)
        ("男双", ["苏大哲","陈财贵"], ["黄冬青","张欣欣"]),
        ("女双", ["李佳琳","李祺祺"], ["林小连","高洁"]),     # 女双轮转2：李佳琳换配李祺
    ],
    7: [
        ("男单", ["罗琴荩"], ["范智强"]),                    # 男单后置（PK完再打，保体力）
        ("混v男", ["林锋","徐越"], ["陈小洪","张欣欣"]),      # 林锋 vs 弱男双
        ("女双", ["李佳琳","林小连"], ["高洁","李祺祺"]),
    ],
}

def is_female(p): return p in FEM_I
def is_male(p): return p in MALE_I or p in MALE_F

errors = []
energy = defaultdict(int)
type_count = defaultdict(int)

for r in range(1, 8):
    ms = ROUNDS[r]
    assert len(ms) == 3, f"R{r} 不是3场"
    players_round = set()
    for i, (typ, a, b) in enumerate(ms):
        for p in a + b:
            if p in players_round:
                errors.append(f"R{r} 第{i+1}场 {p} 重复")
            players_round.add(p)
        if typ == "男双":
            if not (len(a)==2 and len(b)==2 and all(is_male(p) for p in a+b)):
                errors.append(f"R{r}.{i+1} 男双性别错误")
        elif typ == "混双":
            ok = (len(a)==2 and len(b)==2 and is_male(a[0]) and is_female(a[1]) and is_male(b[0]) and is_female(b[1]))
            if not ok: errors.append(f"R{r}.{i+1} 混双结构错误: {a} vs {b}")
        elif typ == "混v男":
            ok = (len(a)==2 and is_male(a[0]) and is_female(a[1])
                  and len(b)==2 and all(is_male(p) for p in b))
            if not ok: errors.append(f"R{r}.{i+1} 混v男结构错误: {a} vs {b}")
        elif typ == "女双":
            if not (len(a)==2 and len(b)==2 and all(is_female(p) for p in a+b)):
                errors.append(f"R{r}.{i+1} 女双性别错误")
        elif typ == "男单":
            if not (len(a)==1 and len(b)==1 and is_male(a[0]) and is_male(b[0])):
                errors.append(f"R{r}.{i+1} 男单性别错误")
        fa = sum(1 for p in a if p in FOREIGN); fb = sum(1 for p in b if p in FOREIGN)
        if fa and fb: errors.append(f"R{r}.{i+1} 外援PK外援")
        for side in (a, b):
            if "王小波" in side and "陈小洪" in side and not (r == 6 and typ == "混v男"):
                # 例外：R6 混v男 用户指定 王波+陈小洪 对 林锋+徐越（王波多打一局）
                errors.append(f"R{r}.{i+1} 王小波+陈小洪同队")
        for p in a + b:
            if p in ("林小连","高洁") and typ != "女双": errors.append(f"R{r}.{i+1} {p}打了{typ}!")
            if p == "王小波" and typ == "男双": errors.append(f"R{r}.{i+1} 王小波打了男双!")
            if p == "严勇文" and typ == "混双": errors.append(f"R{r}.{i+1} 严勇文打了混双!")
            if p == "林锋" and typ not in ("混双","混v男"):
                if not (r == 1 and typ == "男双" and "苏大哲" in a+b and "黄冬青" in a+b):
                    errors.append(f"R{r}.{i+1} 林锋只打混双却打了{typ}!")
        work = 2 if typ in ("男单","女单") else 1
        for p in a + b: energy[p] += work
        type_count[typ] += 1

print("=" * 58)
print("2026-10-12 对阵表 v11（均衡加强：极差2·消灭3）")
print("=" * 58)
for r in range(1, 8):
    print(f"--- 第{r}轮 ---")
    for i, (typ, a, b) in enumerate(ROUNDS[r]):
        print(f"  {COURTS[i]}号 [{typ}] {'/'.join(a)}  VS  {'/'.join(b)}")
print()
print("类型:", dict(type_count))
print("✗" if errors else "✓ 硬校验通过")
for e in errors: print("  -", e)
print()
print("能量分布:")
for p in sorted(energy, key=lambda x: (-energy[x], x)):
    print(f"  {p:<6} {energy[p]}")
v = list(energy.values())
print(f"极差 {max(v)-min(v)} (total={sum(v)})")
print()
pairs = set()
for r in range(1,8):
    for t,a,b in ROUNDS[r]:
        if t=='男双':
            for side in (a,b):
                if set(side) <= {'刘继宇','罗琴荩','严勇文','范智强','王苏丹'}:
                    pairs.add(frozenset(side))
print("5人循环出现组合:", sorted('/'.join(sorted(p)) for p in pairs), f"({len(pairs)}/10)")
