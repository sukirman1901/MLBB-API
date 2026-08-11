#!/usr/bin/env python3
"""
Liquipedia MLBB Source Parser & Scraper
Author: sukirman1901
Repository: https://github.com/sukirman1901/MLBB-API

Fetches wikitext match blocks from Liquipedia MLBB via MediaWiki API,
calculates SHA-256 content hashes, and parses match structures.
"""

import json
import gzip
import os
import re
import hashlib
import time
import urllib.request
from typing import Dict, List, Tuple, Optional

HEADERS = {
    'User-Agent': 'MLBB-API-DataIngestion/1.0 (contact: sukirman1901@users.noreply.github.com)',
    'Accept-Encoding': 'gzip'
}

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW_DIR = os.path.join(BASE_DIR, 'esports/raw/liquipedia')

def test_connectivity(page_title="M5_World_Championship/Knockout_Stage") -> Tuple[bool, Optional[str]]:
    """Rule 4: Live API Connectivity & Data Availability Verification"""
    url = f"https://liquipedia.net/mobilelegends/api.php?action=parse&page={page_title}&prop=wikitext&format=json"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = gzip.decompress(resp.read()).decode('utf-8') if resp.info().get('Content-Encoding') == 'gzip' else resp.read().decode('utf-8')
            data = json.loads(content)
            if 'parse' in data and 'wikitext' in data['parse']:
                wikitext = data['parse']['wikitext']['*']
                print(f"✓ Live API Connectivity Verified! [{page_title}] Length: {len(wikitext)} chars")
                return True, wikitext
    except Exception as e:
        print(f"✗ Live API Connectivity Test Failed: {e}")
        return False, None
    return False, None

def fetch_and_cache_raw(page_title="M5_World_Championship/Knockout_Stage") -> Tuple[Dict, str]:
    """Fetch raw wikitext and calculate SHA-256 snapshot hash (Rule 5)"""
    os.makedirs(RAW_DIR, exist_ok=True)
    cache_file = os.path.join(RAW_DIR, "m5_knockout_raw.json")

    # Check cache first
    if os.path.exists(cache_file):
        with open(cache_file, 'r', encoding='utf-8') as f:
            cached_data = json.load(f)
            print(f"✓ Loaded cached raw wikitext snapshot from {cache_file}")
            return cached_data, cached_data['source']['content_hash']

    # Fetch live
    ok, wikitext = test_connectivity(page_title)
    if not ok or not wikitext:
        raise RuntimeError("Failed to connect to Liquipedia API. Stopping ingestion.")

    content_hash = "sha256:" + hashlib.sha256(wikitext.encode('utf-8')).hexdigest()
    retrieved_at = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

    snapshot = {
        "source": {
            "name": "Liquipedia",
            "url": f"https://liquipedia.net/mobilelegends/{page_title}",
            "retrieved_at": retrieved_at,
            "source_type": "public_web",
            "content_hash": content_hash
        },
        "page_title": page_title,
        "wikitext": wikitext
    }

    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False)

    print(f"✓ Saved raw wikitext snapshot with SHA-256 hash [{content_hash[:16]}...]")
    return snapshot, content_hash

def parse_duration_to_seconds(len_str: str) -> Optional[int]:
    """Convert length '20:58' to 1258 seconds"""
    if not len_str or ':' not in len_str:
        return None
    try:
        parts = len_str.split(':')
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    except Exception:
        pass
    return None

