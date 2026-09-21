#!/usr/bin/env python3
"""Debug: show colspan info for header row."""

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

print("Header row cells with colspan:")
for cell in rows[0].find_all(['td', 'th']):
    text = cell.get_text(strip=True)
    colspan = cell.get('colspan', '1')
    print(f"  text='{text}' colspan={colspan}")

# Also check what data cells look like
print("\nData row cells with colspan (first 5 rows):")
for i in range(1, 6):
    row = rows[i]
    cells = row.find_all(['td', 'th'])
    print(f"\nRow {i} ({len(cells)} cells):")
    for j, cell in enumerate(cells):
        text = cell.get_text(strip=True)
        colspan = cell.get('colspan', '1')
        print(f"  [{j}] text='{text}' colspan={colspan}")

# Check rows with different structure (e.g. 场地1 instead of 场地一)
print("\n\n--- Checking a file with 场地1 format ---")
d2 = sorted(glob.glob(os.path.join(HISTORY_DIR, 'output_*/')))[10]  # index 10
md2 = os.path.join(d2, 'doc_0.md')
with open(md2, 'r', encoding='utf-8') as f:
    content2 = f.read()
tables2 = re.findall(r'<table(.*?)</table>', content2, re.DOTALL)
soup2 = BeautifulSoup(tables2[0], 'html.parser')
rows2 = soup2.find_all('tr')

print(f"\nHeader row ({len(rows2[0].find_all(['td','th']))} cells):")
for cell in rows2[0].find_all(['td', 'th']):
    text = cell.get_text(strip=True)
    colspan = cell.get('colspan', '1')
    print(f"  text='{text}' colspan={colspan}")

print("\nRow 1:")
for cell in rows2[1].find_all(['td', 'th']):
    text = cell.get_text(strip=True)
    colspan = cell.get('colspan', '1')
    print(f"  text='{text}' colspan={colspan}")
