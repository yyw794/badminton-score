# 排阵系统

排阵引擎（代码层）。所有每周数据都在 `活动/<date>/`，这里只放算法和公共名单。

## 主要文件

| 文件 | 作用 |
|---|---|
| `paths.py` | 统一路径：`活动/<date>/`、`比分分析/bt/` |
| `weekly.py` | 读取 `活动/<date>/排阵配置.json`，派生 Week 对象 |
| `solve_lineup.py` | 回溯求解器，输出 `活动/<date>/排阵输出.json` |
| `export_lineup.py` | 独立硬校验 + 导出 `活动/<date>/03_排阵输出.xlsx`（对阵表 + 签到表 + 按人 sheet） |
| `sync_roster.py` | 读 `01_微信接龙.txt`，生成 `排阵配置.json` 草稿 |
| `excel_exporter.py` | 共享球员名单（内部男/女/外援） |
| `player_departments.json` | 签名表用的姓名→部门映射；空缺可在这里补 |

## 每周命令

```bash
.venv/bin/python 排阵系统/sync_roster.py 2026-11-02
.venv/bin/python 排阵系统/weekly.py
.venv/bin/python 排阵系统/solve_lineup.py
.venv/bin/python 排阵系统/export_lineup.py
```

`sync_roster.py` 是可选辅助：它基于上一周配置复制结构，`_note`/`title` 会标成草稿；正式排阵仍以 `02_排阵需求.txt` 为准，由大模型改写 `排阵配置.json`。

## 文档

- `系统架构图.md`
- `求解器算法设计.md`
- `大模型排序需求.md`
- `_archive/`：旧版排阵脚本/一次性脚本，仅存档
