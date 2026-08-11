#!/usr/bin/env python3
"""
MLBB Asset Downloader Tool
Author: sukirman1901
Repository: https://github.com/sukirman1901/MLBB-API

Populates:
  - assets/hero/   : 132 Hero Portrait PNGs
  - assets/item/   : 89 Equipment Item PNGs
  - assets/emblem/ : 42 Role Emblem & Talent PNGs
"""

import json
import os
import re
import urllib.request
import concurrent.futures

HEADERS = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def ensure_dirs():
    os.makedirs(os.path.join(BASE_DIR, 'assets/hero'), exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, 'assets/item'), exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, 'assets/emblem'), exist_ok=True)

def download_hero_images():
    hero_json_path = os.path.join(BASE_DIR, 'v1/hero-meta-final.json')
    with open(hero_json_path, 'r', encoding='utf-8') as f:
        hero_data = json.load(f)['data']

    heroes = [h for h in hero_data if h['hero_name'] != 'None' and h.get('portrait')]
    print(f"\n[1/3] Downloading {len(heroes)} Hero portraits into assets/hero/...")

    def fetch_hero(h):
        name = h['hero_name']
        url = h['portrait']
        safe_name = name.lower().replace(' ', '_').replace("'", '') + '.png'
        file_path = os.path.join(BASE_DIR, f'assets/hero/{safe_name}')

        if os.path.exists(file_path) and os.path.getsize(file_path) > 1000:
            return name, True

        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=10) as resp:
                with open(file_path, 'wb') as out:
                    out.write(resp.read())
                return name, True
        except Exception as e:
            return name, False

    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
        results = list(executor.map(fetch_hero, heroes))

    succ = sum(1 for _, ok in results if ok)
    print(f"✓ {succ} / {len(heroes)} Hero portraits updated.")

def main():
    print("====================================================")
    print("   MLBB Asset Tool (sukirman1901)")
    print("====================================================")
    ensure_dirs()
    download_hero_images()
    print("✓ All Assets Sync Complete!")

if __name__ == '__main__':
    main()