def parse_match_blocks(wikitext: str) -> List[Dict]:
    """Parse {{Match...}} blocks and map1..map5 maps from Liquipedia wikitext"""
    # Regex to split match blocks
    matches_raw = re.findall(r'\|(R\d+M\d+)=\{\{Match(.*?)(?=\|R\d+M\d+=\{\{Match|\}\}\n\n|\}\}\n\||\Z)', wikitext, re.DOTALL)
    parsed_series = []

    for match_tag, block in matches_raw:
        # Extract metadata
        bestof_m = re.search(r'\|bestof=(\d+)', block)
        bestof = int(bestof_m.group(1)) if bestof_m else 3

        date_m = re.search(r'\|date=([^\|\n]+)', block)
        date_str = date_m.group(1).strip() if date_m else None

        opp1_m = re.search(r'\|opponent1=\{\{TeamOpponent\|([^\}]+)\}\}', block)
        opp2_m = re.search(r'\|opponent2=\{\{TeamOpponent\|([^\}]+)\}\}', block)

        team1_name = opp1_m.group(1).strip() if opp1_m else "Team 1"
        team2_name = opp2_m.group(1).strip() if opp2_m else "Team 2"

        # Parse map blocks
        map_blocks = re.findall(r'\|map(\d+)=\{\{Map(.*?)(?=\|map\d+=\{\{Map|\}\}\n|\}\}\s*\n)', block, re.DOTALL)
        
        maps = []
        team1_wins = 0
        team2_wins = 0

        for map_num, map_content in map_blocks:
            game_num = int(map_num)
            
            vod_m = re.search(r'\|vod=([^\s\|\n]+)', map_content)
            vod = vod_m.group(1).strip() if vod_m else None

            t1side_m = re.search(r'\|team1side=([^\s\|\n]+)', map_content)
            t2side_m = re.search(r'\|team2side=([^\s\|\n]+)', map_content)
            len_m = re.search(r'\|length=([^\s\|\n]+)', map_content)
            win_m = re.search(r'\|winner=([^\s\|\n]+)', map_content)

            t1side = t1side_m.group(1).lower() if t1side_m else "blue"
            t2side = t2side_m.group(1).lower() if t2side_m else "red"
            length_str = len_m.group(1) if len_m else None
            duration_sec = parse_duration_to_seconds(length_str)
            winner_num = win_m.group(1) if win_m else None

            if winner_num == '1':
                team1_wins += 1
            elif winner_num == '2':
                team2_wins += 1

            # Hero picks (t1h1..t1h5, t2h1..t2h5)
            t1_picks = [re.search(r'\|t1h' + str(i) + r'=([^\s\|\n]+)', map_content) for i in range(1, 6)]
            t2_picks = [re.search(r'\|t2h' + str(i) + r'=([^\s\|\n]+)', map_content) for i in range(1, 6)]

            # Hero bans (t1b1..t1b5, t2b1..t2b5)
            t1_bans = [re.search(r'\|t1b' + str(i) + r'=([^\s\|\n]+)', map_content) for i in range(1, 6)]
            t2_bans = [re.search(r'\|t2b' + str(i) + r'=([^\s\|\n]+)', map_content) for i in range(1, 6)]

            t1_pick_heroes = [m.group(1).strip() for m in t1_picks if m]
            t2_pick_heroes = [m.group(1).strip() for m in t2_picks if m]

            t1_ban_heroes = [m.group(1).strip() for m in t1_bans if m]
            t2_ban_heroes = [m.group(1).strip() for m in t2_bans if m]

            maps.append({
                "game_number": game_num,
                "team1_side": t1side,
                "team2_side": t2side,
                "duration_seconds": duration_sec,
                "duration_str": length_str,
                "winner_num": winner_num,
                "vod_url": vod,
                "team1_picks": t1_pick_heroes,
                "team2_picks": t2_pick_heroes,
                "team1_bans": t1_ban_heroes,
                "team2_bans": t2_ban_heroes
            })

        series_winner = team1_name if team1_wins > team2_wins else (team2_name if team2_wins > team1_wins else None)

        parsed_series.append({
            "match_tag": match_tag,
            "best_of": bestof,
            "date": date_str,
            "team1": team1_name,
            "team2": team2_name,
            "score": f"{team1_wins}-{team2_wins}",
            "series_winner": series_winner,
            "maps": maps
        })

    print(f"✓ Parsed {len(parsed_series)} series containing {sum(len(s['maps']) for s in parsed_series)} total map games.")
    return parsed_series

if __name__ == '__main__':
    ok, wikitext = test_connectivity()
    if ok:
        snapshot, content_hash = fetch_and_cache_raw()
        series = parse_match_blocks(snapshot['wikitext'])
