#!/usr/bin/env python3
"""
sync_roster.py —— 把 微信接龙.txt 转成本周周实例（instances/<date>.json）。

每周流程：
  1. 你把报名名单更新到 微信接龙.txt
  2. 运行本脚本：自动按共享名单分类（内部男/女/外援），沿用上周实例的
     角色/结构/偏好/上下限/目标/合练对，写出新实例。
  3. 脚本会预警：锚点/种子/混双女/合练对成员 若不在本周名单 → 需要你定策略。
  4. 再跑 weekly.py → solve_lineup.py → export_lineup.py。

用法：
  .venv/bin/python 排阵/大模型排阵/sync_roster.py            # 用最新实例做模板
  .venv/bin/python 排阵/大模型排阵/sync_roster.py 2026-09-14  # 指定基于哪一周模板
  .venv/bin/python 排阵/大模型排阵/sync_roster.py --dry-run    # 只打印不写文件
"""
import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE.parent))          # 排阵/  → excel_exporter
import weekly                                 # noqa: E402
from excel_exporter import (                  # noqa: E402
    INTERNAL_MALE_PLAYERS, GUEST_MALE_PLAYERS,
    INTERNAL_FEMALE_PLAYERS, GUEST_FEMALE_PLAYERS,
)

SIGNUP_FILE = BASE / "微信接龙.txt"
INTERNAL_M = set(INTERNAL_MALE_PLAYERS)
GUEST_M = set(GUEST_MALE_PLAYERS)
INTERNAL_F = set(INTERNAL_FEMALE_PLAYERS)
GUEST_F = set(GUEST_FEMALE_PLAYERS)


def parse_signup(text):
    """从接龙文本解析 (date, [names])。date 取首个 YYYYMMDD，names 取 'N. 姓名'。"""
    date = ""
    m = re.search(r"(\d{4})(\d{2})(\d{2})", text)
    if m:
        date = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    names = []
    for line in text.splitlines():
        mm = re.match(r"^\s*\d+\s*[\.、]\s*([^\s]+)", line)
        if mm:
            names.append(mm.group(1).strip())
    return date, names


def classify(names):
    internal_male, female, guest, unknown, guest_female = [], [], [], [], []
    for n in names:
        if n in INTERNAL_M:
            internal_male.append(n)
        elif n in GUEST_M:
            guest.append(n)
        elif n in INTERNAL_F:
            female.append(n)
        elif n in GUEST_F:
            guest_female.append(n)
        else:
            unknown.append(n)
    return internal_male, female, guest, unknown, guest_female


def build_instance(date, internal_male, female, guest, template):
    """以 template（上一周实例 dict）为基础，替换 roster，写出新实例 dict。"""
    t = json.loads(json.dumps(template))   # deep copy
    t["date"] = date
    t["roster"] = {
        "internal_male": internal_male,
        "female": female,
        "guest": guest,
    }
    return t


def main():
    dry_run = "--dry-run" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    template_date = args[0] if args else None

    if not SIGNUP_FILE.exists():
        print(f"找不到 {SIGNUP_FILE}")
        sys.exit(1)
    date, names = parse_signup(SIGNUP_FILE.read_text(encoding="utf-8"))
    if not date:
        print("接龙里没解析到日期（YYYYMMDD）")
        sys.exit(1)

    internal_male, female, guest, unknown, guest_female = classify(names)
    print(f"接龙日期: {date}，共 {len(names)} 人")
    print(f"  内部男 {len(internal_male)}：{internal_male}")
    print(f"  女     {len(female)}：{female}")
    print(f"  外援男 {len(guest)}：{guest}")
    if guest_female:
        print(f"  ⚠️ 外援女 {len(guest_female)}：{guest_female}（当前结构未建模外援女，需人工处理）")
    if unknown:
        print(f"  ⚠️ 未识别 {len(unknown)}：{unknown}（不在共享名单，需人工归类）")

    # 取模板（上一周实例）
    if template_date:
        tpath = weekly.INSTANCE_DIR / f"{template_date}.json"
        if not tpath.exists():
            print(f"模板 {tpath} 不存在")
            sys.exit(1)
    else:
        tpath = weekly._latest_instance_path()
        if not tpath:
            print("instances/ 里没有任何模板实例")
            sys.exit(1)
    template = json.loads(tpath.read_text(encoding="utf-8"))
    print(f"模板: {tpath.name}")

    inst = build_instance(date, internal_male, female, guest, template)

    # 预警：策略角色成员缺人
    roster_all = set(internal_male) | set(female) | set(guest)
    warnings = []
    for pair in template.get("roles", {}).get("anchors", []):
        missing = [p for p in pair if p not in roster_all]
        if missing:
            warnings.append(f"锚点 {pair} 缺 {missing} → 需重定该锚点")
    for p in template.get("roles", {}).get("seeds", []):
        if p not in roster_all:
            warnings.append(f"种子 {p} 缺 → 需重选种子")
    for p in template.get("roles", {}).get("xd_women", []):
        if p not in roster_all:
            warnings.append(f"混双女 {p} 缺 → 需指定新的混双女")
    for pr in template.get("pairs", []):
        missing = [p for p in pr["pair"] if p not in roster_all]
        if missing:
            warnings.append(f"合练对 {pr['pair']} 缺 {missing} → 需重定合练对")
    for item in template.get("goals", {}).get("xd_min", []):
        if item.get("player") and item["player"] not in roster_all:
            warnings.append(f"混双关键球员 {item['player']} 缺 → 需调整 xd_min")

    # 与模板名单对比：新增/退出
    old = template.get("roster", {})
    old_all = set(old.get("internal_male", [])) | set(old.get("female", [])) | set(old.get("guest", []))
    added = sorted(roster_all - old_all)
    removed = sorted(old_all - roster_all)
    print(f"  新增: {added or '—'}")
    print(f"  退出: {removed or '—'}")
    if warnings:
        print("  ⚠️ 策略预警（需你确认后再跑求解器）：")
        for wmsg in warnings:
            print("    - " + wmsg)

    # 自洽性：每轮凑满场地数、角色成员都在名单里
    courts = len(inst.get("courts", []))
    st = inst.get("structure", {})
    for r, spec in st.get("rounds", {}).items():
        n = (1 if spec.get("ws") else 0) + (1 if spec.get("xd") else 0) \
            + (1 if spec.get("om") else 0) + len(spec.get("ms_seeds", []))
        if r in st.get("sc_rounds", []):
            n += 1
        if r in st.get("xl_rounds", []) and r not in st.get("duel_rounds", []):
            n += 1
        if r in st.get("duel_rounds", []):
            n += 0
        if n != courts:
            warnings.append(f"R{r} 结构={n} 场 ≠ 场地数 {courts}（换锚点结构后需调 structure）")

    out = weekly.INSTANCE_DIR / f"{date}.json"
    if dry_run:
        print("\n[dry-run] 不写文件。将写出：")
        print(json.dumps(inst, ensure_ascii=False, indent=2))
    else:
        out.write_text(json.dumps(inst, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"\n✓ 已写出 {out}")
        if warnings:
            print("  注意：上面有预警，请确认后再跑 weekly.py / solve_lineup.py / export_lineup.py")
        else:
            print("  无预警。可跑：weekly.py → solve_lineup.py → export_lineup.py")


if __name__ == "__main__":
    main()
