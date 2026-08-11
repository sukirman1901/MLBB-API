#!/usr/bin/env python3
"""
MLBB Draft Scouting Evidence Engine V1 (Multi-Level Evidence Hierarchies)
Author: sukirman1901
Repository: https://github.com/sukirman1901/MLBB-API

Quantifies multi-level draft evidence without machine learning or causal claims:
  - Level A (Global): All teams
  - Level B (Team): Filtered by team_id
  - Level C (Team + Patch): Filtered by team_id & patch_version
  - Level D (Team + Opponent): Filtered by team_id & opponent_team_id
  - Level E (Team + Patch + Opponent): Filtered by team_id, patch_version, & opponent_team_id

Key Metrics & Statistical Integrity:
  - Pattern Lift & Context Lift ratios (null if denominator == 0)
  - Sample size metrics: state_count, sample_size_games (unique matches), sample_size_series, tournament_count
  - Sample size labels: LOW_SAMPLE (< 5 games), LIMITED_SAMPLE (5-9), OBSERVED_PATTERN (10-19), STRONG_OBSERVED_SAMPLE (>= 20)
  - Team specificity: LOW_SPECIFICITY, MEDIUM_SPECIFICITY, HIGH_SPECIFICITY
  - Persistence: SINGLE_TOURNAMENT, MULTI_SERIES, MULTI_TOURNAMENT
  - Normalized Shannon Entropy H_norm in [0, 1] (H / log2(K), 0 if K <= 1)
  - Non-causal terminology: "observed response", "observed win rate", "sample size"
"""

import json
import math
import os
import sys
from collections import defaultdict
from typing import Dict, List, Tuple, Optional, Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCOUTING_OUTPUT_DIR = os.path.join(BASE_DIR, 'analytics/output/scouting')

DEFAULT_MIN_GAMES = 5

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

def calculate_shannon_entropy(probabilities: List[float]) -> Tuple[float, float, int]:
    """Calculates raw Shannon entropy H(X) and Normalized Entropy H_norm in [0, 1]"""
    K = len(probabilities)
    if K <= 1:
        return 0.0, 0.0, K

    entropy = 0.0
    for p in probabilities:
        if p > 0:
            entropy -= p * math.log2(p)

    max_entropy = math.log2(K)
    norm_entropy = round(entropy / max_entropy, 4) if max_entropy > 0 else 0.0
    return round(entropy, 4), norm_entropy, K

def classify_sample_size_games(n_games: int) -> Tuple[bool, str]:
    """Classifies sample size based on unique match count"""
    if n_games < 5:
        return False, "LOW_SAMPLE"
    elif n_games < 10:
        return True, "LIMITED_SAMPLE"
    elif n_games < 20:
        return True, "OBSERVED_PATTERN"
    else:
        return True, "STRONG_OBSERVED_SAMPLE"

def classify_diversity(entropy: float) -> str:
    """Classifies response diversity using neutral labels"""
    if entropy < 1.0:
        return "LOW_RESPONSE_DIVERSITY"
    elif entropy < 2.0:
        return "MEDIUM_RESPONSE_DIVERSITY"
    else:
        return "HIGH_RESPONSE_DIVERSITY"

def classify_team_specificity(diff: float) -> str:
    """Classifies team specificity based on absolute difference between team_rate and global_rate"""
    if diff < 0.15:
        return "LOW_SPECIFICITY"
    elif diff < 0.35:
        return "MEDIUM_SPECIFICITY"
    else:
        return "HIGH_SPECIFICITY"

def classify_persistence(tournaments: int, series: int) -> str:
    """Classifies persistence based on tournament and series counts"""
    if tournaments > 1:
        return "MULTI_TOURNAMENT"
    elif series > 1:
        return "MULTI_SERIES"
    else:
        return "SINGLE_TOURNAMENT"

def compute_lift(numerator_rate: float, denominator_rate: float) -> Optional[float]:
    """Computes lift ratio (returns None if denominator is 0.0 or None)"""
    if denominator_rate is None or denominator_rate == 0.0:
        return None
    return round(numerator_rate / denominator_rate, 4)

