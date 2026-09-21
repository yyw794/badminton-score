#!/usr/bin/env python3
"""
周实例配置加载器 —— 把「每周会变的东西」从算法代码里剥离出来。

分层原则（重要）：
  算法层（solve_lineup.py 的回溯/剪枝/目标函数）= 通用、稳定，每周不动；
  实例层（instances/<date>.json）= 数据，每周从微信接龙更新。

周实例 JSON 包含五类信息：
  roster       本周接龙名单（内部男 / 女 / 外援）
  roles        角色指派（锚点对 / 单打种子 / 混双固定女 / 偏好池）
  structure    轮次结构（每轮 xd/ws/om/ms_seeds、sc/xl 锚点轮、内战轮）
  preferences  用户指定的优先级顺序
  limits/goals 场次上下限与训练目标

用法:
    from weekly import load
    w = load()                    # 自动取 instances/ 里日期最新的一份
    w = load("2026-09-14")        # 指定某一周
    w.non_anchor / w.foreign / w.rounds / ...

找不到实例文件时回退到内置 DEFAULT（当前周），保证系统不崩。
"""
import json
from dataclasses import dataclass, field
from pathlib import Path

BASE = Path(__file__).resolve().parent
INSTANCE_DIR = BASE / "instances"


@dataclass
class Week:
    date: str
    title: str
    courts: list
    rounds_count: int
    # 名单（接龙数据）
    internal_male: list
    female: list
    guest: list
    # 角色指派（策略层）
    anchors: list                 # [[p1, p2], ...]
    seeds: list
    ms_pair: list                 # 男单固定对战（如 范智强/罗琴荩）
    ws_pair: list                 # 女单固定对战（如 徐越/李祺祺）
    xd_women: list
    wd_sides: dict                # 女双vs混双 的女方分配（女双 / 混双侧）
    ms_opp_internal: list
    xd_prefer: list
    xl_anchor: str               # 第二男双固定成员（如 严勇文）
    xl_partner: list | None      # 第二男双搭档候选池（如 陈顺星/范智强/罗琴荩）
    sc_opp_pool: list | None     # 最强锚点(苏陈)对手候选池（硬：从这挑，尽量强）
    # 轮次结构
    sc_rounds: list
    xl_rounds: list
    duel_rounds: list
    reshuffle_rounds: list        # 重组轮：该轮锚点拆开重组（如 陈财贵+刘继宇 vs 苏大哲+严勇文）
    reshuffle_teams: list         # 重组轮的两队 [[p1,p2],[p3,p4]]
    rounds: dict                  # {1: {xd,ws,om,ms_seeds}, ...}
    # 偏好
    ms_opp_order: dict
    xd_order: dict
    ms_opp_cap: int
    # 上下限 / 训练目标
    cap: int
    min_cap: int
    caps: dict
    spread_max: int = 4          # 能量极差上限（结构不同，默认 4；旧 4场×16人 结构为 2）
    goals: dict = field(default_factory=dict)
    # 指定合练对（男双固定搭档，至少打 min 场）：[[[p1,p2],min], ...]
    pairs: list = field(default_factory=list)
    # 每人场次下限（覆盖 min_cap）：{p: n}
    mins: dict = field(default_factory=dict)
    # 同队上限（换搭档，如 陈小洪/卢志辉 同队≤2）：[[[p1,p2],max], ...]
    max_pairs: list = field(default_factory=list)

    # ---- 派生量（每周随名单自动重算，不用手填）----
    @property
    def foreign(self):
        return set(self.guest)

    @property
    def all_anchors(self):
        return {p for pair in self.anchors for p in pair}

    @property
    def non_anchor(self):
        """可被分配角色的球员 = 非锚点内部男 + 全部外援（与旧 NON_ANCHOR 一致）。"""
        return [m for m in self.internal_male if m not in self.all_anchors] + list(self.guest)

    @property
    def ms_opp_foreign(self):
        return set(self.guest)

    @property
    def ms_opp_pool(self):
        return self.ms_opp_foreign | set(self.ms_opp_internal)

    @property
    def anchor_pairs(self):
        return [tuple(p) for p in self.anchors]

    @property
    def pair_list(self):
        """指定合练对 → [(frozenset({p1,p2}), min), ...]，供求解器用。"""
        return [(frozenset(p["pair"]), int(p["min"])) for p in self.pairs]

    @property
    def max_pair_list(self):
        """同队上限（换搭档）→ [(frozenset({p1,p2}), max), ...]，供求解器用。"""
        return [(frozenset(p["pair"]), int(p["max"])) for p in self.max_pairs]

    @property
    def min_caps(self):
        """每人场次下限（mins 覆盖 min_cap），只对可分配池球员。"""
        return {p: self.mins.get(p, self.min_cap) for p in self.non_anchor}

    @property
    def reshuffle_set(self):
        return set(self.reshuffle_rounds)


