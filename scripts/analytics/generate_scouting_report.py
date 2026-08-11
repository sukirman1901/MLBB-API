#!/usr/bin/env python3
"""
MLBB CLI Scouting Report Generator V1
Author: sukirman1901
Repository: https://github.com/sukirman1901/MLBB-API

Generates structured team scouting reports from the Scouting Evidence Dataset:
  Usage:
    python3 scripts/analytics/generate_scouting_report.py --team team-ap.bren [--opponent team-onic] [--patch 1.8.44]

Outputs:
  - Formatted terminal scouting report
  - Structured JSON file: analytics/output/scouting/reports/scouting_report_<team_slug>.json

Enforces Non-Causal Terminology & explicit disclaimer:
  "These are observed historical patterns, not guaranteed future behavior."
"""

import argparse
import json
import os
import sys
from typing import Dict, List, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCOUTING_DIR = os.path.join(BASE_DIR, 'analytics/output/scouting')
REPORTS_DIR = os.path.join(SCOUTING_DIR, 'reports')

DISCLAIMER = "These are observed historical patterns, not guaranteed future behavior."

def load_scouting_data():
    evidence_path = os.path.join(SCOUTING_DIR, 'scouting_evidence.json')
    summary_path = os.path.join(SCOUTING_DIR, 'team_scouting_summary.json')
    tendencies_path = os.path.join(BASE_DIR, 'analytics/output/patterns/team_tendencies.json')

    if not os.path.exists(evidence_path) or not os.path.exists(summary_path):
        print("✗ Scouting evidence data not found. Run scripts/analytics/scouting_evidence.py first!")
        sys.exit(1)

    with open(evidence_path, 'r', encoding='utf-8') as f:
        evidence = json.load(f).get('data', [])

    with open(summary_path, 'r', encoding='utf-8') as f:
        summaries = json.load(f).get('data', [])

    tendencies = []
    if os.path.exists(tendencies_path):
        with open(tendencies_path, 'r', encoding='utf-8') as f:
            tendencies = json.load(f).get('data', [])

    return evidence, summaries, tendencies

def generate_report(team_id: str, opponent_id: Optional[str] = None, patch_ver: Optional[str] = None):
    os.makedirs(REPORTS_DIR, exist_ok=True)
    evidence, summaries, tendencies = load_scouting_data()

    # Filter team summary
    team_summary = next((s for s in summaries if s['team_id'] == team_id), None)
    team_tendency = next((t for t in tendencies if t['team_id'] == team_id), None)

    # Filter evidence patterns
    team_patterns = [e for e in evidence if e['context']['team_id'] == team_id]

    if opponent_id:
        # Filter for specific opponent
        team_patterns = [
            e for e in team_patterns
            if any(o['opponent_team_id'] == opponent_id for o in e.get('opponent_breakdown', []))
        ]

    if patch_ver:
        # Filter for specific patch
        team_patterns = [
            e for e in team_patterns
            if any(p['patch_version'] == patch_ver for p in e.get('patch_breakdown', []))
        ]

    # Report Data Structure
    report_obj = {
        "report_type": "TEAM_SCOUTING_REPORT",
        "target_team": team_id,
        "filter_opponent": opponent_id,
        "filter_patch": patch_ver,
        "dataset_scope": "single_tournament",
        "disclaimer": DISCLAIMER,
        "team_flexibility": {
            "distinct_response_categories": team_summary.get("distinct_response_categories", 0) if team_summary else 0,
            "raw_entropy": team_summary.get("raw_entropy", 0.0) if team_summary else 0.0,
            "normalized_entropy": team_summary.get("normalized_entropy", 0.0) if team_summary else 0.0,
            "diversity_label": team_summary.get("diversity_label", "UNKNOWN") if team_summary else "UNKNOWN"
        },
        "first_pick_preferences": team_tendency.get("first_pick_preferences", [])[:5] if team_tendency else [],
        "first_ban_preferences": team_tendency.get("first_ban_preferences", [])[:5] if team_tendency else [],
        "observed_response_patterns": team_patterns[:15]
    }

    # Print Terminal Report
    print("==========================================================")
    print("   MLBB TEAM SCOUTING REPORT V1")
    print("==========================================================")
    print(f"Target Team      : {team_id}")
    if opponent_id:
        print(f"Versus Opponent  : {opponent_id}")
    if patch_ver:
        print(f"Patch Filter     : {patch_ver}")
    print(f"Dataset Scope    : Single Tournament (M5 Knockout Stage)")
    print(f"Disclaimer       : {DISCLAIMER}")
    print("----------------------------------------------------------")

    if team_tendency:
        print("\n[1] FIRST PICK PREFERENCES")
        print(f"  {'Hero':<16} | {'Picks':<6} | {'Pick Rate':<10} | {'Observed Win Rate':<18}")
        print("  " + "-"*56)
        for fp in team_tendency.get("first_pick_preferences", [])[:5]:
            print(f"  {fp['hero_name']:<16} | n={fp['pick_count']:<4} | {fp['pick_rate']*100:<9.1f}% | {fp['observed_win_rate']*100:<17.1f}%")

        print("\n[2] FIRST BAN PREFERENCES")
        print(f"  {'Hero':<16} | {'Bans':<6} | {'Ban Rate':<10}")
        print("  " + "-"*38)
        for fb in team_tendency.get("first_ban_preferences", [])[:5]:
            print(f"  {fb['hero_name']:<16} | n={fb['ban_count']:<4} | {fb['ban_rate']*100:<9.1f}%")

    print("\n[3] TOP OBSERVED RESPONSE TENDENCIES")
    print(f"  {'Trigger -> Response':<32} | {'Games':<6} | {'Team Rate':<10} | {'Lift':<6} | {'Label':<18}")
    print("  " + "-"*80)
    for rec in team_patterns[:8]:
        ev = rec["evidence"]
        pat = rec["pattern"]
        cl = rec["classification"]
        t_str = f"{pat['trigger']['hero_name']} -> {pat['response']['hero_name']}"
        l_str = f"{ev['team_lift']:.2f}x" if ev['team_lift'] is not None else "N/A"
        print(f"  {t_str:<32} | n={ev['sample_size_games']:<4} | {ev['team_rate']*100:<9.1f}% | {l_str:<6} | {cl['sample_label']:<18}")

    if team_summary:
        print("\n[4] DRAFT FLEXIBILITY & NORMALIZED ENTROPY")
        print(f"  Distinct Categories (K) : K={team_summary['distinct_response_categories']}")
        print(f"  Raw Entropy H(X)        : {team_summary['raw_entropy']:.4f}")
        print(f"  Normalized Entropy H_norm: {team_summary['normalized_entropy']:.4f}")
        print(f"  Diversity Label         : {team_summary['diversity_label']}")

    print("\n==========================================================")

    # Save Structured Report JSON
    team_slug = team_id.replace('team-', '').replace('.', '_')
    report_file = os.path.join(REPORTS_DIR, f"scouting_report_{team_slug}.json")
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report_obj, f, indent=2, ensure_ascii=False)

    print(f"✓ Saved structured report to {report_file}")

def main():
    parser = argparse.ArgumentParser(description="Generate MLBB Team Scouting Report")
    parser.add_argument("--team", required=True, help="Target Team ID (e.g. team-ap.bren, team-onic)")
    parser.add_argument("--opponent", required=False, help="Filter for specific Opponent Team ID")
    parser.add_argument("--patch", required=False, help="Filter for specific Patch Version")

    args = parser.parse_args()
    generate_report(args.team, args.opponent, args.patch)

if __name__ == '__main__':
    main()
