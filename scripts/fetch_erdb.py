"""
Download Elden Ring raw text data from public sources.

Sources:
  - fromsoft-fts: https://github.com/tefkah/fromsoft-fts
    assets/data.json  — base game items (talisman, ash, art, goods, sorcery)
    assets/data2.json — Shadow of the Erdtree DLC

Output:
  data/raw/fromsoft_fts/elden_ring_base.json
  data/raw/fromsoft_fts/elden_ring_sote.json

Usage:
    python scripts/fetch_erdb.py
"""

import json
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).parent.parent
RAW_FROMSOFT = ROOT / "data" / "raw" / "fromsoft_fts"
RAW_FROMSOFT.mkdir(parents=True, exist_ok=True)

SOURCES = [
    (
        "elden_ring_base.json",
        "https://raw.githubusercontent.com/tefkah/fromsoft-fts/main/assets/data.json",
        "Elden Ring base game (items)",
    ),
    (
        "elden_ring_sote.json",
        "https://raw.githubusercontent.com/tefkah/fromsoft-fts/main/assets/data2.json",
        "Shadow of the Erdtree DLC (items)",
    ),
    (
        "elden_ring_base.html",
        "https://raw.githubusercontent.com/tefkah/fromsoft-fts/main/assets/Elden%20Text.html",
        "Elden Ring base game (FMG text dump — dialogue/cutscene/names)",
    ),
    (
        "elden_ring_sote.html",
        "https://raw.githubusercontent.com/tefkah/fromsoft-fts/main/assets/Elden%20Text%20SOTE.html",
        "Shadow of the Erdtree (FMG text dump)",
    ),
]


def fetch(label: str, url: str, dest: Path):
    if dest.exists():
        size_kb = dest.stat().st_size / 1024
        print(f"  [{label}] already exists ({size_kb:.0f} KB) - skip\n")
        return
    print(f"  [{label}]")
    print(f"  URL  : {url}")
    print(f"  Dest : {dest}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "elden-ring-lore-db/1.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
        with open(dest, "wb") as f:
            f.write(data)
        size_kb = len(data) / 1024
        if dest.suffix == ".json":
            parsed = json.loads(data)
            items = parsed.get("itemLikes", parsed) if isinstance(parsed, dict) else parsed
            count = len(items) if isinstance(items, list) else "?"
            print(f"  -> {count} entries  ({size_kb:.0f} KB)\n")
        else:
            print(f"  -> {size_kb:.0f} KB\n")
    except urllib.error.HTTPError as e:
        print(f"  [HTTP {e.code}] {url}\n")
    except Exception as e:
        print(f"  [ERROR] {e}\n")


def run():
    print("=== Downloading Elden Ring text data (fromsoft-fts) ===\n")
    for filename, url, label in SOURCES:
        fetch(label, url, RAW_FROMSOFT / filename)
    print("Done.")
    print("Next steps:")
    print("  python scripts/parse_fmg.py   — items / skills / spells")
    print("  python scripts/parse_html.py  — NPC dialogue / cutscenes")


if __name__ == "__main__":
    run()