def _from_dict(d):
    roster, roles, st, pref, lim, goals = (
        d["roster"], d["roles"], d["structure"], d["preferences"],
        d["limits"], d.get("goals", {}))
    return Week(
        date=d["date"],
        title=d["title"],
        courts=list(d["courts"]),
        rounds_count=int(d["rounds_count"]),
        internal_male=list(roster["internal_male"]),
        female=list(roster["female"]),
        guest=list(roster["guest"]),
        anchors=[list(p) for p in roles["anchors"]],
        seeds=list(roles["seeds"]),
        ms_pair=list(roles.get("ms_pair", [])),
        ws_pair=list(roles.get("ws_pair", (roles["xd_women"][0], roles["xd_women"][1]))),
        xd_women=list(roles["xd_women"]),
        wd_sides=dict(roles.get("wd_sides", {})),
        xl_anchor=str(roles.get("xl_anchor", "")),
        xl_partner=list(roles.get("xl_partner", [])) or None,
        sc_opp_pool=list(roles.get("sc_opp_pool", [])) or None,
        ms_opp_internal=list(roles["ms_opp_internal"]),
        xd_prefer=list(roles["xd_prefer"]),
        sc_rounds=list(st["sc_rounds"]),
        xl_rounds=list(st["xl_rounds"]),
        duel_rounds=list(st["duel_rounds"]),
        reshuffle_rounds=list(st.get("reshuffle_rounds", [])),
        reshuffle_teams=[list(t) for t in st.get("reshuffle_teams", [])],
        rounds={int(k): dict(v) for k, v in st["rounds"].items()},
        ms_opp_order=dict(pref["ms_opp_order"]),
        xd_order=dict(pref["xd_order"]),
        ms_opp_cap=int(pref["ms_opp_cap"]),
        cap=int(lim["cap"]),
        min_cap=int(lim["min_cap"]),
        caps=dict(lim["caps"]),
        spread_max=int(lim.get("spread_max", 4)),
        goals=goals,
        pairs=list(d.get("pairs", [])),
        mins=dict(lim.get("mins", {})),
        max_pairs=list(d.get("max_pairs", [])),
    )


def _latest_instance_path():
    files = sorted(INSTANCE_DIR.glob("*.json"))
    return files[-1] if files else None


def load(date=None):
    """读取周实例。date=None → instances/ 里日期最新的一份；都没有 → 内置 DEFAULT。"""
    if date is None:
        p = _latest_instance_path()
    else:
        p = INSTANCE_DIR / f"{date}.json"
    if p and p.exists():
        with open(p, encoding="utf-8") as f:
            return _from_dict(json.load(f))
    return _from_dict(json.loads(json.dumps(DEFAULT)))


# 内置回退（= 2026-09-14 周实例的内容）：instances/ 丢失时兜底，平时用不到
DEFAULT = {
    "date": "2026-09-14",
    "title": "工会杯备战训练 2026-09-14",
    "courts": [6, 8, 17, 18],
    "rounds_count": 7,
    "roster": {
        "internal_male": ["苏大哲", "严勇文", "陈顺星", "陈小洪", "卢志辉", "林锋",
                          "王小波", "刘继宇", "罗琴荩", "陈财贵", "范智强"],
        "female": ["李祺祺", "李佳琳"],
        "guest": ["程建兴", "罗蒙", "张欣欣"],
    },
    "roles": {
        "anchors": [["苏大哲", "陈财贵"], ["陈顺星", "刘继宇"]],
        "seeds": ["范智强", "罗琴荩"],
        "xd_women": ["李祺祺", "李佳琳"],
        "ms_opp_internal": ["严勇文", "陈小洪", "王小波"],
        "xd_prefer": ["林锋", "王小波", "严勇文", "陈小洪", "程建兴", "罗蒙"],
    },
    "structure": {
        "sc_rounds": [1, 2, 3, 4, 5, 6, 7],
        "xl_rounds": [1, 2, 3, 5, 6, 7],
        "duel_rounds": [1, 5],
        "rounds": {
            "1": {"xd": True, "ws": False, "om": False, "ms_seeds": ["范智强", "罗琴荩"]},
            "2": {"xd": False, "ws": True, "om": False, "ms_seeds": ["范智强"]},
            "3": {"xd": True, "ws": False, "om": False, "ms_seeds": ["罗琴荩"]},
            "4": {"xd": True, "ws": False, "om": False, "ms_seeds": ["范智强", "罗琴荩"]},
            "5": {"xd": True, "ws": False, "om": False, "ms_seeds": ["范智强", "罗琴荩"]},
            "6": {"xd": False, "ws": True, "om": True, "ms_seeds": []},
            "7": {"xd": True, "ws": False, "om": True, "ms_seeds": []},
        },
    },
    "preferences": {
        "ms_opp_order": {"程建兴": 0, "罗蒙": 1, "张欣欣": 2},
        "xd_order": {"林锋": 0, "王小波": 1},
        "ms_opp_cap": 2,
    },
    "limits": {"cap": 7, "min_cap": 4, "caps": {"internal": 7, "guest": 7}},
    "goals": {
        "anchor_pair_min": [
            {"pair": ["苏大哲", "陈财贵"], "min": 3},
            {"pair": ["陈顺星", "刘继宇"], "min": 2},
        ],
        "xd_min": [{"player": "林锋", "min": 4}],
        "ws_count": 2,
        "seed_ms_min": 3,
    },
}


if __name__ == "__main__":
    w = load()
    print(f"周实例: {w.date}（{w.title}）")
    print(f"  名单: 内部男{len(w.internal_male)} 女{len(w.female)} 外援{len(w.guest)} = "
          f"{len(w.internal_male) + len(w.female) + len(w.guest)} 人")
    print(f"  锚点: {w.anchor_pairs}")
    if w.pairs:
        print(f"  合练对: {[(list(p['pair']), p['min']) for p in w.pairs]}")
    print(f"  种子: {w.seeds}")
    if w.reshuffle_rounds and w.reshuffle_teams:
        t1, t2 = w.reshuffle_teams
        print(f"  重组轮: {w.reshuffle_rounds} → {'/'.join(t1)} vs {'/'.join(t2)}")
    if w.mins:
        print(f"  场次下限(mins): {w.mins}")
    if w.max_pairs:
        print(f"  同队上限: {[(list(p['pair']), p['max']) for p in w.max_pairs]}")
    print(f"  可分配池(非锚点): {w.non_anchor}")
    print(f"  内战轮: {w.duel_rounds}")
