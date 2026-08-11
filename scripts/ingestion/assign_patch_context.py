#!/usr/bin/env python3
"""
MLBB Match Patch Context Assigner V1
Author: sukirman1901
Repository: https://github.com/sukirman1901/MLBB-API

Enforces strict 4-level assignment hierarchy:
  Level 1: explicit_match_source (HIGH confidence)
  Level 2: verified_tournament_window (HIGH/MEDIUM confidence)
  Level 3: date_inference (LOW confidence)
  Level 4: unresolved (UNKNOWN confidence, version = None)

Normalizes dates to ISO-8601 UTC strings and calculates:
  - days_since_release
  - days_since_effective
"""

import json
import os
import sys
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def parse_iso8601(date_str: str) -> Optional[datetime]:
    """Parse date string into UTC ISO-8601 datetime"""
    if not date_str:
        return None
    
    # Check if already ISO-8601 (e.g. 2023-12-09T14:00:00Z)
    if 'T' in date_str and date_str.endswith('Z'):
        try:
            return datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        except ValueError:
            pass

    # Standard Liquipedia date format: "December 9, 2023 - 14:00"
    clean = date_str.split('{{')[0].strip()  # remove templates if any
    try:
        if ' - ' in clean:
            dt = datetime.strptime(clean, "%B %d, %Y - %H:%M")
        else:
            dt = datetime.strptime(clean, "%Y-%m-%d")
        return dt.replace(tzinfo=timezone.utc)
    except Exception:
        pass
    return None

def format_iso8601(dt: datetime) -> str:
    """Format datetime into ISO-8601 UTC string"""
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

def check_overlapping_windows(windows: List[Dict]):
    """Prevent overlapping PatchWindows for the same tournament_id and stage"""
    grouped = defaultdict(list)
    for w in windows:
        key = (w.get('tournament_id'), w.get('stage'))
        grouped[key].append(w)

    for (t_id, stage), w_list in grouped.items():
        sorted_w = sorted(w_list, key=lambda x: parse_iso8601(x['effective_from']))
        for i in range(len(sorted_w) - 1):
            w1_end = parse_iso8601(sorted_w[i]['effective_until'])
            w2_start = parse_iso8601(sorted_w[i+1]['effective_from'])
            if w1_end >= w2_start:
                raise ValueError(f"Overlapping PatchWindows detected for [{t_id}] [{stage}]: {sorted_w[i]['patch_window_id']} and {sorted_w[i+1]['patch_window_id']}")
    print("✓ Verified zero overlapping PatchWindows.")

def load_data():
    matches_path = os.path.join(BASE_DIR, 'esports/matches/m5_knockout_matches.json')
    patches_path = os.path.join(BASE_DIR, 'patches/patches.json')
    windows_path = os.path.join(BASE_DIR, 'patches/windows.json')

    with open(matches_path, 'r', encoding='utf-8') as f:
        matches = json.load(f).get('data', [])

    with open(patches_path, 'r', encoding='utf-8') as f:
        patches = json.load(f).get('data', [])

    with open(windows_path, 'r', encoding='utf-8') as f:
        windows = json.load(f).get('data', [])

    return matches, patches, windows, matches_path

from collections import defaultdict