def run_scouting_evidence_engine(verbose: bool = True):
    os.makedirs(SCOUTING_OUTPUT_DIR, exist_ok=True)
    states, hero_names = load_data()

    # Track distinct matches, series, and tournaments
    all_matches = set(s['match_id'] for s in states)
    all_series = set(s['series_id'] for s in states)
    all_tournaments = set(s['tournament_id'] for s in states)
    
    total_states = len(states)
    total_games = len(all_matches)

    # -------------------------------------------------------------------------
    # Build Multi-Level Aggregations for Pick Responses (Opponent Pick -> Team Pick)
    # -------------------------------------------------------------------------
    # Structure: key -> {"states": cnt, "games": set(), "series": set(), "tournaments": set(), "wins": cnt}
    
    level_a_global = defaultdict(lambda: {"states": 0, "games": set(), "series": set(), "tournaments": set(), "wins": 0})
    level_b_team = defaultdict(lambda: {"states": 0, "games": set(), "series": set(), "tournaments": set(), "wins": 0})
    level_c_patch = defaultdict(lambda: {"states": 0, "games": set(), "series": set(), "tournaments": set(), "wins": 0})
    level_d_opp = defaultdict(lambda: {"states": 0, "games": set(), "series": set(), "tournaments": set(), "wins": 0})
    level_e_full = defaultdict(lambda: {"states": 0, "games": set(), "series": set(), "tournaments": set(), "wins": 0})

    # Group states by match
    matches_dict = defaultdict(list)
    for s in states:
        matches_dict[s['match_id']].append(s)

    for m_id in matches_dict:
        matches_dict[m_id].sort(key=lambda x: x['action_number'])

    # Track total response opportunities for each context to compute rates
    opp_pick_global_totals = defaultdict(int)
    opp_pick_team_totals = defaultdict(int)
    opp_pick_patch_totals = defaultdict(int)
    opp_pick_opp_totals = defaultdict(int)

    for m_id, m_states in matches_dict.items():
        for i in range(len(m_states) - 1):
            curr = m_states[i]
            nxt = m_states[i+1]

            if curr['action']['type'] == 'pick' and nxt['action']['type'] == 'pick' and curr['action']['team_id'] != nxt['action']['team_id']:
                opp_h = curr['action']['hero_id']
                resp_h = nxt['action']['hero_id']
                t_id = nxt['acting_team'].split('\n')[0].split('{')[0].strip()
                opp_t_id = curr['acting_team'].split('\n')[0].split('{')[0].strip()
                patch_ver = nxt.get('patch_context', {}).get('version', 'unknown')

                s_id = nxt['series_id']
                tourn_id = nxt['tournament_id']
                won = nxt['observed_outcome']['acting_team_won']

                # Opportunities
                opp_pick_global_totals[opp_h] += 1
                opp_pick_team_totals[(t_id, opp_h)] += 1
                opp_pick_patch_totals[(t_id, patch_ver, opp_h)] += 1
                opp_pick_opp_totals[(t_id, opp_t_id, opp_h)] += 1

                # Level A: Global (opp_h, resp_h)
                k_a = (opp_h, resp_h)
                level_a_global[k_a]["states"] += 1
                level_a_global[k_a]["games"].add(m_id)
                level_a_global[k_a]["series"].add(s_id)
                level_a_global[k_a]["tournaments"].add(tourn_id)
                if won: level_a_global[k_a]["wins"] += 1

                # Level B: Team (t_id, opp_h, resp_h)
                k_b = (t_id, opp_h, resp_h)
                level_b_team[k_b]["states"] += 1
                level_b_team[k_b]["games"].add(m_id)
                level_b_team[k_b]["series"].add(s_id)
                level_b_team[k_b]["tournaments"].add(tourn_id)
                if won: level_b_team[k_b]["wins"] += 1

                # Level C: Team + Patch (t_id, patch_ver, opp_h, resp_h)
                k_c = (t_id, patch_ver, opp_h, resp_h)
                level_c_patch[k_c]["states"] += 1
                level_c_patch[k_c]["games"].add(m_id)
                level_c_patch[k_c]["series"].add(s_id)
                level_c_patch[k_c]["tournaments"].add(tourn_id)
                if won: level_c_patch[k_c]["wins"] += 1

                # Level D: Team + Opponent (t_id, opp_t_id, opp_h, resp_h)
                k_d = (t_id, opp_t_id, opp_h, resp_h)
                level_d_opp[k_d]["states"] += 1
                level_d_opp[k_d]["games"].add(m_id)
                level_d_opp[k_d]["series"].add(s_id)
                level_d_opp[k_d]["tournaments"].add(tourn_id)
                if won: level_d_opp[k_d]["wins"] += 1

                # Level E: Team + Patch + Opponent (t_id, patch_ver, opp_t_id, opp_h, resp_h)
                k_e = (t_id, patch_ver, opp_t_id, opp_h, resp_h)
                level_e_full[k_e]["states"] += 1
                level_e_full[k_e]["games"].add(m_id)
                level_e_full[k_e]["series"].add(s_id)
                level_e_full[k_e]["tournaments"].add(tourn_id)
                if won: level_e_full[k_e]["wins"] += 1

    # -------------------------------------------------------------------------
    # Process Evidence Hierarchy Records
    # -------------------------------------------------------------------------
    scouting_evidence_records = []

    for (t_id, opp_h, resp_h), data_b in level_b_team.items():
        st_cnt = data_b["states"]
        n_games = len(data_b["games"])
        n_series = len(data_b["series"])
        n_tourn = len(data_b["tournaments"])
        wins = data_b["wins"]
        losses = st_cnt - wins

        wr = round(wins / st_cnt, 4) if st_cnt > 0 else 0.0

        # Global Rate & Lift
        tot_glob_opp = opp_pick_global_totals.get(opp_h, 0)
        glob_data = level_a_global.get((opp_h, resp_h), {"states": 0})
        glob_st_cnt = glob_data["states"]
        glob_rate = round(glob_st_cnt / tot_glob_opp, 4) if tot_glob_opp > 0 else 0.0

        tot_team_opp = opp_pick_team_totals.get((t_id, opp_h), 0)
        team_rate = round(st_cnt / tot_team_opp, 4) if tot_team_opp > 0 else 0.0

        team_lift = compute_lift(team_rate, glob_rate)

        # Team Specificity Score
        diff = abs(team_rate - glob_rate)
        spec_label = classify_team_specificity(diff)

        # Sample & Persistence Labels
        suf, sample_label = classify_sample_size_games(n_games)
        persist_label = classify_persistence(n_tourn, n_series)

        # Context Lifts
        # Level C: Patch Specificity
        patch_records = []
        for (k_t, k_p, k_oh, k_rh), d_c in level_c_patch.items():
            if k_t == t_id and k_oh == opp_h and k_rh == resp_h:
                c_st = d_c["states"]
                c_games = len(d_c["games"])
                c_tot = opp_pick_patch_totals.get((t_id, k_p, opp_h), 0)
                c_rate = round(c_st / c_tot, 4) if c_tot > 0 else 0.0
                p_lift = compute_lift(c_rate, team_rate)

                patch_records.append({
                    "patch_version": k_p,
                    "state_count": c_st,
                    "sample_size_games": c_games,
                    "patch_rate": c_rate,
                    "patch_lift": p_lift,
                    "context_label": "PATCH_LOCALIZED_TENDENCY" if (p_lift and p_lift >= 1.5) else "NEUTRAL"
                })

        # Level D: Opponent Specificity
        opp_records = []
        for (k_t, k_opp_t, k_oh, k_rh), d_d in level_d_opp.items():
            if k_t == t_id and k_oh == opp_h and k_rh == resp_h:
                d_st = d_d["states"]
                d_games = len(d_d["games"])
                d_tot = opp_pick_opp_totals.get((t_id, k_opp_t, opp_h), 0)
                d_rate = round(d_st / d_tot, 4) if d_tot > 0 else 0.0
                o_lift = compute_lift(d_rate, team_rate)

                opp_records.append({
                    "opponent_team_id": k_opp_t,
                    "state_count": d_st,
                    "sample_size_games": d_games,
                    "opponent_rate": d_rate,
                    "opponent_lift": o_lift,
                    "context_label": "OPPONENT_LOCALIZED_TENDENCY" if (o_lift and o_lift >= 1.5) else "NEUTRAL"
                })

        rec = {
            "pattern": {
                "trigger": {
                    "type": "opponent_pick",
                    "hero_id": opp_h,
                    "hero_name": hero_names.get(opp_h, opp_h)
                },
                "response": {
                    "type": "pick",
                    "hero_id": resp_h,
                    "hero_name": hero_names.get(resp_h, resp_h)
                }
            },
            "context": {
                "team_id": t_id,
                "dataset_scope": "single_tournament" if len(all_tournaments) == 1 else "multi_tournament"
            },
            "evidence": {
                "state_count": st_cnt,
                "sample_size_games": n_games,
                "sample_size_series": n_series,
                "tournament_count": n_tourn,
                "global_rate": glob_rate,
                "team_rate": team_rate,
                "team_lift": team_lift,
                "observed_wins": wins,
                "observed_losses": losses,
                "observed_win_rate": wr
            },
            "classification": {
                "sample_sufficient": suf,
                "sample_label": sample_label,
                "specificity": spec_label,
                "persistence": persist_label,
                "team_concentration": "OBSERVED_TEAM_CONCENTRATION" if (team_lift and team_lift >= 1.5) else "NEUTRAL"
            },
            "patch_breakdown": patch_records,
            "opponent_breakdown": opp_records
        }

        scouting_evidence_records.append(rec)

    scouting_evidence_records.sort(key=lambda x: x["evidence"]["sample_size_games"], reverse=True)

    # -------------------------------------------------------------------------
    # Team Scouting Summaries & Normalized Shannon Entropy
    # -------------------------------------------------------------------------
    team_summaries = []
    grouped_by_team = defaultdict(list)
    for rec in scouting_evidence_records:
        grouped_by_team[rec["context"]["team_id"]].append(rec)

    for t_id, recs in grouped_by_team.items():
        # Calculate distinct response count & normalized entropy
        resp_counts = defaultdict(int)
        tot_resps = 0
        for r in recs:
            cnt = r["evidence"]["state_count"]
            resp_counts[r["pattern"]["response"]["hero_id"]] += cnt
            tot_resps += cnt

        probs = [cnt / tot_resps for cnt in resp_counts.values()] if tot_resps > 0 else []
        raw_entropy, norm_entropy, K = calculate_shannon_entropy(probs)

        div_label = classify_diversity(raw_entropy)

        team_summaries.append({
            "team_id": t_id,
            "total_patterns_observed": len(recs),
            "distinct_response_categories": K,
            "raw_entropy": raw_entropy,
            "normalized_entropy": norm_entropy,
            "diversity_label": div_label,
            "top_patterns": recs[:10]
        })

    team_summaries.sort(key=lambda x: x["total_patterns_observed"], reverse=True)

    # -------------------------------------------------------------------------
    # Save Exported JSON Datasets
    # -------------------------------------------------------------------------
    with open(os.path.join(SCOUTING_OUTPUT_DIR, 'scouting_evidence.json'), 'w', encoding='utf-8') as f:
        json.dump({"description": "MLBB Draft Scouting Evidence Dataset V1", "data": scouting_evidence_records}, f, indent=2, ensure_ascii=False)

    with open(os.path.join(SCOUTING_OUTPUT_DIR, 'team_scouting_summary.json'), 'w', encoding='utf-8') as f:
        json.dump({"description": "Team Scouting Evidence Summary V1", "data": team_summaries}, f, indent=2, ensure_ascii=False)

    if verbose:
        print(f"✓ Created Scouting Evidence JSONs in {SCOUTING_OUTPUT_DIR}\n")

        print("[1] TOP OBSERVED TEAM SCOUTING PATTERNS (By Games Sample Size)")
        print(f"  {'Team':<16} | {'Trigger -> Response':<32} | {'Games':<6} | {'Team Rate':<10} | {'Lift':<6} | {'Label':<18}")
        print("  " + "-"*92)
        for rec in scouting_evidence_records[:10]:
            ev = rec["evidence"]
            pat = rec["pattern"]
            cl = rec["classification"]
            t_str = f"{pat['trigger']['hero_name']} -> {pat['response']['hero_name']}"
            l_str = f"{ev['team_lift']:.2f}x" if ev['team_lift'] is not None else "N/A"
            print(f"  {rec['context']['team_id']:<16} | {t_str:<32} | n={ev['sample_size_games']:<4} | {ev['team_rate']*100:<9.1f}% | {l_str:<6} | {cl['sample_label']:<18}")

        print("\n[2] TEAM RESPONSE DIVERSITY & NORMALIZED SHANNON ENTROPY H_norm")
        print(f"  {'Team':<16} | {'Categories (K)':<15} | {'Raw H':<8} | {'H_norm':<8} | {'Diversity Label':<25}")
        print("  " + "-"*75)
        for ts in team_summaries[:8]:
            print(f"  {ts['team_id']:<16} | K={ts['distinct_response_categories']:<13} | {ts['raw_entropy']:<8.4f} | {ts['normalized_entropy']:<8.4f} | {ts['diversity_label']:<25}")

        print("==========================================================")

if __name__ == '__main__':
    run_scouting_evidence_engine()
