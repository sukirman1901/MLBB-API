#!/usr/bin/env python3
"""
MLBB Draft Pattern & Opponent Scouting Engine V1 (Descriptive & Statistically Honest)
Author: sukirman1901
Repository: https://github.com/sukirman1901/MLBB-API

Transforms draft state transitions into explicit strategic patterns & team tendencies:
  1. Pick Response Patterns (Opponent Pick -> Team Pick)
  2. Ban Response Patterns (Opponent Pick -> Team Ban)
  3. Multi-Step Sequences (1-step, 2-step, 3-step contiguous sequences per match)
  4. Team Draft Tendencies (First Pick, First Ban, Alternative Responses)
  5. Patch-Specific Tendencies (Filtered by patch_version)
  6. Opponent-Specific Tendencies (Team A vs Team B)
  7. Draft Flexibility & Response Diversity (Shannon Entropy H(X))

Enforces strict statistical rules:
  - Preserves group_id = match_id to prevent future ML state leakage
  - Tracks sample_size_games (distinct games) separately from state_count
  - Non-causal terminology: "observed response", "observed win rate", "sample size"
"""

import json
import math
import os
import sys
from collections import defaultdict
from typing import Dict, List, Tuple, Optional, Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PATTERNS_OUTPUT_DIR = os.path.join(BASE_DIR, 'analytics/output/patterns')

DEFAULT_MIN_SAMPLE = 5

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

def calculate_shannon_entropy(probabilities: List[float]) -> float:
    """Calculates Shannon entropy H(X) = - sum(p * log2(p))"""
    entropy = 0.0
    for p in probabilities:
        if p > 0:
            entropy -= p * math.log2(p)
    return round(entropy, 4)

def classify_sample_size(n: int) -> Tuple[bool, str]:
    """Returns sample_sufficient boolean and descriptive sample label"""
    if n < 5:
        return False, "LOW_SAMPLE"
    elif n < 10:
        return True, "LIMITED_SAMPLE"
    else:
        return True, "OBSERVED_PATTERN"

def classify_diversity(entropy: float) -> str:
    """Classifies response diversity using neutral labels"""
    if entropy < 1.0:
        return "LOW_RESPONSE_DIVERSITY"
    elif entropy < 2.0:
        return "MEDIUM_RESPONSE_DIVERSITY"
    else:
        return "HIGH_RESPONSE_DIVERSITY"

