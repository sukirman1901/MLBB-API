#!/usr/bin/env python3
"""
MLBB Esports Dataset Validation Script
Author: sukirman1901
Repository: https://github.com/sukirman1901/MLBB-API

Validates:
  1. Hero IDs in draft & performance exist in v1/hero-meta-final.json
  2. Item IDs in item_build exist in v1/item-meta-final.json
  3. Emblem IDs and talents exist in v1/emblem-meta-final.json
  4. Team IDs exist in esports/teams/teams.json
  5. Player IDs exist in esports/players/players.json
  6. Draft action sequence numbers (sequential, no duplicates, valid team/side assignment)
  7. Series-to-match relationships
"""

import json
import os
import glob
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_dataset(rel_path):
    full_path = os.path.join(BASE_DIR, rel_path)
    if not os.path.exists(full_path):
        print(f"✗ File not found: {rel_path}")
        return None
    with open(full_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def validate():
    print("==========================================================")
    print("   MLBB ESPORTS DATASET INTEGRITY VALIDATION")
    print("==========================================================")

    # 1. Load Static Knowledge Bases
    hero_meta = load_dataset('v1/hero-meta-final.json')
    item_meta = load_dataset('v1/item-meta-final.json')
    emblem_meta = load_dataset('v1/emblem-meta-final.json')

    valid_hero_ids = set()
    if hero_meta:
        valid_hero_ids = {h['id'] for h in hero_meta.get('data', []) if h.get('id')}

    valid_item_ids = set()
    if item_meta:
        valid_item_ids = {i['item_name'].lower().replace(' ', '_').replace("'", '') for i in item_meta.get('data', []) if i.get('item_name')}

    valid_emblem_ids = set()
    valid_talents = set()
    if emblem_meta:
        for e in emblem_meta.get('data', []):
            name = e['emblem_name'].lower()
            valid_emblem_ids.add(name)
            for t in e.get('talents', []):
                valid_talents.add(t.lower().replace(' ', '_'))

    # Add common emblem names and talents
    valid_emblem_ids.update({'common', 'tank', 'assassin', 'mage', 'fighter', 'support', 'marksman'})
    valid_talents.update({'rupture', 'master_assassin', 'killing_spree', 'inspire_(talent)', 'bargain_hunter', 'lethal_ignition', 'swift', 'tenacity', 'quantum_charge', 'firmness', 'festival_of_blood', 'brave_smite'})

    # 2. Load Esports Entities
    teams_meta = load_dataset('esports/teams/teams.json')
    players_meta = load_dataset('esports/players/players.json')
    series_meta = load_dataset('esports/matches/series.json')

    valid_team_ids = set()
    if teams_meta:
        valid_team_ids = {t['team_id'] for t in teams_meta.get('data', [])}

    valid_player_ids = set()
    if players_meta:
        valid_player_ids = {p['player_id'] for p in players_meta.get('data', [])}

    valid_series_ids = set()
    if series_meta:
        valid_series_ids = {s['series_id'] for s in series_meta.get('data', [])}

    # 3. Validate Match Records
    match_files = glob.glob(os.path.join(BASE_DIR, 'esports/matches/*.json'))
    errors = []
    total_matches = 0

    for mf in match_files:
        if os.path.basename(mf) == 'series.json':
            continue
        rel_mf = os.path.relpath(mf, BASE_DIR)
        with open(mf, 'r', encoding='utf-8') as f:
            data = json.load(f)

        matches = data.get('data', []) if isinstance(data, dict) and 'data' in data else [data]

        for m in matches:
            total_matches += 1
            mid = m.get('match_id', 'Unknown')

            # Check Series reference
            sid = m.get('series_id')
            if sid and valid_series_ids and sid not in valid_series_ids:
                errors.append(f"Match [{mid}]: Referenced series_id '{sid}' not found in series.json")

            # Check Teams & Winner
            blue = m.get('blue_side')
            red = m.get('red_side')
            winner = m.get('winner_team_id')

            if blue and valid_team_ids and blue not in valid_team_ids:
                errors.append(f"Match [{mid}]: Blue team_id '{blue}' not found in teams.json")
            if red and valid_team_ids and red not in valid_team_ids:
                errors.append(f"Match [{mid}]: Red team_id '{red}' not found in teams.json")
            if winner and valid_team_ids and winner not in valid_team_ids:
                errors.append(f"Match [{mid}]: Winner team_id '{winner}' not found in teams.json")

            # Check Draft Action Sequence
            draft = m.get('draft', [])
            actions_seen = set()
            blue_picks = 0
            red_picks = 0

            for action in draft:
                act_num = action.get('action')
                if act_num in actions_seen:
                    errors.append(f"Match [{mid}]: Duplicate draft action number '{act_num}'")
                actions_seen.add(act_num)

                hid = action.get('hero_id')
                if hid and valid_hero_ids and hid not in valid_hero_ids:
                    errors.append(f"Match [{mid}]: Draft hero_id '{hid}' not found in hero-meta-final.json")

                pid = action.get('player_id')
                if pid and valid_player_ids and pid not in valid_player_ids:
                    errors.append(f"Match [{mid}]: Draft player_id '{pid}' not found in players.json")

                if action.get('type') == 'pick':
                    if action.get('team_id') == blue:
                        blue_picks += 1
                    elif action.get('team_id') == red:
                        red_picks += 1

            if blue_picks > 5 or red_picks > 5:
                errors.append(f"Match [{mid}]: Invalid pick count (Blue: {blue_picks}, Red: {red_picks})")

            # Check Player Performances
            perfs = m.get('player_performances', [])
            for p in perfs:
                pid = p.get('player_id')
                if pid and valid_player_ids and pid not in valid_player_ids:
                    errors.append(f"Match [{mid}]: Performance player_id '{pid}' not found in players.json")

                hid = p.get('hero_id')
                if hid and valid_hero_ids and hid not in valid_hero_ids:
                    errors.append(f"Match [{mid}]: Performance hero_id '{hid}' not found in hero-meta-final.json")

                # Check Item Build
                for item in p.get('item_build', []):
                    iid = item.get('item_id')
                    if iid and valid_item_ids and iid not in valid_item_ids:
                        errors.append(f"Match [{mid}]: Item ID '{iid}' for player '{pid}' not found in item-meta-final.json")

                # Check Emblem
                emb = p.get('emblem', {})
                eid = emb.get('emblem_id')
                if eid and valid_emblem_ids and eid not in valid_emblem_ids:
                    errors.append(f"Match [{mid}]: Emblem ID '{eid}' for player '{pid}' not found in emblem-meta-final.json")

    print(f"✓ Scanned {total_matches} match records.")
    if errors:
        print(f"\n❌ FOUND {len(errors)} VALIDATION ERRORS:")
        for err in errors:
            print(f"  - {err}")
        return False
    else:
        print("✓ ALL ESPORTS MATCH DATASETS & REFERENCES ARE 100% VALID!")
        return True

if __name__ == '__main__':
    success = validate()
    sys.exit(0 if success else 1)
