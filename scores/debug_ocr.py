#!/usr/bin/env python3
"""Debug: print raw cell structure of tables."""

import os, re, glob
from bs4 import BeautifulSoup

HISTORY_DIR = "/Users/yanyongwen712/Documents/pingan_tech_badminton_team/scores/history"

# Pick one file to debug
d = sorted(glob.glob(os.path.join(HISTORY_DIR, 'output_*/')))[0]
md_file = os.path.join(d, 'doc_0.md')

with open(md_file, 'r', encoding='utf-8') as f:
    content = f.read()

tables = re.findall(r'<table(.*?)</table>', content, re.DOTALL)
soup = BeautifulSoup(tables[0], 'html.parser')
rows = soup.find_all('tr')

print(f"Total rows: {len(rows)}")
print(f"Row 0 (header) cells: {[c.get_text(strip=True) for c in rows[0].find_all(['td','th'])]}")
print()

for i, row in enumerate(rows[1:4]):
    cells = row.find_all(['td','th'])
    print(f"Row {i+1} ({len(cells)} cells):")
    for j, cell in enumerate(cells):
        text = cell.get_text(strip=True)
        colspan = cell.get('colspan', '1')
        print(f"  [{j}] colspan={colspan} text='{text}'")
    print()
