#!/usr/bin/env python3
"""球队名单 / 部门映射。

权威名单：排阵系统/球队名单.json（用户确认过的版本）。
兼容旧文件：player_departments.json（仅兜底，不覆盖权威名单）。
"""
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROSTER_JSON = BASE / "球队名单.json"
DEPARTMENTS_JSON = BASE / "player_departments.json"


def load_roster() -> dict:
    """读权威名单；不存在时返回空结构。"""
    if ROSTER_JSON.exists():
        try:
            return json.loads(ROSTER_JSON.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"members": []}


def load_departments() -> dict[str, str]:
    data: dict[str, str] = {}

    # 1) 权威名单优先
    for m in load_roster().get("members", []):
        name, dept = m.get("name"), m.get("department") or ""
        if name and dept:
            data[str(name)] = str(dept)

    # 2) 旧部门表补充（不覆盖权威名单）
    if DEPARTMENTS_JSON.exists():
        try:
            old = json.loads(DEPARTMENTS_JSON.read_text(encoding="utf-8"))
            for name, dept in old.items():
                if name and dept and not data.get(str(name)):
                    data[str(name)] = str(dept)
        except Exception:
            pass

    return data


def status_of(name: str) -> str:
    """返回 正式/试训/外援；不在权威名单时返回空串。"""
    for m in load_roster().get("members", []):
        if m.get("name") == name:
            return m.get("status", "")
    return ""
