#!/usr/bin/env python3
"""
MLBB Draft State Dataset Builder V1
Author: sukirman1901
Repository: https://github.com/sukirman1901/MLBB-API

Transforms chronological match draft actions into explicit state/action transitions:
  - Input: esports/matches/m5_knockout_matches.json
  - Output: esports/draft_states/m5_knockout_draft_states.json
  - Summary: analytics/output/draft_state_coverage.json

Enforces Draft State Invariants:
  1. state_before == previous state_after (for state 1..N)
  2. state_after == apply(state_before, action)
  3. No duplicate pick, no duplicate ban, no pick of banned hero
  4. Available heroes = canonical_heroes - picked - banned (deterministic)
"""

import json
import os
import sys
from typing import Dict, List, Tuple, Optional, Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DRAFT_STATES_DIR = os.path.join(BASE_DIR, 'esports/draft_states')
ANALYTICS_OUTPUT_DIR = os.path.join(BASE_DIR, 'analytics/output')

def load_data():
    heroes_path = os.path.join(BASE_DIR, 'v1/hero-meta-final.json')
    matches_path = os.path.join(BASE_DIR, 'esports/matches/m5_knockout_matches.json')

    with open(heroes_path, 'r', encoding='utf-8') as f:
        heroes_data = json.load(f).get('data', [])
        all_canonical_hero_ids = sorted([h['id'] for h in heroes_data if h.get('id') and h['id'] != 'default'])

    with open(matches_path, 'r', encoding='utf-8') as f:
        matches = json.load(f).get('data', [])

    return all_canonical_hero_ids, matches

def build_states_for_match(m: Dict, all_canonical_hero_ids: List[str]) -> Tuple[List[Dict], int]:
    """Transforms one match's chronological draft actions into explicit state transition objects"""
    match_id = m['match_id']
    series_id = m['series_id']
    t_id = m['tournament_id']
    stage = m['stage']
    game_num = m['game_number']
    date_iso = m.get('date_iso', m.get('date'))
    patch_ctx = m.get('patch_context', {})
    
    t_a = m['team_a']
    t_b = m['team_b']
    blue_side = m['blue_side']
    red_side = m['red_side']
    winner_team_id = m['winner_team_id']

    draft = m.get('draft', [])
    total_actions = len(draft)
    state_records = []

    # Current accumulators
    blue_picks = []
    blue_bans = []
    red_picks = []
    red_bans = []

    # Detect dynamic first pick & first ban chronological actions
    first_ban_action_num = next((a['action'] for a in draft if a['type'] == 'ban'), None)
    first_pick_action_num = next((a['action'] for a in draft if a['type'] == 'pick'), None)

    for idx, act in enumerate(draft):
        action_num = act['action']
        phase = act.get('phase', 1)
        atype = act['type']
        acting_team = act['team_id']
        hid = act['hero_id']

        acting_side = "blue" if acting_team == blue_side else "red"
        opponent_team = red_side if acting_side == "blue" else blue_side

        # Flags
        is_first_ban = (action_num == first_ban_action_num)
        is_first_pick = (action_num == first_pick_action_num)
        
        # Response pick flag (previous action was opponent pick)
        is_response_pick = False
        if idx > 0 and atype == 'pick':
            prev_act = draft[idx - 1]
            if prev_act['type'] == 'pick' and prev_act['team_id'] != acting_team:
                is_response_pick = True

        # State Before (Deep Copy)
        state_before = {
            "blue": {"picks": list(blue_picks), "bans": list(blue_bans)},
            "red": {"picks": list(red_picks), "bans": list(red_bans)}
        }

        team_relative_before = {
            "acting_team": {"picks": list(state_before[acting_side]["picks"]), "bans": list(state_before[acting_side]["bans"])},
            "opponent_team": {"picks": list(state_before["red" if acting_side == "blue" else "blue"]["picks"]), "bans": list(state_before["red" if acting_side == "blue" else "blue"]["bans"])}
        }

        # Available Hero Set
        picked_set = set(blue_picks) | set(red_picks)
        banned_set = set(blue_bans) | set(red_bans)

        # Invariant Check: No double pick, no double ban, no pick after ban
        if hid != 'default':
            if hid in picked_set or hid in banned_set:
                raise ValueError(f"Hero state invariant violated in {match_id} action {action_num}: {hid} already picked/banned!")

        available_heroes = [h for h in all_canonical_hero_ids if h not in picked_set and h not in banned_set]

        # Apply Action to get State After
        if acting_side == "blue":
            if atype == "pick":
                blue_picks.append(hid)
            else:
                blue_bans.append(hid)
        else:
            if atype == "pick":
                red_picks.append(hid)
            else:
                red_bans.append(hid)

        state_after = {
            "blue": {"picks": list(blue_picks), "bans": list(blue_bans)},
            "red": {"picks": list(red_picks), "bans": list(red_bans)}
        }

        team_relative_after = {
            "acting_team": {"picks": list(state_after[acting_side]["picks"]), "bans": list(state_after[acting_side]["bans"])},
            "opponent_team": {"picks": list(state_after["red" if acting_side == "blue" else "blue"]["picks"]), "bans": list(state_after["red" if acting_side == "blue" else "blue"]["bans"])}
        }

        state_id = f"{match_id}-state-{action_num}"

        record = {
            "state_id": state_id,
            "match_id": match_id,
            "series_id": series_id,
            "tournament_id": t_id,
            "stage": stage,
            "game_number": game_num,
            "date_iso": date_iso,
            "patch_context": patch_ctx,
            "team_a": t_a,
            "team_b": t_b,
            "blue_side": blue_side,
            "red_side": red_side,
            "winner_team_id": winner_team_id,

            "action_number": action_num,
            "phase": phase,
            "action_type": atype,
            "acting_team": acting_team,
            "acting_side": acting_side,
            "opponent_team": opponent_team,

            "is_first_pick": is_first_pick,
            "is_first_ban": is_first_ban,
            "is_response_pick": is_response_pick,

            "blue_pick_count": len(state_before["blue"]["picks"]),
            "blue_ban_count": len(state_before["blue"]["bans"]),
            "red_pick_count": len(state_before["red"]["picks"]),
            "red_ban_count": len(state_before["red"]["bans"]),
            "total_picks": len(state_before["blue"]["picks"]) + len(state_before["red"]["picks"]),
            "total_bans": len(state_before["blue"]["bans"]) + len(state_before["red"]["bans"]),
            "remaining_pick_slots": 10 - (len(state_before["blue"]["picks"]) + len(state_before["red"]["picks"])),
            "remaining_ban_slots": 10 - (len(state_before["blue"]["bans"]) + len(state_before["red"]["bans"])),

            "state_before": state_before,
            "team_relative_before": team_relative_before,

            "action": {
                "type": atype,
                "team_id": acting_team,
                "hero_id": hid
            },

            "state_after": state_after,
            "team_relative_after": team_relative_after,

            "available_heroes": available_heroes,

            "observed_outcome": {
                "winner_team_id": winner_team_id,
                "acting_team_won": (acting_team == winner_team_id)
            }
        }

        state_records.append(record)

    return state_records, total_actions

