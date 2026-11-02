# 活动记录

一周一个目录，命名 `YYYY-MM-DD`。

```
活动/
├── 2026-11-02/
│   ├── 01_微信接龙.txt
│   ├── 02_排阵需求.txt
│   ├── 03_排阵输出.xlsx
│   ├── 04_赛后分析.md
│   ├── 排阵配置.json
│   ├── 排阵输出.json
│   └── 比分/
├── _模板/          # 新一周从这里复制
└── ...
```

## 快速开始

1. `cp -r 活动/_模板 活动/2026-11-09`
2. 填 `01_微信接龙.txt`、`02_排阵需求.txt`
3. 跑：
   ```bash
   .venv/bin/python 排阵系统/sync_roster.py 2026-11-09
   .venv/bin/python 排阵系统/weekly.py
   .venv/bin/python 排阵系统/solve_lineup.py
   .venv/bin/python 排阵系统/export_lineup.py
   ```
4. 赛后把比分放进 `比分/`，分析写到 `04_赛后分析.md`

更细的说明见 `活动/_模板/README.md`。