def assign_patch_context_to_match(m: Dict, patches: List[Dict], windows: List[Dict]) -> Dict:
    """Deterministic 4-level patch assignment hierarchy"""
    raw_date = m.get('date')
    game_dt = parse_iso8601(raw_date)
    iso_date_str = format_iso8601(game_dt) if game_dt else None
    
    t_id = m.get('tournament_id')
    stage = m.get('stage')
    
    # 1. Check Level 1 — Explicit Match Source
    if m.get('patch_source') == 'explicit' and m.get('patch'):
        ver = m['patch']
        # Find release date
        patch_info = next((p for p in patches if p['version'] == ver), None)
        rel_dt = parse_iso8601(patch_info['release_date']) if patch_info else None
        
        days_rel = (game_dt - rel_dt).days if (game_dt and rel_dt) else None
        return {
            "version": ver,
            "patch_window_id": None,
            "patch_release_date": format_iso8601(rel_dt) if rel_dt else None,
            "effective_from": None,
            "effective_until": None,
            "days_since_release": days_rel,
            "days_since_effective": None,
            "assignment_method": "explicit_match_source",
            "assignment_confidence": "HIGH",
            "source": m.get('source', {})
        }

    # 2. Check Level 2 — Verified Tournament PatchWindow
    matching_window = None
    if game_dt:
        for w in windows:
            if w.get('tournament_id') == t_id and w.get('stage') == stage:
                w_start = parse_iso8601(w['effective_from'])
                w_end = parse_iso8601(w['effective_until'])
                if w_start and w_end and w_start <= game_dt <= w_end:
                    matching_window = w
                    break

    if matching_window:
        ver = matching_window['patch_version']
        patch_info = next((p for p in patches if p['version'] == ver), None)
        rel_dt = parse_iso8601(patch_info['release_date']) if patch_info else None
        eff_start = parse_iso8601(matching_window['effective_from'])
        eff_end = parse_iso8601(matching_window['effective_until'])

        days_rel = (game_dt - rel_dt).days if (game_dt and rel_dt) else None
        days_eff = (game_dt - eff_start).days if (game_dt and eff_start) else None

        conf = "HIGH" if matching_window.get('status') == "VERIFIED" else "MEDIUM"

        return {
            "version": ver,
            "patch_window_id": matching_window['patch_window_id'],
            "patch_release_date": format_iso8601(rel_dt) if rel_dt else None,
            "effective_from": format_iso8601(eff_start) if eff_start else None,
            "effective_until": format_iso8601(eff_end) if eff_end else None,
            "days_since_release": days_rel,
            "days_since_effective": days_eff,
            "assignment_method": "verified_tournament_window",
            "assignment_confidence": conf,
            "source": matching_window.get('source', {})
        }

    # 3. Check Level 3 — Date-based inference
    if game_dt:
        # Find latest released patch prior to game date
        candidate_patch = None
        for p in sorted(patches, key=lambda x: parse_iso8601(x['release_date']), reverse=True):
            p_rel = parse_iso8601(p['release_date'])
            if p_rel and p_rel <= game_dt:
                candidate_patch = p
                break
        
        if candidate_patch:
            ver = candidate_patch['version']
            rel_dt = parse_iso8601(candidate_patch['release_date'])
            days_rel = (game_dt - rel_dt).days if (game_dt and rel_dt) else None
            return {
                "version": ver,
                "patch_window_id": None,
                "patch_release_date": format_iso8601(rel_dt) if rel_dt else None,
                "effective_from": None,
                "effective_until": None,
                "days_since_release": days_rel,
                "days_since_effective": None,
                "assignment_method": "date_inference",
                "assignment_confidence": "LOW",
                "source": {
                    "name": "Liquipedia",
                    "url": candidate_patch.get('source_url', ''),
                    "source_type": "public_web"
                }
            }

    # 4. Level 4 — Unresolved / No Evidence
    return {
        "version": None,
        "patch_window_id": None,
        "patch_release_date": None,
        "effective_from": None,
        "effective_until": None,
        "days_since_release": None,
        "days_since_effective": None,
        "assignment_method": "unresolved",
        "assignment_confidence": "UNKNOWN"
    }

def main():
    print("==========================================================")
    print("   MLBB MATCH PATCH CONTEXT ASSIGNER V1")
    print("==========================================================")

    matches, patches, windows, matches_path = load_data()
    check_overlapping_windows(windows)

    method_counts = defaultdict(int)
    confidence_counts = defaultdict(int)

    for m in matches:
        # Normalize date to ISO-8601
        raw_date = m.get('date')
        game_dt = parse_iso8601(raw_date)
        if game_dt:
            m['date_iso'] = format_iso8601(game_dt)

        p_ctx = assign_patch_context_to_match(m, patches, windows)
        m['patch_context'] = p_ctx
        m['patch'] = p_ctx['version']
        m['patch_source'] = p_ctx['assignment_method']

        method_counts[p_ctx['assignment_method']] += 1
        confidence_counts[p_ctx['assignment_confidence']] += 1

    # Save updated match records
    with open(matches_path, 'w', encoding='utf-8') as f:
        json.dump({"revdate": "2026-08-11", "author": "sukirman1901", "data_type": "official_public", "data": matches}, f, indent=2, ensure_ascii=False)

    print(f"✓ Updated {len(matches)} match records with patch_context in {matches_path}")
    print("\nPatch Assignment Methods Breakdown:")
    for method, cnt in method_counts.items():
        print(f"  • {method:<28}: {cnt}")

    print("\nPatch Assignment Confidence Breakdown:")
    for conf, cnt in confidence_counts.items():
        print(f"  • {conf:<10}: {cnt}")

    print("==========================================================")

if __name__ == '__main__':
    main()
