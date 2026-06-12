"""
Parse Elden Ring FMG (text) data from erdb or similar extracted sources.
Input:  data/raw/*.json (from erdb / yabber extraction)
Output: data/processed/lore_entries.json
"""

import json
import os
import re
from pathlib import Path

RAW_DIR = Path(__file__).parent.parent / "data" / "raw"
OUT_DIR = Path(__file__).parent.parent / "data" / "processed"
OUT_DIR.mkdir(parents=True, exist_ok=True)

CATEGORY_MAP = {
    "weapon": "item",
    "armor": "item",
    "talisman": "item",
    "spell": "item",
    "ash_of_war": "item",
    "npc": "dialogue",
    "talk": "dialogue",
    "goods": "item",
    "cutscene": "cutscene",
}


def detect_category(filename: str) -> str:
    name = filename.lower()
    for key, cat in CATEGORY_MAP.items():
        if key in name:
            return cat
    return "misc"


def parse_erdb_file(filepath: Path) -> list[dict]:
    """Parse a single erdb-format JSON file into lore entries."""
    with open(filepath, encoding="utf-8") as f:
        raw = json.load(f)

    entries = []
    category = detect_category(filepath.stem)
    source_name = filepath.stem

    # erdb format: dict of id -> { summary, description, ... }
    if isinstance(raw, dict):
        for entry_id, entry in raw.items():
            text_en = entry.get("description") or entry.get("summary") or ""
            text_ko = entry.get("description_ko") or entry.get("summary_ko") or ""
            name = entry.get("name", entry_id)
            location = entry.get("location", "")

            if not text_en.strip():
                continue

            entries.append({
                "id": f"{source_name}_{entry_id}",
                "category": category,
                "source_name": name,
                "text_en": text_en.strip(),
                "text_ko": text_ko.strip(),
                "location": location,
            })

    # list format: [ { id, text, ... } ]
    elif isinstance(raw, list):
        for item in raw:
            text_en = item.get("text_en") or item.get("text") or item.get("description") or ""
            if not text_en.strip():
                continue
            entries.append({
                "id": item.get("id", ""),
                "category": category,
                "source_name": item.get("name") or item.get("source_name") or source_name,
                "text_en": text_en.strip(),
                "text_ko": item.get("text_ko") or item.get("text_ja") or "",
                "location": item.get("location") or item.get("region") or "",
            })

    return entries


def run():
    all_entries: list[dict] = []
    raw_files = list(RAW_DIR.glob("*.json"))

    if not raw_files:
        print(f"No JSON files found in {RAW_DIR}")
        print("Place extracted erdb/FMG JSON files there and re-run.")
        return

    for path in raw_files:
        print(f"  Parsing {path.name}...")
        try:
            entries = parse_erdb_file(path)
            all_entries.extend(entries)
            print(f"    -> {len(entries)} entries")
        except Exception as e:
            print(f"    [ERROR] {e}")

    out_path = OUT_DIR / "lore_entries.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_entries, f, ensure_ascii=False, indent=2)

    print(f"\nTotal: {len(all_entries)} entries saved to {out_path}")


if __name__ == "__main__":
    run()
