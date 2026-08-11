#!/usr/bin/env python3
"""
MLBB Patch & Meta Tracing Engine V1 (Statistically Honest & Provenance-Safe)
Author: sukirman1901
Repository: https://github.com/sukirman1901/MLBB-API

Strict Methodological Rules:
  1. NO synthetic/hardcoded baselines. Trends require >= 2 REAL observed competitive match periods.
  2. Single observed period results in trend_status = "INSUFFICIENT_HISTORY" and outputs a META SNAPSHOT.
  3. Exposes explicit data coverage report (analytics/output/meta/data_coverage.json).
  4. Keeps Layer A (Observed Data), Layer B (Static Patch Data), and Layer C (Derived Trend) strictly separate.
  5. Uses non-causal terminology ("co-occurred with", "observed alongside").
"""

import json
import os
from collections import defaultdict
from typing import Dict, List, Tuple, Optional, Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
META_OUTPUT_DIR = os.path.join(BASE_DIR, 'analytics/output/meta')

MINIMUM_PERIOD_GAMES = 10
MINIMUM_DELTA_THRESHOLD = 0.15

def load_data():
    matches_path = os.path.join(BASE_DIR, 'esports/matches/m5_knockout_matches.json')
    heroes_path = os.path.join(BASE_DIR, 'v1/hero-meta-final.json')
    patches_path = os.path.join(BASE_DIR, 'patches/patches.json')
    changelog_path = os.path.join(BASE_DIR, 'patches/changelogs/patch_1_8_44.json')

    matches = []
    if os.path.exists(matches_path):
        with open(matches_path, 'r', encoding='utf-8') as f:
            matches = json.load(f).get('data', [])

    heroes = []
    if os.path.exists(heroes_path):
        with open(heroes_path, 'r', encoding='utf-8') as f:
            heroes = json.load(f).get('data', [])

    patches = []
    if os.path.exists(patches_path):
        with open(patches_path, 'r', encoding='utf-8') as f:
            patches = json.load(f).get('data', [])

    changelog = {}
    if os.path.exists(changelog_path):
        with open(changelog_path, 'r', encoding='utf-8') as f:
            changelog_data = json.load(f)
            changelog = {adj['hero_id']: adj for adj in changelog_data.get('hero_adjustments', [])}

    hero_meta = {h['id']: h for h in heroes if h.get('id')}
    return matches, hero_meta, patches, changelog

def calculate_period_stats(games: List[Dict], hero_meta: Dict) -> Dict[str, Dict]:
    """Calculate Layer A Observed Competitive Data for a set of matches"""
    total_games = len(games)
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
    period_stats = {}

    for hid in all_heroes:
        name = hero_meta.get(hid, {}).get('hero_name', hid)
        p_cnt = hero_picks[hid]
        b_cnt = hero_bans[hid]
        c_cnt = p_cnt + b_cnt
        wins = hero_wins[hid]
        losses = p_cnt - wins

        p_rate = round(p_cnt / total_games, 4) if total_games > 0 else 0.0
        b_rate = round(b_cnt / total_games, 4) if total_games > 0 else 0.0
        c_rate = round(c_cnt / total_games, 4) if total_games > 0 else 0.0
        wr = round(wins / p_cnt, 4) if p_cnt > 0 else None

        period_stats[hid] = {
            "hero_id": hid,
            "hero_name": name,
            "total_games": total_games,
            "pick_count": p_cnt,
            "ban_count": b_cnt,
            "contest_count": c_cnt,
            "pick_rate": p_rate,
            "ban_rate": b_rate,
            "contest_rate": c_rate,
            "wins": wins,
            "losses": losses,
            "win_rate": wr,
            "sample_size": p_cnt,
            "sample_sufficient": (p_cnt >= 5)
        }

    return period_stats

