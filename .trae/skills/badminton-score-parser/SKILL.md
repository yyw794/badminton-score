---
name: "badminton-score-parser"
description: "Parse badminton match score images using OCR and generate statistical rankings. Invoke when user provides a match score image file and wants to parse, validate, and generate statistics."
---

# Badminton Score Parser

## Overview

Parse badminton match score images using PaddleOCR, copy OCR results exactly into match_data.json, and calculate player statistics and rankings.

## Important: Trust OCR Completely

**Copy all scores exactly as produced by OCR.** The only exception is: if neither player reaches 15 points in a set, flag it as anomalous (add a note in JSON) and ask user for confirmation. Do not modify any data on your own judgment.

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

### Step 3: Trust OCR Results — Only Flag Anomalous Scores

**Copy all scores exactly from OCR output. Do NOT modify any digits, order, or values.**

However, scores MUST have at least one player reaching 15 points per set. If OCR output shows a set where neither side reaches 15:
- Copy the score exactly as OCR produced it
- Add a note in the `notes` field: "比分异常：XX:XX 双方均未达到 15 分，请确认"
- Ask user to confirm before changing the score

The only modifications allowed are:
- Adding match type column if missing from OCR output
- Adding notes for anomalous scores (as described above)
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
- Match type should match the OCR output (男双/女双/混双/单打)
- Player names should match the OCR output — do not auto-correct names
- If a set has no 15-point winner, copy the score but add a note

### Step 5: Calculate Statistics

```bash
python3 scores/calculate_stats.py scores/<date>/match_data.json
```

Note: Always specify the path explicitly, as the script defaults to the latest match_data.json in scores/ directory.

### Step 6: Cleanup

Remove intermediate files from the output directory:

```bash
rm -rf scores/<date>/output_<date>
```

Only keep: original image + match_data.json

## Scoring Rules

- 15 points per set, first to 15 wins
- 2 sets per match
- Match types: 单打, 男双, 女双, 混双
- 3 columns layout: team_a vs team_b with scores
- 4 columns layout: team_a | score_a | score_b | team_b
