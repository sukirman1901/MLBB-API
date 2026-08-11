#!/usr/bin/env python3
"""
Confidence-Based Entity & Hero Alias Mapper
Author: sukirman1901
Repository: https://github.com/sukirman1901/MLBB-API

Maps Liquipedia hero aliases to canonical Hero IDs in v1/hero-meta-final.json.
Rules:
  - Explicit mapping dictionary with confidence scores (1.0 for high confidence).
  - Unmapped/ambiguous aliases (< 1.0 confidence) are recorded in esports/unresolved_entities.json.
  - Never force ambiguous entity mappings.
"""

import json
import os
from typing import Dict, Tuple, Optional, Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load canonical hero metadata
HERO_META_PATH = os.path.join(BASE_DIR, 'v1/hero-meta-final.json')
with open(HERO_META_PATH, 'r', encoding='utf-8') as f:
    HERO_META = json.load(f)['data']

# Create mapping dictionary from hero_name and exact aliases
HERO_CANONICAL_MAP = {}
for h in HERO_META:
    if h.get('hero_name') == 'None' or not h.get('id'):
        continue
    hid = h['id']
    name = h['hero_name']
    
    # Standard name variations
    HERO_CANONICAL_MAP[name.lower()] = (hid, name, 1.0)
    HERO_CANONICAL_MAP[name.lower().replace(' ', '_')] = (hid, name, 1.0)
    HERO_CANONICAL_MAP[name.lower().replace(' ', '')] = (hid, name, 1.0)
    HERO_CANONICAL_MAP[name.lower().replace('-', '')] = (hid, name, 1.0)

# Explicit Liquipedia Hero Short Aliases Dictionary
LIQUIPEDIA_ALIASES = {
    'teri': 'Terizla',
    'lapu': 'Lapu-Lapu',
    'bea': 'Beatrix',
    'fara': 'Faramis',
    'fanny': 'Fanny',
    'baxia': 'Baxia',
    'nova': 'Novaria',
    'wan': 'Wanwan',
    'valen': 'Valentina',
    'nolan': 'Nolan',
    'guin': 'Guinevere',
    'joy': 'Joy',
    'karrie': 'Karrie',
    'ixia': 'Ixia',
    'paqui': 'Paquito',
    'bruno': 'Bruno',
    'mino': 'Minotaur',
    'khaleed': 'Khaleed',
    'aamon': 'Aamon',
    'dyr': 'Dyrroth',
    'kaja': 'Kaja',
    'diggie': 'Diggie',
    'hilda': 'Hilda',
    'angela': 'Angela',
    'arlot': 'Arlott',
    'arlott': 'Arlott',
    'akai': 'Akai',
    'ling': 'Ling',
    'hayabusa': 'Hayabusa',
    'lancelot': 'Lancelot',
    'chou': 'Chou',
    'pharsa': 'Pharsa',
    'yve': 'Yve',
    'nana': 'Nana',
    'claude': 'Claude',
    'brody': 'Brody',
    'edith': 'Edith',
    'martis': 'Martis',
    'lylia': 'Lylia',
    'fredrinn': 'Fredrinn',
    'barats': 'Barats',
    'gloo': 'Gloo',
    'uranus': 'Uranus',
    'terizla': 'Terizla',
    'yu_zhong': 'Yu Zhong',
    'yuzhong': 'Yu Zhong',
    'mathilda': 'Mathilda',
    'floryn': 'Floryn',
    'rafaela': 'Rafaela',
    'estes': 'Estes',
    'khufra': 'Khufra',
    'atlas': 'Atlas',
    'grock': 'Grock',
    'tigreal': 'Tigreal',
    'badang': 'Badang',
    'leomord': 'Leomord',
    'thamuz': 'Thamuz',
    'aldous': 'Aldous',
    'argus': 'Argus',
    'jawhead': 'Jawhead',
    'alpha': 'Alpha',
    'saber': 'Saber',
    'eudora': 'Eudora',
    'aurora': 'Aurora',
    'gord': 'Gord',
    'kagura': 'Kagura',
    'cyclops': 'Cyclops',
    'harley': 'Harley',
    'odin': 'Odin',
    'change': "Chang'e",
    "chang'e": "Chang'e",
    'lunox': 'Lunox',
    'harith': 'Harith',
    'kadita': 'Kadita',
    'guinevere': 'Guinevere',
    'esmeralda': 'Esmeralda',
    'xborg': 'X.Borg',
    'x.borg': 'X.Borg',
    'diaspar': 'Dyrroth',
    'wanwan': 'Wanwan',
    'silvanna': 'Silvanna',
    'cecilion': 'Cecilion',
    'carmilla': 'Carmilla',
    'popol': 'Popol and Kupa',
    'luoyi': 'Luo Yi',
    'bene': 'Benedetta',
    'fred': 'Fredrinn',
    'haya': 'Hayabusa',
    'lance': 'Lancelot',
    'leo': 'Leomord',
    'mathil': 'Mathilda',
    'paq': 'Paquito',
    'rafa': 'Rafaela',
    'yu': 'Yu Zhong',
    'benedetta': 'Benedetta',
    'helcurt': 'Helcurt',
    'phoveus': 'Phoveus',
    'natan': 'Natan',
    'valentina': 'Valentina',
    'yin': 'Yin',
    'xavier': 'Xavier',
    'julian': 'Julian',
    'cici': 'Cici',
    'zhuxin': 'Zhuxin',
    'suyou': 'Suyou',
    'lukas': 'Lukas',
    'marcel': 'Marcel',
    'sora': 'Sora'
}

UNRESOLVED_ENTITIES = []

def map_hero_alias(source_alias: str) -> Tuple[Optional[str], Optional[str], float]:
    """
    Rule 2: Confidence-based entity mapping.
    Returns (canonical_id, canonical_name, confidence).
    """
    if not source_alias:
        return None, None, 0.0

    raw_clean = source_alias.strip().lower()

    # 1. Direct match in canonical map
    if raw_clean in HERO_CANONICAL_MAP:
        hid, name, conf = HERO_CANONICAL_MAP[raw_clean]
        return hid, name, conf

    # 2. Match via Liquipedia Aliases
    if raw_clean in LIQUIPEDIA_ALIASES:
        canonical_name = LIQUIPEDIA_ALIASES[raw_clean]
        if canonical_name.lower() in HERO_CANONICAL_MAP:
            hid, name, conf = HERO_CANONICAL_MAP[canonical_name.lower()]
            return hid, name, 1.0

    # 3. Unresolved entity
    unresolved_record = {
        "source_name": source_alias,
        "normalized_name": raw_clean,
        "entity_type": "hero",
        "source": "Liquipedia",
        "confidence": 0.0,
        "reason": "No confident canonical match in dictionary"
    }
    UNRESOLVED_ENTITIES.append(unresolved_record)
    return None, None, 0.0

def save_unresolved_entities():
    """Rule 3: Save unresolved entities to esports/unresolved_entities.json"""
    out_path = os.path.join(BASE_DIR, 'esports/unresolved_entities.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(UNRESOLVED_ENTITIES, f, indent=2, ensure_ascii=False)
    if UNRESOLVED_ENTITIES:
        print(f"⚠ Logged {len(UNRESOLVED_ENTITIES)} unresolved entities to {out_path}")
