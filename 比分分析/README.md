# 比分分析

赛后统计/OCR/排名脚本（代码层）。每周原始比分在 `活动/<date>/比分/`，全局 BT 实力数据在 `比分分析/bt/`。

## 数据位置

```
活动/<date>/
├── 比分/
│   ├── <date>.jpg                 # 比分原图
│   ├── match_data.json            # 结构化比分
│   └── output_<date>/             # OCR 原始输出（doc_0.md / paddleocr_raw.jsonl）
└── 04_赛后分析.md                 # 赛后大模型分析
```

## 常用命令

```bash
# 统计某周
.venv/bin/python 比分分析/calculate_stats.py 活动/2026-11-02/比分/match_data.json

# 不传路径：自动找最新一周的 比分/match_data.json
.venv/bin/python 比分分析/calculate_stats.py

# OCR
.venv/bin/python 比分分析/paddleocr_vl.py 活动/2026-11-02/比分/20261102.jpg
.venv/bin/python 比分分析/verify_ocr.py 活动/2026-11-02/比分/output_20261102/doc_0.md

# 全局 BT 排名
.venv/bin/python 比分分析/historical_bt_rank.py
.venv/bin/python 比分分析/output_theta_ratings.py
.venv/bin/python 比分分析/export_bt_excel.py
```

## 主要脚本

| 脚本 | 作用 |
|---|---|
| `calculate_stats.py` | 单周统计/排名 |
| `paddleocr_vl.py` | 比分图 OCR |
| `verify_ocr.py` | OCR 结果校验 |
| `historical_bt_rank.py` | 全历史 BT 排名 |
| `output_theta_ratings.py` | 输出全局 θ → `bt/bt_theta_ratings.json` |
| `export_bt_excel.py` | 输出 `bt/BT排名总表.xlsx` |
| `lineup_discovery.py` / `predict_doubles.py` | 组合/对阵分析 |
| `teammate_analysis.py` / `upset_analysis.py` / `weighted_rank.py` | 专项分析 |

`bt/` 是全局实力数据；各周自己的 θ 快照保留在 `活动/<date>/比分/`（如 2026-09-28、2026-10-19）。
