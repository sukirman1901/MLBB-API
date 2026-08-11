#!/usr/bin/env python3
"""
MLBB Patch & Meta Tracing Engine V1
Author: sukirman1901
Repository: https://github.com/sukirman1901/MLBB-API

Tracks hero competitive priority shifts across patches and tournaments:
  1. Hero Patch Priority & Contest Rate Trends
  2. Emerging Hero Signals (Detecting positive contest rate deltas >= +15%)
  3. Changelog Linkage (Connecting hero buffs/nerfs to competitive priority shifts)
  4. Exposes explicit sample sizes and sample_sufficient flags
  5. Exports JSON datasets to analytics/output/meta/
"""

import json
import os
from collections import defaultdict
from typing import Dict, List, Tuple

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
META_OUTPUT_DIR = os.path.join(BASE_DIR, 'analytics/output/meta')

MINIMUM_SAMPLE_SIZE = 5

def load_data():
    matches_path = os.path.join(BASE_DIR, 'esports/matches/m5_knockout_matches.json')
    heroes_path = os.path.join(BASE_DIR, 'v1/hero-meta-final.json')
    patches_path = os.path.join(BASE_DIR, 'patches/patches.json')
    changelog_path = os.path.join(BASE_DIR, 'patches/changelogs/patch_1_8_44.json')

    with open(matches_path, 'r', encoding='utf-8') as f:
        matches = json.load(f)['data']

    with open(heroes_path, 'r', encoding='utf-8') as f:
        heroes = json.load(f)['data']

    with open(patches_path, 'r', encoding='utf-8') as f:
        patches = json.load(f)['data']

    changelog = {}
    if os.path.exists(changelog_path):
        with open(changelog_path, 'r', encoding='utf-8') as f:
            changelog_data = json.load(f)
            changelog = {adj['hero_id']: adj for adj in changelog_data.get('hero_adjustments', [])}

    hero_meta = {h['id']: h for h in heroes if h.get('id')}
    return matches, hero_meta, patches, changelog

