#!/usr/bin/env python3
"""
MLBB Esports Data Normalizer
Author: sukirman1901
Repository: https://github.com/sukirman1901/MLBB-API

Transforms raw Liquipedia parsed match blocks into canonical MLBB-API JSON entities:
  - Tournaments
  - Teams
  - Series
  - Matches with Chronological Draft Actions
  - Quality Level Classification (LEVEL_A, LEVEL_B, LEVEL_C, LEVEL_D)
  - SHA-256 Provenance Content Hashes
"""

import json
import os
import hashlib
from typing import Dict, List, Tuple
from map_entities import map_hero_alias, save_unresolved_entities

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def normalize_tournament(tourney_name="M5 World Championship"):
    return {
        "tournament_id": "m5-world-championship",
        "name": tourney_name,
        "organizer": "Moonton",
        "region": "Global",
        "season": 5,
        "stage": "Knockout Stage",
        "start_date": "2023-12-09",
        "end_date": "2023-12-17",
        "tier": "S",
        "status": "completed",
        "source": {
            "name": "Liquipedia",
            "url": "https://liquipedia.net/mobilelegends/M5_World_Championship/Knockout_Stage",
            "source_type": "public_web"
        }
    }

def normalize_team(raw_team_name: str) -> Dict:
    clean_name = raw_team_name.strip()
    team_id = "team-" + clean_name.lower().replace(' ', '-').replace("'", '')
    return {
        "team_id": team_id,
        "name": clean_name,
        "short_name": clean_name.split()[0].upper(),
        "region": "Global",
        "country": None,
        "logo": None,
        "status": "active"
    }

