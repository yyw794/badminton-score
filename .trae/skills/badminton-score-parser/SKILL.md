---
name: "badminton-score-parser"
description: "Parse badminton match score images using OCR and generate statistical rankings. Invoke when user provides a match score image file and wants to parse, validate, and generate statistics."
---

# Badminton Score Parser

## Overview

Parse badminton match score images using PaddleOCR, copy OCR results exactly into match_data.json, and calculate player statistics and rankings. Provides advanced analysis for teammate quality, upset wins, and chemistry between pairs.

## Important: Copy OCR, Then Strictly Validate Scores

**Copy all scores exactly as produced by OCR, but every set MUST pass validation: the score has exactly one 15 (winner 15, loser 0–14), and scores greater than 15 are impossible.** If validation fails, it is an OCR misread: keep the OCR value as-is, add a note in JSON, and ask the user to confirm the actual score. Do not modify any data on your own judgment.

## Prerequisites

All scripts are located in the `scores/` directory. Execute commands from the project root directory.

Known players (for reference only):
- Male: 苏大哲, 罗蒙, 江锐, 严勇文, 陈顺星, 陈小洪, 卢志辉, 林锋, 王小波, 刘继宇, 董广博, 林琪琛, 罗琴荩, 张欣欣, 黄冬青, 程建兴, 陈宇霆, 卢子龙, 吴煜
- Female: 田茜, 唐英武, 李祺祺, 高洁, 滕菲, 谢卓珊, 崔倩男, 林小连, 张燕红, 李杏芝, 项小英

## Workflow

### Step 1: OCR Parsing

Run PaddleOCR on the score image:

```bash
python3 scores/paddleocr_vl.py <image_path>
```

Output is saved to `scores/<date>/output_<date>/doc_0.md`.

### Step 2: Read OCR Results

Read the generated markdown file to inspect OCR output. The table has 6 columns (轮次, 场地, 对阵A, 比分A, 比分B, 对阵B) or 7 columns (when type column exists).

### Step 3: Score Validation (分数检查)

**先原样复制 OCR 输出的所有比分。Do NOT modify any digits, order, or values on your own judgment.** 然后逐局检查。

**合法比分规则：每局有且只有 1 个 15 分（胜方 15 分，负方 0–14 分）。** 以下情况均为非法，说明 OCR 识别错误：
- 出现大于 15 分：如 15:17、11:18
- 双方均未达到 15 分：如 13:11
- 双方都是 15 分：如 15:15

对检查不通过的局：
- 比分照抄 OCR 输出，不自行修改
- 在 `notes` 字段添加备注："比分异常：XX:XX（超过 15 分 / 双方均未达 15 分 / 双方均为 15 分），请确认"
- 向用户确认实际比分，用户答复后才可修正，修正后重算所有统计

The only modifications allowed are:
- Adding match type column if missing from OCR output
- Adding notes for anomalous scores (as described above)
- Correcting a score ONLY after the user confirms the actual score
- Converting format from OCR markdown to the required JSON structure

### Step 4: Create match_data.json

Create the JSON file at `scores/<date>/match_data.json` following this format:

```json
{
  "match_date": "YYYY-MM-DD",
  "description": "比赛描述",
  "format": "15分/局，2局",
  "matches": [
    {
      "round": 1,
      "court": 1,
      "type": "男双",
      "team_a": ["选手1", "选手2"],
      "team_b": ["选手1"],
      "score_a": "15:13",
      "score_b": "11:15",
      "notes": "异常情况说明（可选）"
    }
  ]
}
```

Rules:
- All matches must have both score_a and score_b
- Copy scores EXACTLY from OCR output — do not modify them
- 每局有且只有 1 个 15 分（不可能出现大于 15 分）；检查不通过的局照抄并加备注
- Match type should match the OCR output (男双/女双/混双/单打)
- Player names should match the OCR output — do not auto-correct names

**创建后必须运行自动化全量比分检查，0 异常才能进入统计：**

```bash
python3 -c "
import json, sys
data = json.load(open(sys.argv[1]))
issues = 0
for m in data['matches']:
    r, c = m['round'], m['court']
    ta, tb = '/'.join(m['team_a']), '/'.join(m['team_b'])
    for g, s in enumerate([m['score_a'], m['score_b']], 1):
        a, b = map(int, s.split(':'))
        if a > 15 or b > 15:
            print('异常 R%sC%s 局%s: %s 超过 15 分 (%s vs %s)' % (r, c, g, s, ta, tb)); issues += 1
        elif a == 15 and b == 15:
            print('异常 R%sC%s 局%s: %s 双方均为 15 分 (%s vs %s)' % (r, c, g, s, ta, tb)); issues += 1
        elif a != 15 and b != 15:
            print('异常 R%sC%s 局%s: %s 双方均未达 15 分 (%s vs %s)' % (r, c, g, s, ta, tb)); issues += 1
print('检查完成: 共 %s 局, 异常 %s 个' % (len(data['matches'])*2, issues))
" "scores/<date>/match_data.json"
```

