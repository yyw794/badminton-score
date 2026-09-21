#!/usr/bin/env python3
"""Parse all OCR output files and create match_data.json for each."""

import os
import re
import json
import glob
from bs4 import BeautifulSoup
from collections import Counter

HISTORY_DIR = "/Users/yanyongwen712/Documents/pingan_tech_badminton_team/scores/history"


def clean_score(score_str):
    """Clean OCR errors in scores."""
    if not score_str:
        return score_str
    parts = score_str.split(':')
    cleaned = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if len(p) > 2:
            p = p[:2]
        try:
            val = int(p)
            if val > 30:
                p = str(val)[:-1] if len(str(val)) > 2 else p
        except ValueError:
            pass
        cleaned.append(p)
    return ':'.join(cleaned)


def get_cells(row):
    """Get text cells from a table row."""
    return [c.get_text(strip=True) for c in row.find_all(['td', 'th'])]


def parse_court_section(cells, start):
    """Parse a court section (5 cells): p1, p2, score, p3, p4
    Team A = [p1, p2], Team B = [p3, p4]
    """
    section = cells[start:start + 5]
    if len(section) < 3:
        return None

    names = []
    score = ''

    for c in section:
        if not c:
            continue
        if re.match(r'\d+:\d+', c):
            score = c
        elif c.isdigit() and len(c) <= 2:
            continue  # Skip single digits (extra data)
        else:
            names.append(c)

    if len(names) < 4:
        return None

    team_a = names[:2]
    team_b = names[2:4]

    return {'team_a': team_a, 'team_b': team_b, 'score': clean_score(score)}


def count_courts_in_row(cells):
    """Count courts by counting scores in the row."""
    return sum(1 for c in cells if re.match(r'\d+:\d+', c))


def parse_court_table(rows):
    """Parse court-based table. Each court = 5 cells."""
    matches = []

    if len(rows) < 2:
        return matches

    first_cells = get_cells(rows[1])
    num_courts = count_courts_in_row(first_cells)

    for row in rows[1:]:
        cells = get_cells(row)
        if not cells:
            continue

        row_label = cells[0]

        if any('自由练习' in c for c in cells):
            continue

        round_match = re.match(r'第(\d+)局', row_label)
        if not round_match:
            continue
        round_num = int(round_match.group(1))

        for court_idx in range(1, num_courts + 1):
            start = 1 + (court_idx - 1) * 5
            result = parse_court_section(cells, start)
            if result:
                match = {
                    'round': round_num,
                    'court': court_idx,
                    'type': '男双',
                    'team_a': result['team_a'],
                    'team_b': result['team_b'],
                    'score_a': result['score'],
                    'score_b': '',
                }
                matches.append(match)

    return matches


def parse_structured_table(rows):
    """Parse structured table with type/court/score columns."""
    matches = []

    if len(rows) < 2:
        return matches

    for row in rows[1:]:
        cells = get_cells(row)
        if not cells:
            continue

        round_num = ''
        court = 1
        match_type = '男双'
        team_a = []
        team_b = []
        scores = []

        for c in cells:
            text = c
            if not text:
                continue

            if '场地' in text:
                m = re.search(r'(\d+)', text)
                if m:
                    court = int(m.group(1))
                continue

            if text in ('男双', '女双', '混双', '单打'):
                match_type = text
                continue

            if re.match(r'\d+:\d+', text):
                scores.append(clean_score(text))
                continue

            if re.match(r'^第?\d*[轮局]$', text):
                round_num = text
                continue

            if re.match(r'^\d+$', text) and not scores:
                if not round_num:
                    round_num = text
                continue

            if len(team_a) < 2:
                team_a.append(text)
            elif len(team_b) < 2:
                team_b.append(text)

        if team_a and team_b:
            round_match = re.search(r'(\d+)', round_num)
            round_int = int(round_match.group(1)) if round_match else len(matches) + 1

            match = {
                'round': round_int,
                'court': court,
                'type': match_type,
                'team_a': team_a[:2],
                'team_b': team_b[:2],
                'score_a': scores[0] if len(scores) >= 1 else '',
                'score_b': scores[1] if len(scores) >= 2 else '',
            }
            matches.append(match)

    return matches


def parse_md_file(md_path):
    """Parse a single OCR markdown file."""
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    tables = re.findall(r'<table(.*?)</table>', content, re.DOTALL)
    all_matches = []

    for table_html in tables:
        soup = BeautifulSoup(table_html, 'html.parser')
        rows = soup.find_all('tr')

        if not rows:
            continue

        first_cells = [c.get_text() for c in rows[0].find_all(['td', 'th'])]
        has_type = any(t in ('男双', '女双', '混双', '单打') for t in first_cells)

        total_data_cells = sum(1 for r in rows[1:] for _ in r.find_all(['td', 'th']))
        is_court_table = total_data_cells > 50

        if has_type:
            matches = parse_structured_table(rows)
        elif is_court_table:
            matches = parse_court_table(rows)
        else:
            matches = parse_court_table(rows)
            if not matches:
                matches = parse_structured_table(rows)

        all_matches.extend(matches)

    return all_matches


def main():
    output_dirs = sorted(glob.glob(os.path.join(HISTORY_DIR, 'output_*/')))
    total_matches = 0

    for d in output_dirs:
        md_file = os.path.join(d, 'doc_0.md')
        if not os.path.exists(md_file):
            continue

        dir_name = os.path.basename(d.rstrip('/'))
        print(f"\nProcessing: {dir_name}")

        matches = parse_md_file(md_file)
        print(f"  Found {len(matches)} matches")

        if matches:
            match_data = {
                'match_date': '2026-06-17',
                'description': f"历史比分 - {dir_name}",
                'format': '15分/局，2局',
                'matches': matches
            }

            safe_name = re.sub(r'[^\w\-]', '_', dir_name)
            json_path = os.path.join(HISTORY_DIR, f'match_data_{safe_name}.json')

            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(match_data, f, ensure_ascii=False, indent=2)

            print(f"  Saved: {os.path.basename(json_path)}")
            total_matches += len(matches)

            # Show sample
            for m in matches[:5]:
                print(f"    R{m['round']} C{m['court']}: {'/'.join(m['team_a'])} vs {'/'.join(m['team_b'])} ({m['score_a']})")
            if len(matches) > 5:
                print(f"    ... and {len(matches) - 5} more")

    print(f"\nTotal matches parsed: {total_matches}")


if __name__ == '__main__':
    main()
