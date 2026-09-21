#!/usr/bin/env python3
import json
import glob
import os

HISTORY_DIR = "/Users/yanyongwen712/Documents/pingan_tech_badminton_team/scores/history"
json_files = sorted(glob.glob(os.path.join(HISTORY_DIR, "match_data_*.json")))

print(f"Found {len(json_files)} files\n")

all_issues = []

for fpath in json_files:
    fname = os.path.basename(fpath)
    with open(fpath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    matches = data.get("matches", [])
    print(f"\n{'='*60}")
    print(f"FILE: {fname}")
    print(f"  Total matches: {len(matches)}")

    valid_count = 0
    empty_score = 0
    issues_in_file = []

    match_map = {}

    for m in matches:
        score_a = m.get("score_a", "") or ""
        score_b = m.get("score_b", "") or ""
        round_n = m["round"]
        court = m["court"]
        team_a = tuple(m["team_a"])
        team_b = tuple(m["team_b"])

        if not score_a and not score_b:
            empty_score += 1
            issues_in_file.append(f"Empty scores: round {round_n}, court {court}, {m['team_a']} vs {m['team_b']}")
        else:
            valid_count += 1

        if score_a:
            parts = score_a.split(":")
            if len(parts) == 2:
                try:
                    sa, sb = int(parts[0]), int(parts[1])
                    if sa > 25 or sb > 25:
                        issues_in_file.append(f"Unreasonable score {score_a} in round {round_n} court {court}")
                    if sa == sb:
                        issues_in_file.append(f"Tied score {score_a} in round {round_n} court {court}")
                except ValueError:
                    issues_in_file.append(f"Non-numeric score {score_a} in round {round_n} court {court}")

        if score_b:
            parts = score_b.split(":")
            if len(parts) == 2:
                try:
                    sa, sb = int(parts[0]), int(parts[1])
                    if sa > 25 or sb > 25:
                        issues_in_file.append(f"Unreasonable score {score_b} in round {round_n} court {court}")
                    if sa == sb:
                        issues_in_file.append(f"Tied score {score_b} in round {round_n} court {court}")
                except ValueError:
                    issues_in_file.append(f"Non-numeric score {score_b} in round {round_n} court {court}")

        if len(team_a) == 2 and team_a[0] == team_a[1]:
            issues_in_file.append(f"Same player in team_a: [{', '.join(team_a)}] round {round_n} court {court}")

        if len(team_b) == 2 and team_b[0] == team_b[1]:
            issues_in_file.append(f"Same player in team_b: [{', '.join(team_b)}] round {round_n} court {court}")

        key = (round_n, court, team_a, team_b)
        match_map[key] = match_map.get(key, 0) + 1

    dupes = {k: v for k, v in match_map.items() if v > 1}
    for key, count in dupes.items():
        round_n, court, team_a, team_b = key
        issues_in_file.append(f"Duplicate match (count={count}): round {round_n}, court {court}, {team_a} vs {team_b}")

    all_issues.extend(issues_in_file)

    print(f"  Valid score matches: {valid_count}")
    print(f"  Empty score matches: {empty_score}")
    print(f"  Duplicates: {len(dupes)}")
    print(f"  Total issues: {len(issues_in_file)}")
    if issues_in_file:
        for issue in issues_in_file[:50]:
            print(f"    - {issue}")
        if len(issues_in_file) > 50:
            print(f"    ... and {len(issues_in_file)-50} more")

print(f"\n\n{'='*60}")
print(f"OVERALL SUMMARY")
print(f"{'='*60}")
print(f"Total issues across all files: {len(all_issues)}")

unreasonable = [i for i in all_issues if "Unreasonable" in i]
tied = [i for i in all_issues if "Tied" in i]
empty = [i for i in all_issues if "Empty" in i]
duplicate_players = [i for i in all_issues if "Same player" in i]
duplicate_matches = [i for i in all_issues if "Duplicate match" in i]

print(f"  Unreasonable scores (>25): {len(unreasonable)}")
print(f"  Tied scores (=): {len(tied)}")
print(f"  Empty scores: {len(empty)}")
print(f"  Duplicate players on same team: {len(duplicate_players)}")
print(f"  Duplicate match entries: {len(duplicate_matches)}")

print(f"\n  Unreasonable scores detail:")
for u in unreasonable:
    print(f"    - {u}")

print(f"\n  First 10 tied scores:")
for t in tied[:10]:
    print(f"    - {t}")

print(f"\n  First 10 empty scores:")
for e in empty[:10]:
    print(f"    - {e}")

print(f"\n  Duplicate players:")
for d in duplicate_players:
    print(f"    - {d}")

print(f"\n  Duplicate matches:")
for d in duplicate_matches:
    print(f"    - {d}")
