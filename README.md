# MLBB-API — Mobile Legends: Bang Bang Esports & Attribute Database

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Repository](https://img.shields.io/badge/GitHub-sukirman1901%2FMLBB--API-blue)](https://github.com/sukirman1901/MLBB-API)
[![Dataset Status](https://img.shields.io/badge/Data_Completeness-100%25-brightgreen)](#-data-completeness--status)

Welcome to **MLBB-API**, a comprehensive Mobile Legends: Bang Bang (MLBB) Attribute Database and Esports Analytics Engine maintained by **sukirman1901**.

This repository provides rich, up-to-date JSON metadata for **132 Heroes**, **89 Items/Equipment**, and the **New 2025/2026 Emblem System**, along with automated scraping tools and data schemas for building advanced Esports Analytics, Draft Pick Simulators, VOD Review Systems, and Discord Bots.

---

## 📊 Dataset Links

* 🦸 **Hero Data (132 Heroes):** [`v1/hero-meta-final.json`](https://github.com/sukirman1901/MLBB-API/blob/main/v1/hero-meta-final.json)
* ⚔️ **Item Data (89 Equipment):** [`v1/item-meta-final.json`](https://github.com/sukirman1901/MLBB-API/blob/main/v1/item-meta-final.json)
* 🛡️ **Emblem Data (7 Sets + 26 Talents):** [`v1/emblem-meta-final.json`](https://github.com/sukirman1901/MLBB-API/blob/main/v1/emblem-meta-final.json)
* 📐 **Esports Analytics Schema:** [`specification/esports_analytics_schema.json`](https://github.com/sukirman1901/MLBB-API/blob/main/specification/esports_analytics_schema.json)

---

## ✅ Data Completeness & Status

| Dataset | Total Entries | Status / Attributes Included |
| :--- | :---: | :--- |
| **Hero Metadata** | **132 Heroes** | 100% Complete (Skills, Cooldowns, Mana Costs, Base Stats HP/Mana/Def/Atk/Speed, Counters & Synergies) |
| **Equipment Items** | **89 Items** | 100% Complete (Stats Modifiers, Unique Passives e.g., *Armor Buster*, *Malefic Energy*, Prices & Build Paths) |
| **Emblem System** | **7 Sets + 26 Talents** | 100% Complete (2025/2026 Role-based Emblems: Common, Tank, Assassin, Mage, Fighter, Support, Marksman) |

---

## 🚀 Automation & Scraper Scripts

This repository includes simple automated Python scripts to keep all datasets and assets up-to-date:

### 1. Hero Data Scraper (`heroes.py`)
Fetches complete hero skills, base stats, counters, synergies, and tiers directly from official APIs.
```bash
python3 heroes.py
```

### 2. Equipment Data Scraper (`equipment.py`)
Parses equipment stats, unique passives, costs, and build paths directly from Fandom MediaWiki API.
```bash
python3 equipment.py
```

### 3. Asset Downloader (`assets.py`)
Downloads and syncs high-resolution PNG image assets into `assets/hero/`, `assets/item/`, and `assets/emblem/`.
```bash
python3 assets.py
```

### 4. Data Transformation (`transform.py`)
Transforms raw payloads into standardized MLBB-API JSON schemas.
```bash
python3 transform.py
```

---

## 🎮 API Features & Data Capabilities

Designed for developers, coaches, and analysts to build MLBB applications:
* **Hero Analytics:** 132 heroes with base stats, skill mechanics, cooldowns, mana costs, counters, synergies, recommended builds, and meta tiers (`SS` / `S` / `A` / `B` / `C`).
* **Equipment & Passives:** 89 items with stat modifiers, unique passive effects (*Armor Buster*, *Malefic Energy*, *Lethality*, etc.), costs, and build paths.
* **Emblem & Talent System:** 7 role emblem sets and 26 ability talents (2025/2026 system).
* **Draft & Counter Engine Data:** Counter-pick relationships, hero combo synergies, and role recommendations.
* **JSON Schemas:** Standardized schemas defined in `specification/` for easy database integration and API development.

---

## 💻 Usage Examples

### Python Example
```python
import json

# Read hero dataset
with open('v1/hero-meta-final.json', 'r', encoding='utf-8') as f:
    heroes = json.load(f)['data']

# Find hero information
sora = next(h for h in heroes if h['hero_name'] == 'Sora')
print(f"Hero: {sora['hero_name']} ({sora['class']})")
print(f"Base HP: {sora['base_stats']['HP']}")
print("Counters:", [c['heroname'] for c in sora['counters']])
```

### Node.js / JavaScript Example
```javascript
const fs = require('fs');

const items = JSON.parse(fs.readFileSync('./v1/item-meta-final.json', 'utf8')).data;
const maleficGun = items.find(i => i.item_name === 'Malefic Gun');

console.log("Stats Modifiers:", maleficGun.data[0].modifiers);
console.log("Unique Passives:", maleficGun.data[0].unique_passive);
```

---

## 📄 License & Author

* **Author:** [sukirman1901](https://github.com/sukirman1901)
* **Repository:** [https://github.com/sukirman1901/MLBB-API](https://github.com/sukirman1901/MLBB-API)
* **License:** [MIT License](LICENSE)
