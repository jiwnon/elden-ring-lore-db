"""
Parse downloaded raw data into unified lore_entries.json.

Input:
  data/raw/fromsoft_fts/elden_ring_base.json  — { itemLikes: [...] }
  data/raw/fromsoft_fts/elden_ring_sote.json  — { itemLikes: [...] }

Output:
  data/processed/lore_entries.json

Each entry schema:
  {
    "id":          str,   e.g. "base_1000"
    "category":    str,   "item" | "skill" | "spell" | "consumable"
    "source_name": str,   item display name
    "text_en":     str,   in-game description (English)
    "text_ko":     str,   Korean translation (empty for now)
    "location":    str,   empty until location data is added
    "game":        str,   "base" | "sote"
  }
"""

import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
RAW_DIR = ROOT / "data" / "raw" / "fromsoft_fts"
OUT_DIR = ROOT / "data" / "processed"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# fromsoft-fts type → our category
TYPE_MAP = {
    "talisman":   "item",
    "goods":      "item",
    "ash":        "skill",
    "art":        "skill",
    "sorcery":    "spell",
    "incantation":"spell",
    "weapon":     "item",
    "armor":      "item",
    "shield":     "item",
}

SOURCES = [
    ("elden_ring_base.json", "base"),
    ("elden_ring_sote.json", "sote"),
]


def parse_file(path: Path, game: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    items = raw.get("itemLikes", []) if isinstance(raw, dict) else raw
    entries = []

    for item in items:
        text = (item.get("description") or "").strip()
        if not text:
            continue

        raw_type = (item.get("type") or "").lower()
        sub_type = (item.get("subType") or "").lower()
        category = TYPE_MAP.get(sub_type) or TYPE_MAP.get(raw_type) or "item"

        entries.append({
            "id":          f"{game}_{item.get('id', '')}",
            "category":    category,
            "source_name": (item.get("title") or "").strip(),
            "text_en":     text,
            "text_ko":     "",
            "location":    "",
            "game":        game,
        })

    return entries


def run():
    all_entries: list[dict] = []

    for filename, game in SOURCES:
        path = RAW_DIR / filename
        if not path.exists():
            print(f"  [SKIP] {filename} not found — run fetch_erdb.py first")
            continue

        print(f"  Parsing {filename} ({game})...")
        entries = parse_file(path, game)
        all_entries.extend(entries)

        by_cat: dict[str, int] = {}
        for e in entries:
            by_cat[e["category"]] = by_cat.get(e["category"], 0) + 1
        for cat, n in sorted(by_cat.items()):
            print(f"    {cat:15} {n:>5} entries")
        print(f"    {'TOTAL':15} {len(entries):>5}\n")

    out_path = OUT_DIR / "lore_entries.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_entries, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(all_entries)} total entries -> {out_path}")


if __name__ == "__main__":
    run()
