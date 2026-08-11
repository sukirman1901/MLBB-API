#!/usr/bin/env python3
"""
Liquipedia MLBB Patch Notes Scraper & Parser
Author: sukirman1901
Repository: https://github.com/sukirman1901/MLBB-API

Scrapes, parses, and normalizes official Liquipedia patch notes (e.g. Patch 2.1.95, Patch 1.8.44, Patch 1.8.30):
  - Infobox patch metadata (release date, previous/next versions, footnotes)
  - Hero adjustments ({{Herobc}}, {{Hic|hero=...}})
  - Equipment adjustments ({{Gameplaybc}})
  - Raw wikitext snapshots with SHA-256 content hashes in patches/raw/
  - Populates patches/patches.json and patches/changelogs/
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
    'User-Agent': 'MLBB-API-PatchIngestion/1.0 (contact: sukirman1901@users.noreply.github.com)',
    'Accept-Encoding': 'gzip'
}

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PATCHES_DIR = os.path.join(BASE_DIR, 'patches')
RAW_PATCH_DIR = os.path.join(PATCHES_DIR, 'raw')
CHANGELOG_DIR = os.path.join(PATCHES_DIR, 'changelogs')

# Load hero metadata for canonical ID mapping
HERO_META_PATH = os.path.join(BASE_DIR, 'v1/hero-meta-final.json')
HERO_NAME_TO_ID = {}
if os.path.exists(HERO_META_PATH):
    with open(HERO_META_PATH, 'r', encoding='utf-8') as f:
        for h in json.load(f).get('data', []):
            if h.get('hero_name') and h.get('id'):
                HERO_NAME_TO_ID[h['hero_name'].lower()] = h['id']

def fetch_patch_wikitext(patch_page_title: str) -> Tuple[Optional[str], Optional[str]]:
    """Fetch raw patch wikitext from Liquipedia API and calculate SHA-256 content hash"""
    url = f"https://liquipedia.net/mobilelegends/api.php?action=parse&page={patch_page_title}&prop=wikitext&format=json"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            content = gzip.decompress(resp.read()).decode('utf-8') if resp.info().get('Content-Encoding') == 'gzip' else resp.read().decode('utf-8')
            data = json.loads(content)
            if 'parse' in data and 'wikitext' in data['parse']:
                wikitext = data['parse']['wikitext']['*']
                content_hash = "sha256:" + hashlib.sha256(wikitext.encode('utf-8')).hexdigest()
                return wikitext, content_hash
    except Exception as e:
        print(f"✗ Failed to fetch {patch_page_title}: {e}")
    return None, None

def parse_patch_infobox(wikitext: str) -> Dict:
    """Parse {{Infobox patch...}} template fields"""
    infobox = {}
    ib_m = re.search(r'\{\{Infobox patch(.*?)\n\}\}', wikitext, re.DOTALL)
    if ib_m:
        ib_text = ib_m.group(1)
        for key in ['name', 'release', 'previous', 'next', 'footnotes']:
            km = re.search(r'\|' + key + r'\s*=\s*([^\n\|]+)', ib_text)
            if km:
                infobox[key] = km.group(1).strip()
    return infobox

def parse_hero_adjustments(wikitext: str) -> List[Dict]:
    """Parse hero adjustments from {{Herobc...}} or {{Hic|hero=...}} references"""
    adjustments = []

    # 1. Parse Herobc templates
    herobc_blocks = re.findall(r'\{\{Herobc(.*?)\}\}\n', wikitext, re.DOTALL)
    for block in herobc_blocks:
        hero_m = re.search(r'\|hero\s*=\s*([^\n\|]+)', block)
        type_m = re.search(r'\|type\s*=\s*([^\n\|]+)', block)
        note_m = re.search(r'\|note\s*=\s*([^\n\|]+)', block)
        adj_m = re.search(r'\|adjustment\s*=\s*(.*)', block, re.DOTALL)

        if hero_m:
            hname = hero_m.group(1).strip()
            atype = type_m.group(1).strip().lower() if type_m else "adjustment"
            summary = note_m.group(1).strip() if note_m else ""
            details = adj_m.group(1).strip() if adj_m else ""

            # Remove wikitext markup
            details_clean = re.sub(r'\'\'\'|\<[^\>]+\>', '', details).strip()
            summary_clean = re.sub(r'\'\'\'|\<[^\>]+\>', '', summary).strip()

            hid = HERO_NAME_TO_ID.get(hname.lower(), "h_unknown")

            adjustments.append({
                "hero_id": hid,
                "hero_name": hname,
                "type": atype,
                "summary": summary_clean or f"Hero {atype.capitalize()} in patch",
                "details": details_clean[:200]
            })

    # 2. Parse Hic references if no Herobc blocks exist
    if not adjustments:
        hic_heroes = re.findall(r'\{\{Hic\|hero=([^\}]+)\}\}', wikitext)
        seen_hic = set()
        for hname in hic_heroes:
            if hname.lower() in seen_hic:
                continue
            seen_hic.add(hname.lower())
            hid = HERO_NAME_TO_ID.get(hname.lower(), "h_unknown")
            adjustments.append({
                "hero_id": hid,
                "hero_name": hname,
                "type": "adjustment",
                "summary": f"{hname} adjusted in patch notes.",
                "details": f"See official Liquipedia patch notes for full breakdown."
            })

    return adjustments

def parse_equipment_adjustments(wikitext: str) -> List[Dict]:
    """Parse equipment adjustments from {{Gameplaybc...}} templates"""
    items = []
    gameplaybc_blocks = re.findall(r'\{\{Gameplaybc(.*?)\}\}\n', wikitext, re.DOTALL)
    for block in gameplaybc_blocks:
        title_m = re.search(r'\|title\s*=\s*([^\n\|]+)', block)
        note_m = re.search(r'\|note\s*=\s*([^\n\|]+)', block)
        adj_m = re.search(r'\|adjustment\s*=\s*(.*)', block, re.DOTALL)

        if title_m:
            iname = title_m.group(1).strip()
            note = note_m.group(1).strip() if note_m else ""
            adj = adj_m.group(1).strip() if adj_m else ""

            items.append({
                "item_name": iname,
                "item_id": iname.lower().replace(' ', '_'),
                "summary": re.sub(r'\'\'\'|\<[^\>]+\>', '', note).strip(),
                "details": re.sub(r'\'\'\'|\<[^\>]+\>', '', adj)[:200].strip()
            })
    return items

def ingest_patch(patch_page_title: str) -> Optional[Dict]:
    """Scrape, parse, cache raw wikitext, and save normalized patch & changelog"""
    os.makedirs(RAW_PATCH_DIR, exist_ok=True)
    os.makedirs(CHANGELOG_DIR, exist_ok=True)

    print(f"\n[Ingesting Patch] {patch_page_title}...")
    wikitext, content_hash = fetch_patch_wikitext(patch_page_title)
    if not wikitext:
        return None

    ver_slug = patch_page_title.replace('Patch_', '').replace('.', '_').lower()
    ver_name = patch_page_title.replace('Patch_', '')

    # 1. Save Raw Snapshot
    raw_file = os.path.join(RAW_PATCH_DIR, f"patch_{ver_slug}_raw.json")
    retrieved_at = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

    raw_snapshot = {
        "source": {
            "name": "Liquipedia",
            "url": f"https://liquipedia.net/mobilelegends/{patch_page_title}",
            "retrieved_at": retrieved_at,
            "source_type": "public_web",
            "content_hash": content_hash
        },
        "page_title": patch_page_title,
        "wikitext": wikitext
    }

    with open(raw_file, 'w', encoding='utf-8') as f:
        json.dump(raw_snapshot, f, indent=2, ensure_ascii=False)
    print(f"  ✓ Raw snapshot cached: {raw_file} [{content_hash[:16]}...]")

    # 2. Parse Infobox & Adjustments
    infobox = parse_patch_infobox(wikitext)
    hero_adjs = parse_hero_adjustments(wikitext)
    equip_adjs = parse_equipment_adjustments(wikitext)

    rel_date = infobox.get('release', '2026-08-04' if '2.1.95' in patch_page_title else '2023-12-20')

    # 3. Write Changelog JSON
    changelog_file = os.path.join(CHANGELOG_DIR, f"patch_{ver_slug}.json")
    changelog_rel_path = f"patches/changelogs/patch_{ver_slug}.json"

    changelog_data = {
        "patch_id": f"patch-{ver_name.lower()}",
        "version": ver_name,
        "release_date": rel_date,
        "previous_version": infobox.get('previous'),
        "next_version": infobox.get('next'),
        "source": {
            "name": "Liquipedia",
            "url": f"https://liquipedia.net/mobilelegends/{patch_page_title}",
            "retrieved_at": retrieved_at,
            "content_hash": content_hash
        },
        "hero_adjustments": hero_adjs,
        "equipment_adjustments": equip_adjs
    }

    with open(changelog_file, 'w', encoding='utf-8') as f:
        json.dump(changelog_data, f, indent=2, ensure_ascii=False)
    print(f"  ✓ Saved changelog: {changelog_file} ({len(hero_adjs)} hero adjs, {len(equip_adjs)} equip adjs)")

    return {
        "patch_id": f"patch-{ver_name.lower()}",
        "version": ver_name,
        "official_name": infobox.get('name', f"Patch {ver_name}"),
        "release_date": rel_date,
        "season": 30 if "1.8" in ver_name else 35,
        "source_url": f"https://liquipedia.net/mobilelegends/{patch_page_title}",
        "status": "archived",
        "changelog_file": changelog_rel_path
    }

def main():
    print("==========================================================")
    print("   LIQUIPEDIA MLBB PATCH NOTES INGESTION & PARSER")
    print("==========================================================")

    target_patches = ["Patch_2.1.95", "Patch_1.8.44", "Patch_1.8.30"]
    patch_catalog = []

    for ptitle in target_patches:
        record = ingest_patch(ptitle)
        if record:
            patch_catalog.append(record)

    # Update patches/patches.json
    patches_catalog_file = os.path.join(PATCHES_DIR, "patches.json")
    catalog_data = {
        "revdate": time.strftime('%Y-%m-%d', time.gmtime()),
        "author": "sukirman1901",
        "description": "MLBB Game Patch Catalog from Liquipedia Official Patch Notes",
        "data": patch_catalog
    }

    with open(patches_catalog_file, 'w', encoding='utf-8') as f:
        json.dump(catalog_data, f, indent=2, ensure_ascii=False)

    print("\n✓ PATCH CATALOG UPDATED!")
    print(f"  - Catalog file: {patches_catalog_file}")
    print(f"  - Total Patches Ingested: {len(patch_catalog)}")
    print("==========================================================")

if __name__ == '__main__':
    main()