有异常时：逐一向用户确认实际比分 → 修正 match_data.json → 重跑检查直到 0 异常 → 再计算统计（若已算过，修正后必须全部重算）。

### Step 5: Calculate Statistics

```bash
python3 scores/calculate_stats.py scores/<date>/match_data.json
```

Note: Always specify the path explicitly, as the script defaults to the latest match_data.json in scores/ directory.

### Step 6 (Optional): Advanced Analysis — Teammate Quality (队友含金量)

Run this to determine whether high-ranked players got there by carrying weak teammates or by riding on strong teammates' coattails.

```bash
python3 scores/teammate_analysis.py scores/<date>/match_data.json
```

**How it works:**
- Assign each player a "rank score" by overall ranking (#1 = 1 point, #20 = 20 points; lower = stronger)
- For each player, compute the AVERAGE rank score of ALL their partners across every round they played
- Compute DIFF = own_rank_score − avg_partner_score
  - **Large negative (e.g. -11): True MVP / real carry** — player is way stronger than average partner, yet wins a lot
  - **Large positive (e.g. +9): Free-rider / carried** — player is much weaker than average partner, only wins because partners are strong
- Key output metrics: teammate average score, diff, qualitative tags (真正大腿 / 抱大腿王 / etc.)

### Step 7 (Optional): Advanced Analysis — Upset Wins & Pair Chemistry (以弱胜强/配合加成)

Run this to find underdog wins, players who consistently outperform expectations, and pairs with great chemistry.

```bash
python3 scores/upset_analysis.py scores/<date>/match_data.json
```

**How it works:**
- For every set, compute "paper strength" = sum of rank scores of each team (lower sum = stronger on paper)
- If the team with HIGHER paper sum (weaker on paper) wins the set → count as UPSET (逆袭)
- Three sections in output:
  1. **Top upset matches** (sorted by paper-strength gap) — the most surprising wins of the day
  2. **Per-player upset metrics:**
     - Upset win rate = upset_wins / (upset_wins + upset_losses): "comeback king" if high
     - Upset loss rate = favored_losses / (favored_wins + favored_losses): "choker" if high (loses when supposed to win)
  3. **Pair chemistry** (pairs with ≥4 sets): upset rate + total win rate
     - 100% upset win rate = pairs that punch way above their weight (great chemistry)
     - 0% win rate = toxic pairs that never win, avoid combining

### Step 8 (Optional): Advanced Analysis — Weighted Comprehensive Ranking (综合加权排名)

Run this to produce a fairer ranking that blends raw win rate with opponent difficulty and teammate carry/coattail factors — so that players who win by carrying weaker teammates get bumped up, while players who win only against weak opponents or ride strong teammates get corrected down.

```bash
python3 scores/weighted_rank.py scores/<date>/match_data.json
```

**How it works (v3 balanced formula, 65% / 20% / 15%):**
1. **65% Base component** = raw_win_rate × 100 + 4 × net_points_per_set  
   Raw win rate dominates — a 3-9 record can never surpass a 9-3 record.
2. **20% Difficulty adjustment** = 150 × (weighted_win_rate − raw_win_rate) + 10 × weighted_net_score_per_set  
   - Weighted "win weight" per set = sqrt(own_team_avg_rank / opponent_avg_rank): larger = harder underdog situation
   - Win a hard set → +sqrt(difficulty); lose an easy set → −1/sqrt(difficulty) (easy-set losses are penalized heavily)
   - Δ胜 = weighted_win_rate − raw_win_rate: positive = "underdog warrior", negative = "weak-team stat padder"
3. **15% Gold-content bonus** = 2.2 × (−teammate_diff) + 1.6 × (10.5 − avg_opponent_rank)  
   - **Carry bonus (−teammate_diff):** teammate_diff = own_rank − avg_partner_rank. A large negative (e.g. −11.3 for 黄冬青) means the player is way stronger than average partners → massive carry bonus added.
   - **Opponent-strength bonus:** avg_opponent_rank below 10.5 means the player fought stronger opponents on average → extra bonus.
   - Large positive teammate_diff (e.g. +9.3 for 王小波) → bonus becomes negative → coattail penalty applied.

**Final composite score = 65% base + 20% difficulty + 15% gold-content.** Output includes:
- Ranked table with movement arrows (↑/↓ vs. pure-win-rate ranking)
- Top risers (previously underrated carry / hard-match players)
- Top fallers (previously overrated coattail / weak-opponent stat-padder players)

### Step 9: Cleanup

Remove intermediate files from the output directory:

```bash
rm -rf scores/<date>/output_<date>
```

Only keep: original image + match_data.json

## Scoring Rules

- 15 points per set, first to 15 wins
- **每局比分有且只有 1 个 15 分：胜方 15，负方 0–14；不可能出现大于 15 分，也不可能双方都未达到 15 分**
- 2 sets per match
- Match types: 单打, 男双, 女双, 混双
- 3 columns layout: team_a vs team_b with scores
- 4 columns layout: team_a | score_a | score_b | team_b
