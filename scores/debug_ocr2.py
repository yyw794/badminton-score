#!/usr/bin/env python3
"""Debug: show detailed cell analysis for a few rows."""

import os, re, glob
from bs4 import BeautifulSoup

HISTORY_DIR = "/Users/yanyongwen712/Documents/pingan_tech_badminton_team/scores/history"

d = sorted(glob.glob(os.path.join(HISTORY_DIR, 'output_*/')))[0]
md_file = os.path.join(d, 'doc_0.md')

with open(md_file, 'r', encoding='utf-8') as f:
    content = f.read()

tables = re.findall(r'<table(.*?)</table>', content, re.DOTALL)
soup = BeautifulSoup(tables[0], 'html.parser')
rows = soup.find_all('tr')

# Analyze row 1
row = rows[1]
cells = row.find_all(['td', 'th'])
print(f"Row 1: {len(cells)} cells")
for i, cell in enumerate(cells):
    text = cell.get_text(strip=True)
    print(f"  [{i}]='{text}'")

# Identify patterns: names vs scores
print("\nClassification:")
for i, cell in enumerate(cells):
    text = cell.get_text(strip=True)
    if re.match(r'第', text):
        cat = 'ROUND'
    elif re.match(r'\d+:\d+', text):
        cat = 'SCORE'
    elif text.isdigit():
        cat = 'SINGLE_NUM'
    elif not text:
        cat = 'EMPTY'
    else:
        cat = 'NAME'
    print(f"  [{i}] {cat:10s} '{text}'")

# Now try: group cells by 5 starting from position 1
print("\n\n5-cell groups starting from pos 1:")
for g in range(3):
    start = 1 + g * 5
    end = start + 5
    group = cells[start:end]
    names = [c.get_text(strip=True) for c in group if c.get_text(strip=True) and not re.match(r'\d+:\d+', c.get_text(strip=True)) and not c.get_text(strip=True).isdigit()]
    scores = [c.get_text(strip=True) for c in group if re.match(r'\d+:\d+', c.get_text(strip=True))]
    print(f"  Group {g+1}: cells[{start}:{end}]")
    print(f"    Names: {names}")
    print(f"    Scores: {scores}")
