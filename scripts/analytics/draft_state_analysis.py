#!/usr/bin/env python3
"""
MLBB Statistical Draft-State Analytics V1
Author: sukirman1901
Repository: https://github.com/sukirman1901/MLBB-API

Analyzes observed draft state transitions without ML/causal claims:
  1. Response Pick Analysis (opponent_previous_pick -> our_response)
  2. Response Ban Analysis (opponent_pick -> next_ban)
  3. Pick After Ban Analysis (hero_banned -> next_pick)
  4. Non-causal terminology: "observed response", "observed win rate", "sample size"
"""

import json
import os
import sys
from collections import defaultdict
from typing import Dict, List, Tuple, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ANALYTICS_OUTPUT_DIR = os.path.join(BASE_DIR, 'analytics/output')

def load_data():
    states_path = os.path.join(BASE_DIR, 'esports/draft_states/m5_knockout_draft_states.json')
    heroes_path = os.path.join(BASE_DIR, 'v1/hero-meta-final.json')

    with open(states_path, 'r', encoding='utf-8') as f:
        states = json.load(f).get('data', [])

    hero_names = {}
    if os.path.exists(heroes_path):
        with open(heroes_path, 'r', encoding='utf-8') as f:
            for h in json.load(f).get('data', []):
                if h.get('id'):
                    hero_names[h['id']] = h.get('hero_name', h['id'])

    return states, hero_names

def run_draft_state_analytics():
    print("==========================================================")
    print("   MLBB STATISTICAL DRAFT-STATE ANALYTICS V1")
    print("==========================================================")

    states, hero_names = load_data()
    total_states = len(states)

    response_pick_stats = defaultdict(lambda: {"count": 0, "wins": 0})
    response_ban_stats = defaultdict(int)
    pick_after_ban_stats = defaultdict(int)

    for i in range(1, total_states):
        prev = states[i-1]
        curr = states[i]

        # Match must be identical
        if prev['match_id'] != curr['match_id']:
            continue

        prev_act = prev['action']
        curr_act = curr['action']

        # 1. Response Pick Analysis (opponent_pick -> our_pick)
        if prev_act['type'] == 'pick' and curr_act['type'] == 'pick' and prev_act['team_id'] != curr_act['team_id']:
            opp_hero = prev_act['hero_id']
            resp_hero = curr_act['hero_id']
            key = (opp_hero, resp_hero)

            response_pick_stats[key]["count"] += 1
            if curr['observed_outcome']['acting_team_won']:
                response_pick_stats[key]["wins"] += 1

        # 2. Response Ban Analysis (opponent_pick -> next_ban)
        if prev_act['type'] == 'pick' and curr_act['type'] == 'ban':
            opp_hero = prev_act['hero_id']
            ban_hero = curr_act['hero_id']
            response_ban_stats[(opp_hero, ban_hero)] += 1

        # 3. Pick After Ban Analysis (hero_banned -> next_pick)
        if prev_act['type'] == 'ban' and curr_act['type'] == 'pick':
            banned_h = prev_act['hero_id']
            picked_h = curr_act['hero_id']
            pick_after_ban_stats[(banned_h, picked_h)] += 1

    # Format Response Pick Results
    response_picks_list = []
    for (opp_h, resp_h), data in response_pick_stats.items():
        n = data["count"]
        w = data["wins"]
        wr = round(w / n, 4) if n > 0 else 0.0
        response_picks_list.append({
            "opponent_hero_id": opp_h,
            "opponent_hero_name": hero_names.get(opp_h, opp_h),
            "response_hero_id": resp_h,
            "response_hero_name": hero_names.get(resp_h, resp_h),
            "observed_count": n,
            "observed_wins": w,
            "observed_win_rate": wr,
            "sample_size": n,
            "sample_sufficient": (n >= 5)
        })

    response_picks_list.sort(key=lambda x: x["observed_count"], reverse=True)

    # Format Response Ban Results
    response_bans_list = []
    for (opp_h, ban_h), cnt in response_ban_stats.items():
        response_bans_list.append({
            "opponent_hero_id": opp_h,
            "opponent_hero_name": hero_names.get(opp_h, opp_h),
            "next_ban_hero_id": ban_h,
            "next_ban_hero_name": hero_names.get(ban_h, ban_h),
            "observed_frequency": cnt
        })
    response_bans_list.sort(key=lambda x: x["observed_frequency"], reverse=True)

    # Format Pick After Ban Results
    pick_after_bans_list = []
    for (ban_h, pick_h), cnt in pick_after_ban_stats.items():
        pick_after_bans_list.append({
            "banned_hero_id": ban_h,
            "banned_hero_name": hero_names.get(ban_h, ban_h),
            "next_pick_hero_id": pick_h,
            "next_pick_hero_name": hero_names.get(pick_h, pick_h),
            "observed_frequency": cnt
        })
    pick_after_bans_list.sort(key=lambda x: x["observed_frequency"], reverse=True)

    # Save JSON Export
    os.makedirs(ANALYTICS_OUTPUT_DIR, exist_ok=True)
    export_data = {
        "description": "Descriptive Draft State Transition Analytics V1",
        "top_observed_response_picks": response_picks_list[:20],
        "top_observed_response_bans": response_bans_list[:20],
        "top_observed_picks_after_ban": pick_after_bans_list[:20]
    }

    output_file = os.path.join(ANALYTICS_OUTPUT_DIR, 'draft_state_analytics.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)

    print(f"✓ Saved analytics output: {output_file}\n")

    print("[1] TOP OBSERVED RESPONSE PICKS (Opponent Pick -> Response Pick)")
    print(f"  {'Opponent Hero':<16} -> {'Response Hero':<16} | {'Count':<6} | {'WR':<7} | {'Sufficient':<10}")
    print("  " + "-"*65)
    for rp in response_picks_list[:10]:
        suf = "✓ Yes" if rp["sample_sufficient"] else "⚠ Low"
        print(f"  {rp['opponent_hero_name']:<16} -> {rp['response_hero_name']:<16} | n={rp['observed_count']:<4} | {rp['observed_win_rate']*100:<5.1f}% | {suf:<10}")

    print("\n[2] TOP OBSERVED RESPONSE BANS (Opponent Pick -> Next Ban)")
    print(f"  {'Opponent Hero':<16} -> {'Next Ban Hero':<16} | {'Observed Frequency':<18}")
    print("  " + "-"*55)
    for rb in response_bans_list[:8]:
        print(f"  {rb['opponent_hero_name']:<16} -> {rb['next_ban_hero_name']:<16} | {rb['observed_frequency']:<18}")

    print("\n[3] TOP OBSERVED PICKS AFTER BAN (Banned Hero -> Next Pick)")
    print(f"  {'Banned Hero':<16} -> {'Next Pick Hero':<16} | {'Observed Frequency':<18}")
    print("  " + "-"*55)
    for pb in pick_after_bans_list[:8]:
        print(f"  {pb['banned_hero_name']:<16} -> {pb['next_pick_hero_name']:<16} | {pb['observed_frequency']:<18}")

    print("==========================================================")

if __name__ == '__main__':
    run_draft_state_analytics()
