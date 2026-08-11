#!/usr/bin/env python3
"""
Descriptive MLBB Match Analytics Engine
Author: sukirman1901
Repository: https://github.com/sukirman1901/MLBB-API

Calculates observed descriptive statistics across ingested real esports matches:
  1. Hero Pick/Ban Priority, Pick Rate, Ban Rate, Win Rate
  2. First-Pick Win Rate & Side Advantage (Blue vs Red)
  3. Team Hero Preferences & Win Rates
"""

import json
import os
from collections import defaultdict
from typing import Dict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def load_data():
    matches_path = os.path.join(BASE_DIR, 'esports/matches/m5_knockout_matches.json')
    heroes_path = os.path.join(BASE_DIR, 'v1/hero-meta-final.json')

    with open(matches_path, 'r', encoding='utf-8') as f:
        matches = json.load(f)['data']

    with open(heroes_path, 'r', encoding='utf-8') as f:
        heroes = json.load(f)['data']

    hero_names = {h['id']: h['hero_name'] for h in heroes if h.get('id')}
    return matches, hero_names

def run_analysis():
    matches, hero_names = load_data()
    total_matches = len(matches)

    print("==========================================================")
    print(f"   REAL MLBB ESPORTS MATCH ANALYTICS ({total_matches} REAL GAMES)")
    print("==========================================================")

    # 1. Side Advantage
    blue_wins = sum(1 for m in matches if m['winner_team_id'] == m['blue_side'])
    red_wins = total_matches - blue_wins
    print(f"\n[1] SIDE ADVANTAGE (BLUE vs RED)")
    print(f"  • Blue Side Win Rate: {blue_wins}/{total_matches} ({blue_wins/total_matches*100:.1f}%)")
    print(f"  • Red Side Win Rate : {red_wins}/{total_matches} ({red_wins/total_matches*100:.1f}%)")

    # 2. Hero Pick/Ban/Win Statistics
    hero_picks = defaultdict(int)
    hero_bans = defaultdict(int)
    hero_wins = defaultdict(int)

    # First Pick Stats
    first_pick_total = 0
    first_pick_wins = 0

    for m in matches:
        winner = m['winner_team_id']
        draft = m.get('draft', [])

        # Check Action 5 (First Pick)
        picks = [a for a in draft if a['type'] == 'pick']
        if picks:
            first_pick = picks[0]
            first_pick_total += 1
            if first_pick['team_id'] == winner:
                first_pick_wins += 1

        # Track Picks & Bans
        for action in draft:
            hid = action['hero_id']
            team = action['team_id']
            act_type = action['type']

            if act_type == 'pick':
                hero_picks[hid] += 1
                if team == winner:
                    hero_wins[hid] += 1
            elif act_type == 'ban':
                hero_bans[hid] += 1

    if first_pick_total > 0:
        print(f"\n[2] FIRST-PICK ADVANTAGE")
        print(f"  • First-Pick Win Rate: {first_pick_wins}/{first_pick_total} ({first_pick_wins/first_pick_total*100:.1f}%)")

    # Top Picked & Banned Heroes
    print(f"\n[3] TOP CONTESTED HEROES (Picks, Bans & Win Rates)")
    all_heroes = set(hero_picks.keys()) | set(hero_bans.keys())

    stats = []
    for hid in all_heroes:
        name = hero_names.get(hid, hid)
        p_count = hero_picks[hid]
        b_count = hero_bans[hid]
        w_count = hero_wins[hid]
        pb_count = p_count + b_count
        pb_rate = (pb_count / total_matches) * 100
        win_rate = (w_count / p_count * 100) if p_count > 0 else 0.0
        stats.append((name, pb_count, pb_rate, p_count, b_count, win_rate))

    stats.sort(key=lambda x: x[1], reverse=True)

    print(f"  {'Hero':<16} | {'P+B Count':<10} | {'P+B Rate':<10} | {'Picks':<6} | {'Bans':<6} | {'Win Rate':<8}")
    print("  " + "-"*65)
    for row in stats[:15]:
        print(f"  {row[0]:<16} | {row[1]:<10} | {row[2]:<9.1f}% | {row[3]:<6} | {row[4]:<6} | {row[5]:<7.1f}%")

    print("\n==========================================================")

if __name__ == '__main__':
    run_analysis()