def run_pattern_engine(verbose: bool = True):
    os.makedirs(PATTERNS_OUTPUT_DIR, exist_ok=True)
    states, hero_names = load_data()
    total_states = len(states)
    all_matches = set(s['match_id'] for s in states)
    total_games = len(all_matches)

    print("==========================================================")
    print("   MLBB DRAFT PATTERN & OPPONENT SCOUTING ENGINE V1")
    print("==========================================================")
    print(f"Total Games Analyzed  : {total_games}")
    print(f"Total Draft States    : {total_states}")
    print("----------------------------------------------------------")

    # Group states by match to prevent cross-match sequence contamination
    matches_dict = defaultdict(list)
    for s in states:
        matches_dict[s['match_id']].append(s)

    for m_id in matches_dict:
        matches_dict[m_id].sort(key=lambda x: x['action_number'])

    # -------------------------------------------------------------------------
    # 1. Pick Response & Ban Response Patterns
    # -------------------------------------------------------------------------
    pick_response_agg = defaultdict(lambda: {"count": 0, "wins": 0, "games": set()})
    ban_response_agg = defaultdict(lambda: {"count": 0, "games": set()})

    for m_id, m_states in matches_dict.items():
        for i in range(len(m_states) - 1):
            curr = m_states[i]
            nxt = m_states[i+1]

            curr_act = curr['action']
            nxt_act = nxt['action']

            # Opponent Pick -> Our Pick
            if curr_act['type'] == 'pick' and nxt_act['type'] == 'pick' and curr_act['team_id'] != nxt_act['team_id']:
                key = (curr_act['hero_id'], nxt_act['hero_id'], nxt['acting_team'])
                pick_response_agg[key]["count"] += 1
                pick_response_agg[key]["games"].add(m_id)
                if nxt['observed_outcome']['acting_team_won']:
                    pick_response_agg[key]["wins"] += 1

            # Opponent Pick -> Our Ban
            if curr_act['type'] == 'pick' and nxt_act['type'] == 'ban' and curr_act['team_id'] != nxt_act['team_id']:
                key = (curr_act['hero_id'], nxt_act['hero_id'], nxt['acting_team'])
                ban_response_agg[key]["count"] += 1
                ban_response_agg[key]["games"].add(m_id)

    # Format Pick Response Patterns JSON
    pick_response_list = []
    for (opp_h, resp_h, team_id), data in pick_response_agg.items():
        n = data["count"]
        w = data["wins"]
        n_g = len(data["games"])
        wr = round(w / n, 4) if n > 0 else 0.0
        suf, label = classify_sample_size(n)

        pick_response_list.append({
            "group_id_matches": sorted(list(data["games"])),
            "team_id": team_id,
            "opponent_pick_hero_id": opp_h,
            "opponent_pick_hero_name": hero_names.get(opp_h, opp_h),
            "response_pick_hero_id": resp_h,
            "response_pick_hero_name": hero_names.get(resp_h, resp_h),
            "state_count": n,
            "sample_size_games": n_g,
            "wins": w,
            "losses": n - w,
            "observed_win_rate": wr,
            "sample_sufficient": suf,
            "pattern_confidence_label": label
        })
    pick_response_list.sort(key=lambda x: x["state_count"], reverse=True)

    # Format Ban Response Patterns JSON
    ban_response_list = []
    for (opp_h, ban_h, team_id), data in ban_response_agg.items():
        n = data["count"]
        n_g = len(data["games"])
        suf, label = classify_sample_size(n)

        ban_response_list.append({
            "group_id_matches": sorted(list(data["games"])),
            "team_id": team_id,
            "opponent_pick_hero_id": opp_h,
            "response_ban_hero_id": ban_h,
            "response_ban_hero_name": hero_names.get(ban_h, ban_h),
            "state_count": n,
            "sample_size_games": n_g,
            "sample_sufficient": suf,
            "pattern_confidence_label": label
        })
    ban_response_list.sort(key=lambda x: x["state_count"], reverse=True)

    # -------------------------------------------------------------------------
    # 2. Multi-Step Sequences (1-step, 2-step, 3-step)
    # -------------------------------------------------------------------------
    seq_1_step = defaultdict(lambda: {"count": 0, "games": set()})
    seq_2_step = defaultdict(lambda: {"count": 0, "games": set()})
    seq_3_step = defaultdict(lambda: {"count": 0, "games": set()})

    for m_id, m_states in matches_dict.items():
        for i in range(len(m_states)):
            # 1-step
            s1 = m_states[i]
            a1 = s1['action']
            key1 = (a1['type'], a1['hero_id'])
            seq_1_step[key1]["count"] += 1
            seq_1_step[key1]["games"].add(m_id)

            # 2-step
            if i + 1 < len(m_states):
                s2 = m_states[i+1]
                a2 = s2['action']
                key2 = (a1['type'], a1['hero_id'], a2['type'], a2['hero_id'])
                seq_2_step[key2]["count"] += 1
                seq_2_step[key2]["games"].add(m_id)

            # 3-step
            if i + 2 < len(m_states):
                s3 = m_states[i+2]
                a3 = s3['action']
                key3 = (a1['type'], a1['hero_id'], a2['type'], a2['hero_id'], a3['type'], a3['hero_id'])
                seq_3_step[key3]["count"] += 1
                seq_3_step[key3]["games"].add(m_id)

    multi_step_data = {
        "one_step_sequences": [
            {
                "sequence": [f"{t1}:{h1}"],
                "sequence_names": [f"{t1.upper()} {hero_names.get(h1, h1)}"],
                "observed_frequency": d["count"],
                "sample_size_games": len(d["games"])
            }
            for (t1, h1), d in sorted(seq_1_step.items(), key=lambda x: x[1]["count"], reverse=True)[:15]
        ],
        "two_step_sequences": [
            {
                "sequence": [f"{t1}:{h1}", f"{t2}:{h2}"],
                "sequence_names": [f"{t1.upper()} {hero_names.get(h1, h1)}", f"{t2.upper()} {hero_names.get(h2, h2)}"],
                "observed_frequency": d["count"],
                "sample_size_games": len(d["games"])
            }
            for (t1, h1, t2, h2), d in sorted(seq_2_step.items(), key=lambda x: x[1]["count"], reverse=True)[:15]
        ],
        "three_step_sequences": [
            {
                "sequence": [f"{t1}:{h1}", f"{t2}:{h2}", f"{t3}:{h3}"],
                "sequence_names": [f"{t1.upper()} {hero_names.get(h1, h1)}", f"{t2.upper()} {hero_names.get(h2, h2)}", f"{t3.upper()} {hero_names.get(h3, h3)}"],
                "observed_frequency": d["count"],
                "sample_size_games": len(d["games"])
            }
            for (t1, h1, t2, h2, t3, h3), d in sorted(seq_3_step.items(), key=lambda x: x[1]["count"], reverse=True)[:15]
        ]
    }

    # -------------------------------------------------------------------------
    # 3. Team Tendencies & Alternative Response Distributions
    # -------------------------------------------------------------------------
    team_fp_picks = defaultdict(lambda: defaultdict(lambda: {"count": 0, "wins": 0, "games": set()}))
    team_fb_bans = defaultdict(lambda: defaultdict(lambda: {"count": 0, "games": set()}))
    team_responses = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: {"count": 0, "wins": 0, "games": set()})))

    # Track team total FP and FB games
    team_fp_games = defaultdict(set)
    team_fb_games = defaultdict(set)

    for s in states:
        t_id = s['acting_team']
        m_id = s['match_id']

        # First pick preference
        if s['is_first_pick']:
            team_fp_games[t_id].add(m_id)
            hid = s['action']['hero_id']
            team_fp_picks[t_id][hid]["count"] += 1
            team_fp_picks[t_id][hid]["games"].add(m_id)
            if s['observed_outcome']['acting_team_won']:
                team_fp_picks[t_id][hid]["wins"] += 1

        # First ban preference
        if s['is_first_ban']:
            team_fb_games[t_id].add(m_id)
            hid = s['action']['hero_id']
            team_fb_bans[t_id][hid]["count"] += 1
            team_fb_bans[t_id][hid]["games"].add(m_id)

    # Calculate team responses across matches
    for m_id, m_states in matches_dict.items():
        for i in range(len(m_states) - 1):
            curr = m_states[i]
            nxt = m_states[i+1]
            if curr['action']['type'] == 'pick' and nxt['action']['type'] == 'pick' and curr['action']['team_id'] != nxt['action']['team_id']:
                t_id = nxt['acting_team']
                opp_h = curr['action']['hero_id']
                resp_h = nxt['action']['hero_id']

                team_responses[t_id][opp_h][resp_h]["count"] += 1
                team_responses[t_id][opp_h][resp_h]["games"].add(m_id)
                if nxt['observed_outcome']['acting_team_won']:
                    team_responses[t_id][opp_h][resp_h]["wins"] += 1

    team_tendencies_data = []
    team_flexibility_data = []

    for t_id, fp_dict in team_fp_picks.items():
        tot_fp_games = len(team_fp_games[t_id])
        tot_fb_games = len(team_fb_games[t_id])

        # FP preferences
        fp_list = []
        for hid, d in fp_dict.items():
            cnt = d["count"]
            wins = d["wins"]
            p_rate = round(cnt / tot_fp_games, 4) if tot_fp_games > 0 else 0.0
            w_rate = round(wins / cnt, 4) if cnt > 0 else 0.0
            fp_list.append({
                "hero_id": hid,
                "hero_name": hero_names.get(hid, hid),
                "pick_count": cnt,
                "sample_size_games": len(d["games"]),
                "pick_rate": p_rate,
                "observed_win_rate": w_rate
            })
        fp_list.sort(key=lambda x: x["pick_count"], reverse=True)

        # FB preferences
        fb_list = []
        for hid, d in team_fb_bans[t_id].items():
            cnt = d["count"]
            b_rate = round(cnt / tot_fb_games, 4) if tot_fb_games > 0 else 0.0
            fb_list.append({
                "hero_id": hid,
                "hero_name": hero_names.get(hid, hid),
                "ban_count": cnt,
                "sample_size_games": len(d["games"]),
                "ban_rate": b_rate
            })
        fb_list.sort(key=lambda x: x["ban_count"], reverse=True)

        # Alternative Response Distributions & Shannon Entropy
        responses_out = {}
        all_team_response_probs = []
        total_team_responses = 0

        for opp_h, resp_dict in team_responses[t_id].items():
            tot_resp_for_opp = sum(d["count"] for d in resp_dict.values())
            total_team_responses += tot_resp_for_opp
            
            resp_list = []
            probs = []
            for resp_h, d in resp_dict.items():
                cnt = d["count"]
                wins = d["wins"]
                rate = round(cnt / tot_resp_for_opp, 4) if tot_resp_for_opp > 0 else 0.0
                w_rate = round(wins / cnt, 4) if cnt > 0 else 0.0
                suf, label = classify_sample_size(cnt)
                probs.append(rate)
                all_team_response_probs.append(cnt)

                resp_list.append({
                    "hero_id": resp_h,
                    "hero_name": hero_names.get(resp_h, resp_h),
                    "count": cnt,
                    "sample_size_games": len(d["games"]),
                    "response_rate": rate,
                    "wins": wins,
                    "losses": cnt - wins,
                    "observed_win_rate": w_rate,
                    "sample_sufficient": suf,
                    "pattern_confidence_label": label
                })
            resp_list.sort(key=lambda x: x["count"], reverse=True)

            # Context Entropy
            ctx_entropy = calculate_shannon_entropy(probs)
            ctx_div_label = classify_diversity(ctx_entropy)

            responses_out[opp_h] = {
                "opponent_hero_name": hero_names.get(opp_h, opp_h),
                "distinct_responses": len(resp_list),
                "response_entropy": ctx_entropy,
                "response_diversity_label": ctx_div_label,
                "observed_responses": resp_list
            }

        team_tendencies_data.append({
            "team_id": t_id,
            "total_first_pick_games": tot_fp_games,
            "total_first_ban_games": tot_fb_games,
            "first_pick_preferences": fp_list,
            "first_ban_preferences": fb_list,
            "alternative_responses": responses_out
        })

        # Calculate Overall Team Response Entropy
        if total_team_responses > 0:
            overall_probs = [cnt / total_team_responses for cnt in all_team_response_probs]
            team_entropy = calculate_shannon_entropy(overall_probs)
            team_flexibility_data.append({
                "team_id": t_id,
                "total_response_events": total_team_responses,
                "overall_response_entropy": team_entropy,
                "response_diversity_label": classify_diversity(team_entropy)
            })

    team_flexibility_data.sort(key=lambda x: x["overall_response_entropy"], reverse=True)

    # -------------------------------------------------------------------------
    # 4. Patch-Specific & Opponent-Specific Tendencies
    # -------------------------------------------------------------------------
    patch_agg = defaultdict(lambda: {"count": 0, "games": set()})
    opp_agg = defaultdict(lambda: {"count": 0, "games": set()})

    for m_id, m_states in matches_dict.items():
        for i in range(len(m_states) - 1):
            curr = m_states[i]
            nxt = m_states[i+1]
            if curr['action']['type'] == 'pick' and nxt['action']['type'] == 'pick' and curr['action']['team_id'] != nxt['action']['team_id']:
                patch_ver = nxt.get('patch_context', {}).get('version', 'unknown')
                t_id = nxt['acting_team']
                opp_team_id = curr['acting_team']
                opp_h = curr['action']['hero_id']
                resp_h = nxt['action']['hero_id']

                patch_key = (patch_ver, t_id, opp_h, resp_h)
                patch_agg[patch_key]["count"] += 1
                patch_agg[patch_key]["games"].add(m_id)

                opp_key = (t_id, opp_team_id, opp_h, resp_h)
                opp_agg[opp_key]["count"] += 1
                opp_agg[opp_key]["games"].add(m_id)

    patch_tendencies_list = [
        {
            "patch_version": p_ver,
            "team_id": t_id,
            "opponent_pick_hero_id": opp_h,
            "opponent_pick_hero_name": hero_names.get(opp_h, opp_h),
            "response_pick_hero_id": resp_h,
            "response_pick_hero_name": hero_names.get(resp_h, resp_h),
            "observed_count": d["count"],
            "sample_size_games": len(d["games"])
        }
        for (p_ver, t_id, opp_h, resp_h), d in sorted(patch_agg.items(), key=lambda x: x[1]["count"], reverse=True)
    ]

    opponent_tendencies_list = [
        {
            "team_id": t_id,
            "opponent_team_id": opp_team_id,
            "opponent_pick_hero_id": opp_h,
            "opponent_pick_hero_name": hero_names.get(opp_h, opp_h),
            "response_pick_hero_id": resp_h,
            "response_pick_hero_name": hero_names.get(resp_h, resp_h),
            "observed_count": d["count"],
            "sample_size_games": len(d["games"])
        }
        for (t_id, opp_team_id, opp_h, resp_h), d in sorted(opp_agg.items(), key=lambda x: x[1]["count"], reverse=True)
    ]

    # -------------------------------------------------------------------------
    # 5. Save Exported Datasets
    # -------------------------------------------------------------------------
    with open(os.path.join(PATTERNS_OUTPUT_DIR, 'pick_response_patterns.json'), 'w', encoding='utf-8') as f:
        json.dump({"data": pick_response_list}, f, indent=2, ensure_ascii=False)

    with open(os.path.join(PATTERNS_OUTPUT_DIR, 'ban_response_patterns.json'), 'w', encoding='utf-8') as f:
        json.dump({"data": ban_response_list}, f, indent=2, ensure_ascii=False)

    with open(os.path.join(PATTERNS_OUTPUT_DIR, 'multi_step_sequences.json'), 'w', encoding='utf-8') as f:
        json.dump(multi_step_data, f, indent=2, ensure_ascii=False)

    with open(os.path.join(PATTERNS_OUTPUT_DIR, 'team_tendencies.json'), 'w', encoding='utf-8') as f:
        json.dump({"data": team_tendencies_data}, f, indent=2, ensure_ascii=False)

    with open(os.path.join(PATTERNS_OUTPUT_DIR, 'patch_tendencies.json'), 'w', encoding='utf-8') as f:
        json.dump({"data": patch_tendencies_list}, f, indent=2, ensure_ascii=False)

    with open(os.path.join(PATTERNS_OUTPUT_DIR, 'opponent_tendencies.json'), 'w', encoding='utf-8') as f:
        json.dump({"data": opponent_tendencies_list}, f, indent=2, ensure_ascii=False)

    with open(os.path.join(PATTERNS_OUTPUT_DIR, 'draft_flexibility.json'), 'w', encoding='utf-8') as f:
        json.dump({"data": team_flexibility_data}, f, indent=2, ensure_ascii=False)

    if verbose:
        print("==========================================================")
        print("   MLBB DRAFT PATTERN & OPPONENT SCOUTING ENGINE V1")
        print("==========================================================")
        print(f"Total Games Analyzed  : {total_games}")
        print(f"Total Draft States    : {total_states}")
        print("----------------------------------------------------------")
        print(f"✓ Created 7 Pattern JSON Datasets in {PATTERNS_OUTPUT_DIR}\n")

        print("[1] TOP PICK RESPONSE PATTERNS")
        print(f"  {'Team':<20} | {'Opponent Pick':<15} -> {'Response Pick':<15} | {'Count':<5} | {'WR':<6} | {'Label':<15}")
        print("  " + "-"*85)
        for pr in pick_response_list[:8]:
            clean_team = pr['team_id'].split('\n')[0].split('{')[0].strip()
            print(f"  {clean_team:<20} | {pr['opponent_pick_hero_name']:<15} -> {pr['response_pick_hero_name']:<15} | n={pr['state_count']:<3} | {pr['observed_win_rate']*100:<4.1f}% | {pr['pattern_confidence_label']:<15}")

        print("\n[2] TOP MULTI-STEP DRAFT SEQUENCES (3-Step)")
        print(f"  {'Sequence':<55} | {'Frequency':<10}")
        print("  " + "-"*70)
        for seq3 in multi_step_data["three_step_sequences"][:5]:
            seq_str = " -> ".join(seq3["sequence_names"])
            print(f"  {seq_str:<55} | {seq3['observed_frequency']:<10}")

        print("\n[3] TEAM DRAFT FLEXIBILITY & SHANNON ENTROPY")
        print(f"  {'Team':<16} | {'Response Events':<16} | {'Entropy H(X)':<14} | {'Diversity Label':<25}")
        print("  " + "-"*75)
        for tf in team_flexibility_data[:8]:
            print(f"  {tf['team_id']:<16} | {tf['total_response_events']:<16} | {tf['overall_response_entropy']:<14.4f} | {tf['response_diversity_label']:<25}")

        print("==========================================================")

if __name__ == '__main__':
    run_pattern_engine()
