#!/usr/bin/env python3
"""Check for cross-file duplicate matches"""
import json
import glob
import os
from collections import defaultdict

HISTORY_DIR = "/Users/yanyongwen712/Documents/pingan_tech_badminton_team/scores/history"
json_files = sorted(glob.glob(os.path.join(HISTORY_DIR, "match_data_*.json")))

# Track all matches across files with their source
# key: (round, court, tuple(team_a), tuple(team_b)) -> list of file names
all_match_map = defaultdict(list)

for fpath in json_files:
    fname = os.path.basename(fpath)
    with open(fpath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    matches = data.get("matches", [])
    for m in matches:
        key = (m["round"], m["court"], tuple(m["team_a"]), tuple(m["team_b"]))
        all_match_map[key].append(fname)

# Find cross-file duplicates
cross_dupes = {k: v for k, v in all_match_map.items() if len(v) > 1}

print(f"Cross-file duplicate matches: {len(cross_dupes)}")
print(f"Total unique match entries: {len(all_match_map)}")
print()

if cross_dupes:
    # Group by player to see who's most affected
    player_dup_count = defaultdict(int)
    for key, files in cross_dupes.items():
        round_n, court, team_a, team_b = key
        for p in team_a:
            player_dup_count[p] += 1
        for p in team_b:
            player_dup_count[p] += 1
    
    print("Players with most duplicate match entries:")
    for p, c in sorted(player_dup_count.items(), key=lambda x: -x[1])[:20]:
        print(f"  {p}: {c} duplicate entries")
    
    print("\nSample cross-file duplicates:")
    shown = 0
    for key, files in list(cross_dupes.items())[:30]:
        round_n, court, team_a, team_b = key
        print(f"  Round {round_n}, Court {court}: {team_a} vs {team_b}")
        print(f"    Files: {files}")
        print()
        shown += 1
    
    if len(cross_dupes) > 30:
        print(f"  ... and {len(cross_dupes)-30} more")

# Count total matches including duplicates
total_entries = sum(len(v) for v in all_match_map.values())
print(f"\nTotal match entries (with cross-file dupes): {total_entries}")
print(f"Unique match entries (deduped): {len(all_match_map)}")
print(f"Cross-file duplicates to remove: {total_entries - len(all_match_map)}")