def main():
    print("==========================================================")
    print("   MLBB DRAFT STATE DATASET BUILDER V1")
    print("==========================================================")

    os.makedirs(DRAFT_STATES_DIR, exist_ok=True)
    os.makedirs(ANALYTICS_OUTPUT_DIR, exist_ok=True)

    all_canonical_hero_ids, matches = load_data()
    total_matches = len(matches)

    all_draft_states = []
    match_state_counts = []
    validation_errors = 0

    for m in matches:
        try:
            states, count = build_states_for_match(m, all_canonical_hero_ids)
            all_draft_states.extend(states)
            match_state_counts.append(count)
        except Exception as e:
            print(f"✗ Validation Error in match {m['match_id']}: {e}")
            validation_errors += 1

    total_states = len(all_draft_states)
    min_states = min(match_state_counts) if match_state_counts else 0
    max_states = max(match_state_counts) if match_state_counts else 0
    avg_states = round(total_states / total_matches, 2) if total_matches > 0 else 0.0

    # Output Draft States Dataset
    output_file = os.path.join(DRAFT_STATES_DIR, 'm5_knockout_draft_states.json')
    dataset = {
        "revdate": "2026-08-11",
        "author": "sukirman1901",
        "description": "M5 Knockout Stage Chronological Draft State Transition Dataset V1",
        "total_states": total_states,
        "data": all_draft_states
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)

    print(f"✓ Created Draft State Dataset: {output_file}")
    print(f"  • Total Matches Processed : {total_matches}")
    print(f"  • Total Draft States      : {total_states}")
    print(f"  • Min States / Match      : {min_states}")
    print(f"  • Max States / Match      : {max_states}")
    print(f"  • Avg States / Match      : {avg_states}")

    # Output Coverage Summary
    coverage_file = os.path.join(ANALYTICS_OUTPUT_DIR, 'draft_state_coverage.json')
    coverage = {
        "matches": total_matches,
        "draft_states": total_states,
        "average_states_per_match": avg_states,
        "min_states": min_states,
        "max_states": max_states,
        "complete_state_transitions": total_states,
        "validation_errors": validation_errors
    }

    with open(coverage_file, 'w', encoding='utf-8') as f:
        json.dump(coverage, f, indent=2, ensure_ascii=False)

    print(f"✓ Created State Coverage Summary: {coverage_file}")
    print("==========================================================")

if __name__ == '__main__':
    main()
