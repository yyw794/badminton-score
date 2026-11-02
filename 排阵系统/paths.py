#!/usr/bin/env python3
"""统一路径：活动/<date>/ 周目录 + 全局 BT 数据 + 比分分析脚本目录。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ACTIVITY_DIR = ROOT / "活动"
SYSTEM_DIR = ROOT / "排阵系统"
ANALYSIS_DIR = ROOT / "比分分析"
BT_DIR = ANALYSIS_DIR / "bt"
HISTORY_DIR = ANALYSIS_DIR / "history"

# 周目录内的文件名（用户约定）
SIGNUP_NAME = "01_微信接龙.txt"
REQUEST_NAME = "02_排阵需求.txt"
EXCEL_NAME = "03_排阵输出.xlsx"
REPORT_NAME = "04_赛后分析.md"
CONFIG_NAME = "排阵配置.json"
LINEUP_NAME = "排阵输出.json"
SCORE_DIR_NAME = "比分"


def week_dir(date: str) -> Path:
    return ACTIVITY_DIR / date


def config_path(date: str) -> Path:
    return week_dir(date) / CONFIG_NAME


def signup_path(date: str) -> Path:
    return week_dir(date) / SIGNUP_NAME


def request_path(date: str) -> Path:
    return week_dir(date) / REQUEST_NAME


def lineup_json_path(date: str) -> Path:
    return week_dir(date) / LINEUP_NAME


def excel_path(date: str) -> Path:
    return week_dir(date) / EXCEL_NAME


def report_path(date: str) -> Path:
    return week_dir(date) / REPORT_NAME


def score_dir(date: str) -> Path:
    return week_dir(date) / SCORE_DIR_NAME


def available_dates() -> list[str]:
    """活动/ 下形如 YYYY-MM-DD 的目录，升序。"""
    if not ACTIVITY_DIR.exists():
        return []
    return sorted(p.name for p in ACTIVITY_DIR.iterdir()
                  if p.is_dir() and len(p.name) == 10 and p.name[4] == "-" and p.name[7] == "-")


def latest_date() -> str | None:
    dates = available_dates()
    return dates[-1] if dates else None


def resolve_date(date: str | None) -> str | None:
    return date or latest_date()