def run_meta_tracing():
    os.makedirs(META_OUTPUT_DIR, exist_ok=True)
    matches, hero_meta, patches, changelog = load_data()
    total_games = len(matches)

    # 1. Group Matches by Patch
    patch_matches = defaultdict(list)
    for m in matches:
        patch_ver = m.get('patch', '1.8.44')
        patch_matches[patch_ver].append(m)

    # Historical baseline contest rates from prior patch (Patch 1.8.30 baseline reference)
    baseline_contest_rates = {
        "h122": 0.40,  # Nolan (was 40% in qualifying)
        "h079": 0.25,  # Guinevere (was 25% before buff)
        "h089": 0.65,  # Wanwan
        "h066": 0.60,  # Faramis
        "h110": 0.70,  # Valentina
        "h108": 0.85   # Joy
    }

    hero_trends = []
    emerging_signals = []

    for patch_ver, games in patch_matches.items():
        patch_game_count = len(games)
        hero_picks = defaultdict(int)
        hero_bans = defaultdict(int)
        hero_wins = defaultdict(int)

        for m in games:
            winner = m['winner_team_id']
            for action in m.get('draft', []):
                hid = action['hero_id']
                team = action['team_id']
                act_type = action['type']

                if act_type == 'pick':
                    hero_picks[hid] += 1
                    if team == winner:
                        hero_wins[hid] += 1
                elif act_type == 'ban':
                    hero_bans[hid] += 1

        all_heroes = set(hero_picks.keys()) | set(hero_bans.keys())

        for hid in all_heroes:
            meta = hero_meta.get(hid, {})
            name = meta.get('hero_name', hid)
            p_cnt = hero_picks[hid]
            b_cnt = hero_bans[hid]
            c_cnt = p_cnt + b_cnt
            wins = hero_wins[hid]
            losses = p_cnt - wins

            p_rate = round(p_cnt / patch_game_count, 4)
            b_rate = round(b_cnt / patch_game_count, 4)
            c_rate = round(c_cnt / patch_game_count, 4)
            wr = round(wins / p_cnt, 4) if p_cnt > 0 else None

            prior_rate = baseline_contest_rates.get(hid, 0.30)
            delta = round(c_rate - prior_rate, 4)

            adjustment = changelog.get(hid)
            adj_type = adjustment.get('type') if adjustment else "unchanged"
            adj_summary = adjustment.get('summary') if adjustment else "No direct patch changes noted."

            trend_record = {
                "hero_id": hid,
                "hero_name": name,
                "patch": patch_ver,
                "patch_source": "inferred",
                "total_patch_games": patch_game_count,
                "pick_count": p_cnt,
                "ban_count": b_cnt,
                "contest_count": c_cnt,
                "pick_rate": p_rate,
                "ban_rate": b_rate,
                "contest_rate": c_rate,
                "prior_patch_contest_rate": prior_rate,
                "contest_rate_delta": delta,
                "wins": wins,
                "losses": losses,
                "win_rate": wr,
                "sample_size": p_cnt,
                "sample_sufficient": (p_cnt >= MINIMUM_SAMPLE_SIZE),
                "patch_adjustment": {
                    "type": adj_type,
                    "summary": adj_summary
                }
            }
            hero_trends.append(trend_record)

            # Detect Emerging Hero Signal (+delta >= +0.15 and contest_rate >= 0.70)
            if delta >= 0.15 and c_rate >= 0.70:
                emerging_signals.append({
                    "hero_id": hid,
                    "hero_name": name,
                    "patch": patch_ver,
                    "signal_type": "EMERGING_CONTEST_PRIORITY",
                    "prior_contest_rate": prior_rate,
                    "current_contest_rate": c_rate,
                    "delta": delta,
                    "sample_size": p_cnt,
                    "sample_sufficient": (p_cnt >= MINIMUM_SAMPLE_SIZE),
                    "patch_adjustment": {
                        "type": adj_type,
                        "summary": adj_summary
                    }
                })

    hero_trends.sort(key=lambda x: x["contest_rate"], reverse=True)
    emerging_signals.sort(key=lambda x: x["delta"], reverse=True)

    # Exports
    with open(os.path.join(META_OUTPUT_DIR, 'patch_timeline.json'), 'w', encoding='utf-8') as f:
        json.dump({"data": patches}, f, indent=2, ensure_ascii=False)

    with open(os.path.join(META_OUTPUT_DIR, 'hero_patch_trends.json'), 'w', encoding='utf-8') as f:
        json.dump({"data": hero_trends}, f, indent=2, ensure_ascii=False)

    with open(os.path.join(META_OUTPUT_DIR, 'emerging_signals.json'), 'w', encoding='utf-8') as f:
        json.dump({"minimum_delta_threshold": 0.15, "data": emerging_signals}, f, indent=2, ensure_ascii=False)

    # Print Console Summary
    print("\n==========================================================")
    print("   MLBB META TRACING ENGINE V1")
    print(f"   PATCH 1.8.44 ANALYSIS ({total_games} REAL GAMES)")
    print("==========================================================")

    print("\n[1] DETECTED EMERGING HERO SIGNALS (Priority Shifts >= +15%)")
    print(f"  {'Hero':<16} | {'Prior Contest':<14} | {'M5 Contest':<12} | {'Delta':<8} | {'Patch Adjustment':<10}")
    print("  " + "-"*75)
    for es in emerging_signals:
        d_str = f"+{es['delta']*100:.1f}%"
        print(f"  {es['hero_name']:<16} | {es['prior_contest_rate']*100:<13.1f}% | {es['current_contest_rate']*100:<11.1f}% | {d_str:<8} | {es['patch_adjustment']['type'].upper():<10}")

    print("\n[2] HERO PRIORITY vs PATCH ADJUSTMENT LINKAGE")
    print(f"  {'Hero':<16} | {'Contest Rate':<14} | {'Changelog Effect':<18} | {'Summary':<30}")
    print("  " + "-"*85)
    for rec in hero_trends[:10]:
        adj = rec['patch_adjustment']
        print(f"  {rec['hero_name']:<16} | {rec['contest_rate']*100:<13.1f}% | {adj['type'].upper():<18} | {adj['summary'][:30]:<30}")

    print("\n==========================================================")

if __name__ == '__main__':
    run_meta_tracing()
