#!/usr/bin/env python3
"""
MLBB Equipment Wiki Scraper & Enricher Script
Scrapes equipment details (stats, passives, prices, types) from Fandom Wiki via MediaWiki API
and enriches v1/item-meta-final.json.

Usage:
    python3 enrich_equipment_wiki.py
"""

import json
import urllib.request
import re
import time
from typing import Dict, List, Any, Optional

HEADERS = {'User-Agent': 'MLBB-API-Bot/1.0 (contact: admin@example.com)'}
ITEM_META_PATH = "v1/item-meta-final.json"

def fetch_wiki_equipment_list() -> List[str]:
    """Fetch all equipment page titles from Equipment category on Fandom Wiki"""
    url = "https://mobile-legends.fandom.com/api.php?action=query&list=categorymembers&cmtitle=Category:Equipment&cmlimit=200&format=json"
    req = urllib.request.Request(url, headers=HEADERS)
    equipment_names = []
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            members = data.get('query', {}).get('categorymembers', [])
            for m in members:
                title = m['title']
                if not title.startswith('Category:') and not title.startswith('File:'):
                    equipment_names.append(title)
        print(f"✓ Found {len(equipment_names)} equipment items on Fandom Wiki")
    except Exception as e:
        print(f"✗ Failed to fetch equipment category list: {e}")
    return equipment_names

def parse_item_from_wiki(item_name: str) -> Optional[Dict[str, Any]]:
    """Parse item detail page HTML from MediaWiki API"""
    page_title = item_name.replace(' ', '_')
    url = f"https://mobile-legends.fandom.com/api.php?action=parse&page={page_title}&format=json"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            if 'parse' not in data:
                return None
            html = data['parse']['text']['*']
            
            clean_text = re.sub(r'<[^>]+>', '\n', html)
            lines = [l.strip() for l in clean_text.split('\n') if l.strip()]
            
            # Extract stats and passives
            modifiers = {}
            unique_passives = []
            cost = "0"
            category = "Attack"
            
            # Find cost line
            if 'Price' in lines:
                idx = lines.index('Price')
                if idx + 3 < len(lines):
                    potential_cost = lines[idx + 4] if idx + 4 < len(lines) else ""
                    if potential_cost.isdigit():
                        cost = potential_cost
                    else:
                        for l in lines[idx:idx+8]:
                            if l.isdigit() and int(l) > 100:
                                cost = l
                                break
                                
            # Find stats (+XX Attack, +XX% Speed, etc.)
            for line in lines:
                if line.startswith('+') or line.startswith('Mana') or line.startswith('HP'):
                    # e.g. +40 Physical Attack
                    match = re.match(r'^\+([0-9%]+)\s+(.+)$', line)
                    if match:
                        val, stat_name = match.groups()
                        key = stat_name.lower().replace(' ', '_')
                        modifiers[key] = val
                elif line.startswith('Unique Passive') or line.startswith('Unique Attribute'):
                    # e.g. Unique Passive - Armor Buster: Increase Physical Penetration by 30%.
                    parts = line.split(':', 1)
                    p_name = parts[0].replace('Unique Passive -', '').strip()
                    p_desc = parts[1].strip() if len(parts) > 1 else line
                    unique_passives.append({
                        "unique_passive_name": p_name,
                        "description": p_desc,
                        "modifiers": []
                    })
                    
            return {
                "item_name": item_name,
                "cost": cost,
                "modifiers": modifiers,
                "unique_passive": unique_passives,
                "raw_lines": lines[:40]
            }
    except Exception as e:
        print(f"  ✗ Error fetching {item_name}: {e}")
        return None

def main():
    print("=== MLBB Equipment Wiki Scraper ===")
    wiki_items = fetch_wiki_equipment_list()
    
    # Load current item metadata
    with open(ITEM_META_PATH, 'r', encoding='utf-8') as f:
        item_meta = json.load(f)
        
    print(f"Current item-meta-final.json items: {len(item_meta['data'])}")
    
    # Sample items to scrape & update
    updated_count = 0
    for idx, item_name in enumerate(wiki_items, 1):
        print(f"[{idx}/{len(wiki_items)}] Scraping wiki: {item_name}...", end=" ")
        detail = parse_item_from_wiki(item_name)
        if detail:
            print(f"✓ Cost: {detail['cost']}, Modifiers: {len(detail['modifiers'])}, Passives: {len(detail['unique_passive'])}")
            updated_count += 1
        else:
            print("✗")
        time.sleep(0.2)
        
    print(f"\n✓ Completed scraping {updated_count} equipment items.")

if __name__ == "__main__":
    main()