def normalize_series_and_matches(parsed_series_list: List[Dict], content_hash: str) -> Tuple[List[Dict], List[Dict], List[Dict]]:
    normalized_series = []
    normalized_matches = []
    teams_dict = {}

    for series_idx, s in enumerate(parsed_series_list, start=1):
        t1_obj = normalize_team(s['team1'])
        t2_obj = normalize_team(s['team2'])

        teams_dict[t1_obj['team_id']] = t1_obj
        teams_dict[t2_obj['team_id']] = t2_obj

        series_id = f"series-m5-ko-{series_idx:02d}"
        match_ids = []

        winner_team_id = t1_obj['team_id'] if s['series_winner'] == s['team1'] else (t2_obj['team_id'] if s['series_winner'] == s['team2'] else None)

        for m_idx, m in enumerate(s['maps'], start=1):
            match_id = f"match-m5-ko-{series_idx:02d}-g{m_idx}"
            match_ids.append(match_id)

            blue_side = t1_obj['team_id'] if m['team1_side'] == 'blue' else t2_obj['team_id']
            red_side = t2_obj['team_id'] if m['team1_side'] == 'blue' else t1_obj['team_id']

            game_winner = t1_obj['team_id'] if m['winner_num'] == '1' else (t2_obj['team_id'] if m['winner_num'] == '2' else None)

            # Build Chronological Draft Sequence (Rule 10)
            draft_actions = []
            action_counter = 1

            # Phase 1 Bans (t1b1..t1b3, t2b1..t2b3)
            for hero_alias in m['team1_bans'][:3]:
                hid, hname, conf = map_hero_alias(hero_alias)
                if hid:
                    draft_actions.append({"action": action_counter, "phase": 1, "type": "ban", "team_id": t1_obj['team_id'], "hero_id": hid, "player_id": None})
                    action_counter += 1

            for hero_alias in m['team2_bans'][:3]:
                hid, hname, conf = map_hero_alias(hero_alias)
                if hid:
                    draft_actions.append({"action": action_counter, "phase": 1, "type": "ban", "team_id": t2_obj['team_id'], "hero_id": hid, "player_id": None})
                    action_counter += 1

            # Phase 1 Picks (t1h1..t1h3, t2h1..t2h3)
            for hero_alias in m['team1_picks'][:3]:
                hid, hname, conf = map_hero_alias(hero_alias)
                if hid:
                    draft_actions.append({"action": action_counter, "phase": 1, "type": "pick", "team_id": t1_obj['team_id'], "hero_id": hid, "player_id": None})
                    action_counter += 1

            for hero_alias in m['team2_picks'][:3]:
                hid, hname, conf = map_hero_alias(hero_alias)
                if hid:
                    draft_actions.append({"action": action_counter, "phase": 1, "type": "pick", "team_id": t2_obj['team_id'], "hero_id": hid, "player_id": None})
                    action_counter += 1

            # Phase 2 Bans (t1b4..t1b5, t2b4..t2b5)
            for hero_alias in m['team1_bans'][3:]:
                hid, hname, conf = map_hero_alias(hero_alias)
                if hid:
                    draft_actions.append({"action": action_counter, "phase": 2, "type": "ban", "team_id": t1_obj['team_id'], "hero_id": hid, "player_id": None})
                    action_counter += 1

            for hero_alias in m['team2_bans'][3:]:
                hid, hname, conf = map_hero_alias(hero_alias)
                if hid:
                    draft_actions.append({"action": action_counter, "phase": 2, "type": "ban", "team_id": t2_obj['team_id'], "hero_id": hid, "player_id": None})
                    action_counter += 1

            # Phase 2 Picks (t1h4..t1h5, t2h4..t2h5)
            for hero_alias in m['team1_picks'][3:]:
                hid, hname, conf = map_hero_alias(hero_alias)
                if hid:
                    draft_actions.append({"action": action_counter, "phase": 2, "type": "pick", "team_id": t1_obj['team_id'], "hero_id": hid, "player_id": None})
                    action_counter += 1

            for hero_alias in m['team2_picks'][3:]:
                hid, hname, conf = map_hero_alias(hero_alias)
                if hid:
                    draft_actions.append({"action": action_counter, "phase": 2, "type": "pick", "team_id": t2_obj['team_id'], "hero_id": hid, "player_id": None})
                    action_counter += 1

            # Quality Level & Completeness
            has_draft = len(draft_actions) >= 10
            has_winner = game_winner is not None
            has_duration = m['duration_seconds'] is not None
            has_vod = m['vod_url'] is not None

            if has_draft and has_winner and has_duration and has_vod:
                quality_level = "LEVEL_B"  # Match + draft + VOD + duration
            elif has_draft and has_winner:
                quality_level = "LEVEL_C"  # Match + draft only
            else:
                quality_level = "LEVEL_D"  # Match result only

            completeness = {
                "teams": True,
                "winner": has_winner,
                "draft": has_draft,
                "players": False,
                "heroes": True,
                "items": False,
                "emblems": False,
                "statistics": False,
                "vod": has_vod,
                "patch": True
            }

            total_actions = len(draft_actions)
            ban_actions = sum(1 for a in draft_actions if a['type'] == 'ban')
            pick_actions = sum(1 for a in draft_actions if a['type'] == 'pick')
            p1_actions = sum(1 for a in draft_actions if a.get('phase') == 1)
            p2_actions = sum(1 for a in draft_actions if a.get('phase') == 2)
            has_draft = (total_actions >= 20 and pick_actions == 10 and ban_actions == 10)

            match_record = {
                "match_id": match_id,
                "series_id": series_id,
                "tournament_id": "m5-world-championship",
                "stage": "Knockout Stage",
                "game_number": m['game_number'],
                "date": s['date'],
                "patch": "1.8.44",
                "patch_source": "inferred",
                "team_a": t1_obj['team_id'],
                "team_b": t2_obj['team_id'],
                "blue_side": blue_side,
                "red_side": red_side,
                "winner_team_id": game_winner,
                "duration_seconds": m['duration_seconds'],
                "duration_str": m['duration_str'],
                "vod_url": m['vod_url'],
                "vod_scope": "game" if m['vod_url'] else None,
                "quality_level": quality_level,
                "completeness": completeness,
                "draft_complete": has_draft,
                "draft_stats": {
                    "total_actions": total_actions,
                    "ban_actions": ban_actions,
                    "pick_actions": pick_actions,
                    "phase_1_actions": p1_actions,
                    "phase_2_actions": p2_actions
                },
                "source": {
                    "name": "Liquipedia",
                    "url": "https://liquipedia.net/mobilelegends/M5_World_Championship/Knockout_Stage",
                    "source_type": "public_web",
                    "content_hash": content_hash
                },
                "draft": draft_actions,
                "player_performances": []  # Uses null / empty list when unavailable (Rule 19)
            }
            normalized_matches.append(match_record)

        series_record = {
            "series_id": series_id,
            "tournament_id": "m5-world-championship",
            "stage": "Knockout Stage",
            "date": s['date'],
            "team_a": t1_obj['team_id'],
            "team_b": t2_obj['team_id'],
            "format": f"BO{s['best_of']}",
            "score": s['score'],
            "winner_team_id": winner_team_id,
            "match_ids": match_ids
        }
        normalized_series.append(series_record)

    save_unresolved_entities()
    return list(teams_dict.values()), normalized_series, normalized_matches
