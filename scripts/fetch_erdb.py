"""
Download Elden Ring data from public datasets.

Sources:
  - erdb:         https://github.com/EldenRingDatabase/erdb  (MIT)
  - fromsoft-fts: https://github.com/tefkah/fromsoft-fts

Usage:
    python scripts/fetch_erdb.py
"""

import json
import urllib.request
import urllib.error
from pathlib import Path

RAW_DIR = Path(__file__).parent.parent / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

# erdb — structured item/NPC data (MIT license)
ERDB_BASE = "https://raw.githubusercontent.com/EldenRingDatabase/erdb/main/er-params"
ERDB_TARGETS = [
    ("weapons.json",      "weapons/weapons.json"),
    ("armors.json",       "armors/armors.json"),
    ("talismans.json",    "talismans/talismans.json"),
    ("goods.json",        "goods/goods.json"),
    ("ashes_of_war.json", "ashes-of-war/ashes-of-war.json"),
    ("spells.json",       "spells/spells.json"),
    ("spirit_ashes.json", "spirit-ashes/spirit-ashes.json"),
]

# fromsoft-fts — item descriptions + NPC dialogue (searchable JSON)
FROMSOFT_FTS_BASE = "https://raw.githubusercontent.com/tefkah/fromsoft-fts/main/public/data"
FROMSOFT_TARGETS = [
    ("fts_elden_ring_items.json",    "elden-ring/items.json"),
    ("fts_elden_ring_dialogue.json", "elden-ring/dialogue.json"),
]


def fetch(url: str, dest: Path):
    print(f"  Fetching {dest.name}  <- {url}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "elden-ring-lore-db/1.0"})
        with urllib.request.urlopen(req) as resp:
            data = resp.read()
        with open(dest, "wb") as f:
            f.write(data)
        parsed = json.loads(data)
        count = len(parsed) if isinstance(parsed, (dict, list)) else "?"
        print(f"    -> {count} entries saved to {dest}")
    except urllib.error.HTTPError as e:
        print(f"    [HTTP {e.code}] {url}")
    except Exception as e:
        print(f"    [ERROR] {e}")


def run():
    print("=== Fetching erdb data ===")
    for filename, path in ERDB_TARGETS:
        fetch(f"{ERDB_BASE}/{path}", RAW_DIR / filename)

    print("\n=== Fetching fromsoft-fts data ===")
    for filename, path in FROMSOFT_TARGETS:
        fetch(f"{FROMSOFT_FTS_BASE}/{path}", RAW_DIR / filename)

    print(f"\nAll done. Run `python scripts/parse_fmg.py` next.")


if __name__ == "__main__":
    run()
