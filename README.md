# MLBB-API — Mobile Legends: Bang Bang Knowledge Base & Esports Match Datasets

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Repository](https://img.shields.io/badge/GitHub-sukirman1901%2FMLBB--API-blue)](https://github.com/sukirman1901/MLBB-API)
[![Dataset Status](https://img.shields.io/badge/Data_Completeness-100%25-brightgreen)](#-data-completeness--status)

Welcome to **MLBB-API**, an open-source Mobile Legends: Bang Bang (MLBB) Attribute Database, Esports Match Datasets, and Analytics Engine maintained by **sukirman1901**.

---

## 🏗️ Project Architecture: V0 vs V1

```text
                 MLBB-API ENGINE
                        │
       ┌────────────────┴────────────────┐
       │                                 │
  V0: STATIC KNOWLEDGE            V1: ESPORTS MATCH DATASET
       │                                 │
 Heroes (132)                     Tournaments (MPL/M-Series)
 Items (89)                       Teams & Rosters
 Emblems (7 Sets + 26 Talents)    Player Profiles
 Image Assets (247 PNGs/WebPs)    Matches & Draft Picks/Bans
       │                                 │
       └────────────────┬────────────────┘
                        ↓
                 ANALYTICS ENGINE
             (Draft & Meta Tracing)
```

---

## 📊 Dataset Structure & Quick Links

### 1. V0 — Static Knowledge Base (`v1/`)
* 🦸 **Hero Data (132 Heroes):** [`v1/hero-meta-final.json`](https://github.com/sukirman1901/MLBB-API/blob/main/v1/hero-meta-final.json)
* ⚔️ **Item Data (89 Equipment):** [`v1/item-meta-final.json`](https://github.com/sukirman1901/MLBB-API/blob/main/v1/item-meta-final.json)
* 🛡️ **Emblem Data (7 Sets + 26 Talents):** [`v1/emblem-meta-final.json`](https://github.com/sukirman1901/MLBB-API/blob/main/v1/emblem-meta-final.json)

### 2. V1 — Esports Match Datasets (`esports/`)
* 🏆 **Tournaments:** [`esports/tournaments/mpl_id_s16.json`](https://github.com/sukirman1901/MLBB-API/blob/main/esports/tournaments/mpl_id_s16.json)
* 🛡️ **Teams & Rosters:** [`esports/teams/teams.json`](https://github.com/sukirman1901/MLBB-API/blob/main/esports/teams/teams.json)
* 👤 **Player Profiles:** [`esports/players/players.json`](https://github.com/sukirman1901/MLBB-API/blob/main/esports/players/players.json)
* 🎮 **Matches & Draft Picks:** [`esports/matches/mpl_id_s16_g1.json`](https://github.com/sukirman1901/MLBB-API/blob/main/esports/matches/mpl_id_s16_g1.json)
* 📐 **Esports Analytics Schema:** [`specification/esports_analytics_schema.json`](https://github.com/sukirman1901/MLBB-API/blob/main/specification/esports_analytics_schema.json)

---

## ✅ Data Completeness & Status

| Category | Total Entries | Attributes & Coverage Included |
| :--- | :---: | :--- |
| **Hero Metadata** | **132 Heroes** | 100% Complete (Skills, Cooldowns, Mana Costs, Base Stats HP/Mana/Def/Atk/Speed, Counters, Synergies, Recommended Builds, Tiers) |
| **Equipment Items** | **89 Items** | 100% Complete (Stats Modifiers, Unique Passives e.g., *Armor Buster*, *Malefic Energy*, Prices & Build Paths) |
| **Emblem System** | **7 Sets + 26 Talents** | 100% Complete (2025/2026 Role-based Emblems: Common, Tank, Assassin, Mage, Fighter, Support, Marksman) |
| **Esports Match Data** | **Match & Draft Records** | Draft Picks & Bans (Blue/Red side), Player Performance KDA, GPM, Damage Dealt/Taken, Itemization & Emblem Choices |

---

## ⚡ Automation & Scraper Scripts (`scripts/`)

All maintainer scripts are stored inside the `scripts/` directory:

### 1. Hero Data Scraper (`scripts/heroes.py`)
Fetches complete hero skills, base stats, counters, synergies, and tiers directly from official APIs.
```bash
python3 scripts/heroes.py
```

### 2. Equipment Data Scraper (`scripts/equipment.py`)
Parses equipment stats, unique passives, costs, and build paths directly from Fandom MediaWiki API.
```bash
python3 scripts/equipment.py
```

### 3. Asset Downloader (`scripts/assets.py`)
Downloads and syncs high-resolution PNG image assets into `assets/hero/`, `assets/item/`, and `assets/emblem/`.
```bash
python3 scripts/assets.py
```

### 4. Data Transformation (`scripts/transform.py`)
Transforms raw payloads into standardized MLBB-API JSON schemas.
```bash
python3 scripts/transform.py
```

---

## 💻 Usage Examples

### Python: Linking Static Knowledge to Match Data
```python
import json

# Load Static Hero Knowledge & Match Data
with open('v1/hero-meta-final.json', 'r') as f:
    heroes = json.load(f)['data']

with open('esports/matches/mpl_id_s16_g1.json', 'r') as f:
    match = json.load(f)

print(f"Match: {match['blue_team']['name']} vs {match['red_team']['name']} (Winner: {match['winner']})")
print("Blue Bans:", match['blue_team']['bans'])
print("Blue Picks:", [p['hero'] for p in match['blue_team']['picks']])

# Inspect Player Performance for Kairi (Ling)
kairi_perf = next(p for p in match['player_performances'] if p['player'] == 'Kairi')
print(f"\nPlayer: {kairi_perf['player']} | Hero: {kairi_perf['hero']}")
print(f"KDA: {kairi_perf['kda']['kills']}/{kairi_perf['kda']['deaths']}/{kairi_perf['kda']['assists']} | GPM: {kairi_perf['gpm']}")
print("Build Items:", kairi_perf['items'])
print("Emblem:", kairi_perf['emblem'])
```

---

## 📄 License & Author

* **Author:** [sukirman1901](https://github.com/sukirman1901)
* **Repository:** [https://github.com/sukirman1901/MLBB-API](https://github.com/sukirman1901/MLBB-API)
* **License:** [MIT License](LICENSE)