def run_meta_tracing():
    os.makedirs(META_OUTPUT_DIR, exist_ok=True)
    matches, hero_meta, patches, changelog = load_data()
    total_matches = len(matches)

    # 1. Group Matches by Period (Tournament + Patch)
    periods = defaultdict(list)
    for m in matches:
        period_key = f"{m.get('tournament_id', 'unknown')}:{m.get('patch', 'unknown')}"
        periods[period_key].append(m)

    sorted_period_keys = sorted(periods.keys())
    num_periods = len(sorted_period_keys)
    historical_comparison_available = (num_periods >= 2)

    # 2. Dynamic Data Coverage Report
    unique_tournaments = len(set(m.get('tournament_id') for m in matches if m.get('tournament_id')))
    unique_patches = len(set(m.get('patch') for m in matches if m.get('patch')))
    unique_heroes = len(set(a['hero_id'] for m in matches for a in m.get('draft', [])))

    data_coverage = {
        "patches_observed": unique_patches,
        "matches_observed": total_matches,
        "tournaments_observed": unique_tournaments,
        "heroes_observed": unique_heroes,
        "competitive_periods_observed": num_periods,
        "historical_comparison_available": historical_comparison_available
    }

    hero_trends = []
    emerging_signals = []

    # 3. Analyze Current Period
    current_period_key = sorted_period_keys[-1] if sorted_period_keys else "none"
    current_games = periods[current_period_key] if current_period_key != "none" else []
    current_stats = calculate_period_stats(current_games, hero_meta)

    previous_stats = {}
    prev_period_key = None

    if historical_comparison_available:
        prev_period_key = sorted_period_keys[-2]
        prev_games = periods[prev_period_key]
        if len(prev_games) >= MINIMUM_PERIOD_GAMES:
            previous_stats = calculate_period_stats(prev_games, hero_meta)

    for hid, c_data in current_stats.items():
        name = c_data["hero_name"]
        curr_c_rate = c_data["contest_rate"]

        adj = changelog.get(hid)
        adj_type = adj.get('type') if adj else "unchanged"
        adj_summary = adj.get('summary') if adj else "No direct patch changes noted."

        if prev_period_key and hid in previous_stats and len(periods[prev_period_key]) >= MINIMUM_PERIOD_GAMES:
            prev_c_rate = previous_stats[hid]["contest_rate"]
            delta = round(curr_c_rate - prev_c_rate, 4)

            if delta >= MINIMUM_DELTA_THRESHOLD:
                trend_status = "OBSERVED_INCREASE"
                emerging_signals.append({
                    "hero_id": hid,
                    "hero_name": name,
                    "previous_period": prev_period_key,
                    "current_period": current_period_key,
                    "signal_type": "EMERGING_CONTEST_PRIORITY",
                    "previous_observed_contest_rate": prev_c_rate,
                    "current_observed_contest_rate": curr_c_rate,
                    "delta_percentage_points": delta,
                    "previous_period_sample": len(periods[prev_period_key]),
                    "current_period_sample": c_data["total_games"],
                    "sample_sufficient": (c_data["sample_size"] >= 5 and len(periods[prev_period_key]) >= MINIMUM_PERIOD_GAMES),
                    "patch_adjustment_linkage": {
                        "type": adj_type,
                        "summary": adj_summary
                    }
                })
            elif delta <= -MINIMUM_DELTA_THRESHOLD:
                trend_status = "OBSERVED_DECREASE"
            else:
                trend_status = "STABLE"

            trend_record = {
                "hero_id": hid,
                "hero_name": name,
                "current_period": current_period_key,
                "previous_period": prev_period_key,
                "baseline_source": "observed_match_data",
                "layer_a_observed_stats": c_data,
                "layer_b_static_patch": {
                    "patch": current_period_key.split(':')[-1],
                    "patch_source": "inferred",
                    "adjustment_type": adj_type,
                    "summary": adj_summary
                },
                "layer_c_derived_trend": {
                    "previous_observed_contest_rate": prev_c_rate,
                    "current_observed_contest_rate": curr_c_rate,
                    "delta_percentage_points": delta,
                    "trend_status": trend_status
                }
            }
        else:
            # Insufficient Historical Coverage (1 Period Observed)
            trend_record = {
                "hero_id": hid,
                "hero_name": name,
                "current_period": current_period_key,
                "previous_period": None,
                "baseline_source": "none",
                "layer_a_observed_stats": c_data,
                "layer_b_static_patch": {
                    "patch": current_period_key.split(':')[-1],
                    "patch_source": "inferred",
                    "adjustment_type": adj_type,
                    "summary": adj_summary
                },
                "layer_c_derived_trend": {
                    "previous_observed_contest_rate": None,
                    "current_observed_contest_rate": curr_c_rate,
                    "delta_percentage_points": None,
                    "trend_status": "INSUFFICIENT_HISTORY"
                }
            }

        hero_trends.append(trend_record)

    hero_trends.sort(key=lambda x: x["layer_a_observed_stats"]["contest_rate"], reverse=True)
    emerging_signals.sort(key=lambda x: x["delta_percentage_points"], reverse=True)

    # 4. Save JSON Exports
    with open(os.path.join(META_OUTPUT_DIR, 'data_coverage.json'), 'w', encoding='utf-8') as f:
        json.dump(data_coverage, f, indent=2, ensure_ascii=False)

    with open(os.path.join(META_OUTPUT_DIR, 'patch_timeline.json'), 'w', encoding='utf-8') as f:
        json.dump({"data": patches}, f, indent=2, ensure_ascii=False)

    with open(os.path.join(META_OUTPUT_DIR, 'hero_patch_trends.json'), 'w', encoding='utf-8') as f:
        json.dump({"data_coverage": data_coverage, "data": hero_trends}, f, indent=2, ensure_ascii=False)

    with open(os.path.join(META_OUTPUT_DIR, 'emerging_signals.json'), 'w', encoding='utf-8') as f:
        json.dump({"historical_comparison_available": historical_comparison_available, "data": emerging_signals}, f, indent=2, ensure_ascii=False)

    # 5. Print Methodologically Honest Terminal Report
    print("\n==========================================================")
    print("   MLBB META TRACING ENGINE V1")
    print("==========================================================")
    print(f"Observed competitive periods  : {num_periods}")
    print(f"Historical comparison periods : {num_periods - 1 if num_periods > 0 else 0}")
    print("----------------------------------------------------------")

    if not historical_comparison_available:
        print("\nSTATUS:")
        print("INSUFFICIENT HISTORICAL COVERAGE (Meta Snapshot Mode)")
        print("\n[!] Note: Trends and Emergence Signals require >= 2 real competitive match periods.")
        print("    Displaying Current M5 Priority Snapshot (Patch 1.8.44 [inferred]):")

        print(f"\n  {'Hero':<16} | {'Picks':<5} | {'Bans':<5} | {'Contest Rate':<14} | {'Status':<22} | {'Patch Adjustment Linkage':<25}")
        print("  " + "-"*92)
        for tr in hero_trends[:15]:
            st = tr["layer_a_observed_stats"]
            adj = tr["layer_b_static_patch"]
            c_str = f"{st['contest_rate']*100:.1f}%"
            print(f"  {tr['hero_name']:<16} | {st['pick_count']:<5} | {st['ban_count']:<5} | {c_str:<14} | {tr['layer_c_derived_trend']['trend_status']:<22} | {adj['adjustment_type'].upper():<25}")

    else:
        print("\nSTATUS:")
        print("HISTORICAL TREND COMPARISON AVAILABLE")
        print("\n[1] DETECTED EMERGING HERO SIGNALS (Delta >= +15 percentage points)")
        print(f"  {'Hero':<16} | {'Prev Contest':<14} | {'Current Contest':<15} | {'Delta':<8} | {'Adjustment Linkage':<20}")
        print("  " + "-"*80)
        for es in emerging_signals:
            d_str = f"+{es['delta_percentage_points']*100:.1f} pts"
            print(f"  {es['hero_name']:<16} | {es['previous_observed_contest_rate']*100:<13.1f}% | {es['current_observed_contest_rate']*100:<14.1f}% | {d_str:<8} | {es['patch_adjustment_linkage']['type'].upper():<20}")

    print("\n==========================================================")

if __name__ == '__main__':
    run_meta_tracing()
