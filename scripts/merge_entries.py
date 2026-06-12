"""
Merge all processed data into a single lore_entries.json.

Inputs:
  data/processed/lore_entries.json      (items / skills / spells)
  data/processed/dialogue_entries.json  (dialogue / cutscene / event)

Output:
  data/processed/lore_entries.json  (overwritten with full merged set)

Usage:
    python scripts/merge_entries.py
"""

import json
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

OUT_DIR = Path(__file__).parent.parent / "data" / "processed"
ITEM_FILE = OUT_DIR / "lore_entries.json"
DIALOGUE_FILE = OUT_DIR / "dialogue_entries.json"


def load(path: Path) -> list[dict]:
    if not path.exists():
        print(f"  [SKIP] {path.name} not found")
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def run():
    items = load(ITEM_FILE)
    dialogue = load(DIALOGUE_FILE)

    # Deduplicate by id (items take precedence over dialogue for same id)
    seen: set[str] = set()
    merged: list[dict] = []
    for entry in items + dialogue:
        if entry["id"] not in seen:
            seen.add(entry["id"])
            merged.append(entry)

    # Sort: game asc, category asc, id asc
    cat_order = {"item": 0, "skill": 1, "spell": 2, "dialogue": 3, "cutscene": 4, "event": 5}
    merged.sort(key=lambda e: (e.get("game", ""), cat_order.get(e.get("category", ""), 9), e.get("id", "")))

    # Stats
    cat_count = Counter(e["category"] for e in merged)
    game_count = Counter(e["game"] for e in merged)

    print(f"=== Merged: {len(merged)} total entries ===\n")
    print("카테고리:")
    for k, v in sorted(cat_count.items(), key=lambda x: cat_order.get(x[0], 9)):
        print(f"  {k:12} {v:>5}")
    print(f"\n게임별:")
    for k, v in game_count.most_common():
        label = "기본게임" if k == "base" else "SOTE DLC"
        print(f"  {label:12} {v:>5}")

    out_path = OUT_DIR / "lore_entries.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    print(f"\nSaved -> {out_path}")

    # Clean up intermediate file
    DIALOGUE_FILE.unlink(missing_ok=True)
    print(f"Removed intermediate {DIALOGUE_FILE.name}")


if __name__ == "__main__":
    run()
