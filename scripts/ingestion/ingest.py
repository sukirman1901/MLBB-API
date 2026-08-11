#!/usr/bin/env python3
"""
MLBB Esports Ingestion Pipeline Runner
Author: sukirman1901
Repository: https://github.com/sukirman1901/MLBB-API

Orchestrates:
  1. Live API connectivity test & wikitext raw snapshot caching with SHA-256 hash.
  2. Parsing wikitext series and match maps.
  3. Normalizing entities (Tournaments, Teams, Series, Matches, Chronological Drafts).
  4. Saving output to esports/ directory structure.
"""

import json
import os
import sys

from sources.liquipedia import test_connectivity, fetch_and_cache_raw, parse_match_blocks
from normalize import normalize_tournament, normalize_series_and_matches

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    print("==========================================================")
    print("   MLBB ESPORTS DATA ACQUISITION PIPELINE V1.1")
    print("==========================================================")

    # 1. Connectivity & Raw Snapshot
    page_title = "M5_World_Championship/Knockout_Stage"
    ok, _ = test_connectivity(page_title)
    if not ok:
        print("✗ Ingestion stopped due to failed connectivity test.")
        sys.exit(1)

    snapshot, content_hash = fetch_and_cache_raw(page_title)
    parsed_series = parse_match_blocks(snapshot['wikitext'])

    # 2. Normalize
    tournament = normalize_tournament("M5 World Championship")
    teams, series, matches = normalize_series_and_matches(parsed_series, content_hash)

    # 3. Save to esports/
    tournaments_file = os.path.join(BASE_DIR, 'esports/tournaments/tournaments.json')
    teams_file = os.path.join(BASE_DIR, 'esports/teams/teams.json')
    series_file = os.path.join(BASE_DIR, 'esports/matches/series.json')
    matches_file = os.path.join(BASE_DIR, 'esports/matches/m5_knockout_matches.json')

    with open(tournaments_file, 'w', encoding='utf-8') as f:
        json.dump({"revdate": "2026-08-11", "author": "sukirman1901", "data_type": "official_public", "data": [tournament]}, f, indent=2, ensure_ascii=False)

    with open(teams_file, 'w', encoding='utf-8') as f:
        json.dump({"revdate": "2026-08-11", "author": "sukirman1901", "data_type": "official_public", "data": teams}, f, indent=2, ensure_ascii=False)

    with open(series_file, 'w', encoding='utf-8') as f:
        json.dump({"revdate": "2026-08-11", "author": "sukirman1901", "data_type": "official_public", "data": series}, f, indent=2, ensure_ascii=False)

    with open(matches_file, 'w', encoding='utf-8') as f:
        json.dump({"revdate": "2026-08-11", "author": "sukirman1901", "data_type": "official_public", "data": matches}, f, indent=2, ensure_ascii=False)

    print(f"\n✓ INGESTION COMPLETE!")
    print(f"  - Tournaments : 1 ({tournaments_file})")
    print(f"  - Teams       : {len(teams)} ({teams_file})")
    print(f"  - Series      : {len(series)} ({series_file})")
    print(f"  - Real Matches: {len(matches)} ({matches_file})")
    print("==========================================================")

if __name__ == '__main__':
    main()
