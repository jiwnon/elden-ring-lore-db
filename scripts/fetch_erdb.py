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
        "Elden Ring base game",
    ),
    (
        "elden_ring_sote.json",
        "https://raw.githubusercontent.com/tefkah/fromsoft-fts/main/assets/data2.json",
        "Shadow of the Erdtree DLC",
    ),
]


def fetch(label: str, url: str, dest: Path):
    print(f"  [{label}]")
    print(f"  URL  : {url}")
    print(f"  Dest : {dest}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "elden-ring-lore-db/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        with open(dest, "wb") as f:
            f.write(data)
        parsed = json.loads(data)
        items = parsed.get("itemLikes", parsed) if isinstance(parsed, dict) else parsed
        count = len(items) if isinstance(items, list) else "?"
        size_kb = len(data) / 1024
        print(f"  -> {count} entries  ({size_kb:.0f} KB)\n")
    except urllib.error.HTTPError as e:
        print(f"  [HTTP {e.code}] {url}\n")
    except Exception as e:
        print(f"  [ERROR] {e}\n")


def run():
    print("=== Downloading Elden Ring text data (fromsoft-fts) ===\n")
    for filename, url, label in SOURCES:
        fetch(label, url, RAW_FROMSOFT / filename)
    print("Done. Run `python scripts/parse_fmg.py` next.")


if __name__ == "__main__":
    run()
