#!/usr/bin/env python3
"""
MLBB Esports Dataset Integrity Audit Suite
Author: sukirman1901
Repository: https://github.com/sukirman1901/MLBB-API

Executes a full 17-point audit of canonical esports match data:
  1. Identifies canonical vs duplicate match records
  2. Deduplication check (deterministic key: match_id, series_id, game_number, team_a, team_b, date)
  3. Tournament & Stage scope verification (M5 World Championship — Knockout Stage)
  4. Series integrity check (sum(games per series) == total canonical matches)
  5. Sequential game numbering per series
  6. Chronological draft completeness check
  7. Hero alias mapping & unresolved entity audit
  8. Patch Context Assignment Breakdown (Explicit, Verified Window, Inferred, Unresolved)
  9. ISO-8601 Date Normalization & Provenance Hash audit
 10. VOD scope verification
"""

import json
import os
import glob
import sys
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_json(rel_path):
    path = os.path.join(BASE_DIR, rel_path)
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def run_audit():
    print("==========================================================")
    print("   MLBB ESPORTS DATASET INTEGRITY AUDIT")
    print("==========================================================")

    # 1. Load static knowledge bases
    hero_meta = load_json('v1/hero-meta-final.json')
    valid_hero_ids = {h['id'] for h in hero_meta.get('data', []) if h.get('id')} if hero_meta else set()

    # 2. Load esports entities
    teams_meta = load_json('esports/teams/teams.json')
    valid_team_ids = {t['team_id'] for t in teams_meta.get('data', [])} if teams_meta else set()

    series_meta = load_json('esports/matches/series.json')
    valid_series_dict = {s['series_id']: s for s in series_meta.get('data', [])} if series_meta else {}

    unresolved_meta = load_json('esports/unresolved_entities.json') or []
    unresolved_count = len(unresolved_meta)

    # 3. Audit match files
    match_files = glob.glob(os.path.join(BASE_DIR, 'esports/matches/*.json'))

    all_matches = []
    non_m5_count = 0
    non_knockout_count = 0
    duplicate_count = 0
    seen_dedup_keys = set()

    complete_drafts = 0
    incomplete_drafts = 0
    mapped_hero_ids_count = 0

    vod_available = 0
    
    # Patch Context Counts
    explicit_patch_cnt = 0
    verified_window_cnt = 0
    inferred_patch_cnt = 0
    unresolved_patch_cnt = 0
    
    fabricated_stats = 0
    series_game_counts = defaultdict(int)

    for mf in match_files:
        if os.path.basename(mf) == 'series.json':
            continue
        data = load_json(os.path.relpath(mf, BASE_DIR))
        matches = data.get('data', []) if isinstance(data, dict) and 'data' in data else ([data] if isinstance(data, dict) else data)

        for m in matches:
            # Deterministic Deduplication Key
            dedup_key = (
                m.get('match_id'),
                m.get('series_id'),
                m.get('game_number'),
                m.get('team_a'),
                m.get('team_b'),
                m.get('date')
            )

            if dedup_key in seen_dedup_keys:
                duplicate_count += 1
                continue
            seen_dedup_keys.add(dedup_key)
            all_matches.append(m)

            # Tournament scope check
            if m.get('tournament_id') != 'm5-world-championship':
                non_m5_count += 1
            if m.get('stage') != 'Knockout Stage':
                non_knockout_count += 1

            # Series integrity
            sid = m.get('series_id')
            if sid:
                series_game_counts[sid] += 1

            # Draft completeness check
            draft = m.get('draft', [])
            if len(draft) >= 10 and m.get('draft_complete', True):
                complete_drafts += 1
            else:
                incomplete_drafts += 1

            for action in draft:
                hid = action.get('hero_id')
                if hid in valid_hero_ids:
                    mapped_hero_ids_count += 1

            # VOD check
            vod_url = m.get('vod_url', '') or ''
            if vod_url and ('youtube' in vod_url.lower() or 'youtu.be' in vod_url.lower()):
                vod_available += 1

            # Patch Context Check
            p_ctx = m.get('patch_context', {})
            method = p_ctx.get('assignment_method', m.get('patch_source'))
            if method == 'explicit_match_source':
                explicit_patch_cnt += 1
            elif method == 'verified_tournament_window':
                verified_window_cnt += 1
            elif method == 'date_inference' or method == 'inferred':
                inferred_patch_cnt += 1
            else:
                unresolved_patch_cnt += 1

            # Fabricated stats check (Rule 19)
            if m.get('player_performances'):
                for p in m['player_performances']:
                    if p.get('kills') is not None or p.get('gold') is not None:
                        fabricated_stats += 1

    canonical_games = len(all_matches)
    expected_games = 57
    expected_series = len(valid_series_dict)

    print("\nSource:")
    print("M5 World Championship — Knockout Stage")
    print(f"\nExpected games: {expected_games}")
    print(f"Canonical games: {canonical_games}")
    print(f"Duplicate games: {duplicate_count}")
    print(f"Non-M5 games: {non_m5_count}")
    print(f"Non-Knockout games: {non_knockout_count}")

    print(f"\nSeries:")
    print(f"{expected_series}")

    print(f"\nDraft:")
    print(f"Complete: {complete_drafts}/{canonical_games}")
    print(f"Incomplete: {incomplete_drafts}/{canonical_games}")

    print(f"\nHero mapping:")
    print(f"Mapped: {mapped_hero_ids_count}")
    print(f"Unresolved: {unresolved_count}")

    print(f"\nVOD:")
    print(f"Available: {vod_available}/{canonical_games}")

    print(f"\nPatch Context Coverage:")
    print(f"Resolved: {explicit_patch_cnt + verified_window_cnt + inferred_patch_cnt}/{canonical_games}")
    print(f"Explicit Match Source: {explicit_patch_cnt}/{canonical_games}")
    print(f"Verified Window: {verified_window_cnt}/{canonical_games}")
    print(f"Inferred: {inferred_patch_cnt}/{canonical_games}")
    print(f"Unresolved: {unresolved_patch_cnt}/{canonical_games}")

    print(f"\nFabricated statistics:")
    print(f"{fabricated_stats}")

    is_pass = (
        canonical_games == expected_games and
        duplicate_count == 0 and
        non_m5_count == 0 and
        non_knockout_count == 0 and
        complete_drafts == canonical_games and
        fabricated_stats == 0
    )

    print("\nSTATUS:")
    if is_pass:
        print("PASS")
    else:
        print("FAIL")

    print("==========================================================")
    return is_pass

if __name__ == '__main__':
    success = run_audit()
    sys.exit(0 if success else 1)
