#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 2026-10-12 实例 + lineup JSON（争位战版），供 export_lineup 校验/导出 Excel"""
import json, sys, importlib.util
from pathlib import Path

BASE = Path("/Users/yanyongwen712/Codes/pingan_tech_badminton_team/排阵")
sol = BASE / "大模型排阵"

# ---------- 1. 复用 builder 的对阵表 ----------
spec = importlib.util.spec_from_file_location("b1210", BASE / "2026-10-12_builder.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
ROUNDS, COURTS = mod.ROUNDS, mod.COURTS

# ---------- 2. lineup JSON ----------
rounds_out = []
for r in range(1, 8):
    matches = []
    for i, (typ, a, b) in enumerate(ROUNDS[r]):
        matches.append({"court": COURTS[i], "type": typ, "a": a, "b": b})
    rounds_out.append({"round": r, "matches": matches})

lineup = {
    "title": "工会杯备战训练 2026-10-12（5人男双大循环 + 林锋只混双·混v男对抗 + 罗范单打后置）",
    "date": "2026-10-12",
    "courts": COURTS,
    "caps": {"internal": 6, "guest": 6},
    "design_notes": {
        "目标": "5人男双大循环(刘继宇/罗琴荩/严勇文/范智强/王苏丹)选出男双二候选名单 + 罗琴荩vs范智强单打后置 + 刘继宇vs王小波混双男二PK",
        "男双循环": "5人双打大循环：严罗vs刘范 / 严刘vs罗王 / 严范vs刘王 / 刘罗vs范王 / 严王vs罗范（10种配对各1次，每人循环4场，各轮休1次）",
        "林锋定编": "林锋θ=3.56内部第一，主打混双（R2混v男/R3混双/R6混v男/R7混双），搭档=正赛混双女（唐英武今晚不在→用徐越，内部现役组合强度第一）；R1 用户指定加一场强档男双：黄冬青+林锋 PK 大哲+财贵（检验锚点）",
        "混v男": "林锋+徐越 打【相对弱的男双组合】：R6 vs 王小波+陈小洪（用户指定王波替严勇文多打一局）、R7 vs 陈小洪+张欣欣、R2 王波+徐越 vs 陈小洪+张欣欣（王波多一场混')。王波+陈小洪同队为本次用户指定例外（原约永不同队）",
        "男双二判定": "看5人循环+参照对苏陈/黄张战绩，定男双二（数据推荐 严罗70%，刘继宇要求实战定夺）",
        "男单": "罗琴荩 vs 范智强（R7 后置，循环打完再打，保体力）",
        "混双PK": "刘继宇+徐越 vs 王小波+李祺（R5，混双男二之争）",
        "王苏丹": "男双循环4场+混双1场（R1）；高洁/林小连 只打女双",
        "女双主力": "李佳琳+林小连（工会杯首选）为主；4场女双轮转配对：R2主力 林vs佳琳・R4李佳琳换配高洁・R6李佳琳换配李祺・R7主力收官，每人跟另外3人都配过一遍；高洁伤后不打主力但全面轮转",
        "能量": "总能量84（17人），极差2=无3！分布：6×4(罗/范=男单固有、徐越/李佳琳=混女双主力) + 5×8(含王波5=用户指定多打一局、R6混v男替严勇文) + 4×5(严勇文/张欣欣/林小连/林锋/高洁)。极差1无法实现(罗范单打能量×2固定6、只女双/只混双岗位封顶4)；2已是结构最优",
        "外援规则": "无外援PK外援；黄冬青+张欣欣 为强男双参考对手",
    },
    "rounds": rounds_out,
}

lineup_path = sol / "2026-10-12-lineup.json"
json.dump(lineup, open(lineup_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("✓ lineup:", lineup_path)

# ---------- 3. 周实例 JSON ----------
inst = {
    "_note": "手工争位战版：5人男双大循环(刘罗严范王)选男双二 + 罗范男单后置R7 + 刘王混双PK R5 + 林锋只混双(配徐越)含2场混v男对抗弱男双 + 王苏丹混双R1；高洁只女双。名单17人3场地。手工对阵，非求解器产物。",
    "date": "2026-10-12",
    "title": "工会杯备战训练 2026-10-12（5人男双大循环 + 林锋只混双·混v男对抗 + 罗范单打后置）",
    "courts": [8, 17, 18],
    "rounds_count": 7,
    "roster": {
        "internal_male": ["苏大哲", "严勇文", "范智强", "王苏丹", "罗琴荩", "陈小洪", "刘继宇", "王小波", "林锋", "陈财贵"],
        "female": ["林小连", "李祺祺", "高洁", "徐越", "李佳琳"],
        "guest": ["张欣欣", "黄冬青"]
    },
    "roles": {
        "anchors": [["苏大哲", "陈财贵"]],
        "seeds": [],
        "ms_pair": [],
        "ws_pair": [],
        "xl_anchor": "",
        "xl_partner": [],
        "sc_opp_pool": [],
        "xd_women": ["李祺祺", "徐越"],
        "wd_sides": {},
        "ms_opp_internal": [],
        "xd_prefer": ["林锋", "刘继宇", "王小波", "严勇文", "罗琴荩", "陈小洪"]
    },
    "structure": {
        "sc_rounds": [1, 3, 4, 5, 6],
        "xl_rounds": [],
        "duel_rounds": [],
        "reshuffle_rounds": [],
        "reshuffle_teams": [],
        "rounds": {
            "1": {"ms": False, "ws": False, "xd": True, "wd": False, "om": False},
            "2": {"ms": False, "ws": False, "xd": True, "wd": True, "om": False},
            "3": {"ms": False, "ws": False, "xd": True, "wd": False, "om": False},
            "4": {"ms": False, "ws": False, "xd": False, "wd": True, "om": False},
            "5": {"ms": False, "ws": False, "xd": True, "wd": False, "om": False},
            "6": {"ms": False, "ws": False, "xd": True, "wd": True, "om": False},
            "7": {"ms": True, "ws": False, "xd": True, "wd": True, "om": False}
        }
    },
    "preferences": {
        "ms_opp_order": {},
        "xd_order": {"林锋": 0},
        "ms_opp_cap": 2
    },
    "limits": {
        "cap": 6,
        "min_cap": 3,
        "caps": {"internal": 6, "guest": 6},
        "spread_max": 2
    },
    "goals": {
        "anchor_pair_min": [{"pair": ["苏大哲", "陈财贵"], "min": 3}],
        "xd_min": [{"player": "林锋", "min": 1}],
        "ws_count": 0,
        "seed_ms_min": 0
    },
    "pairs": [],
    "max_pairs": [
        {"pair": ["王小波", "陈小洪"], "max": 1}
    ]
}
inst_path = sol / "instances" / "2026-10-12.json"
json.dump(inst, open(inst_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("✓ instance:", inst_path)
