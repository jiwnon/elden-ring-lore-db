import json
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")

with open("data/processed/lore_entries.json", encoding="utf-8") as f:
    data = json.load(f)

print(f"=== 총 엔트리: {len(data)}건 ===\n")

cat_count = Counter(e["category"] for e in data)
game_count = Counter(e["game"] for e in data)

print("--- 카테고리별 ---")
cat_labels = {"item": "아이템 설명", "skill": "전투 기술(Ash/Art)", "spell": "마법/기도"}
for cat, n in sorted(cat_count.items(), key=lambda x: -x[1]):
    label = cat_labels.get(cat, cat)
    print(f"  {label:22} {n:>5}건")

print()
print("--- 게임별 ---")
for game, n in sorted(game_count.items(), key=lambda x: -x[1]):
    label = "기본게임" if game == "base" else "SOTE DLC"
    print(f"  {label:22} {n:>5}건")

melina = [
    e for e in data
    if "melina" in e["text_en"].lower() or "melina" in e["source_name"].lower()
]

print()
print(f"--- Melina 관련: {len(melina)}건 ---")
for e in melina:
    preview = e["text_en"][:120].replace("\n", " ")
    print(f"  [{e['category']:6}] {e['source_name']}")
    print(f"           {preview}")
    print()

# 샘플 10개 (멜리나 우선, 카테고리 골고루)
print("=== 샘플 10개 ===\n")
samples = list(melina)
used_ids = {e["id"] for e in samples}

for cat in ["item", "skill", "spell"]:
    for e in data:
        if len(samples) >= 10:
            break
        if e["category"] == cat and e["id"] not in used_ids:
            samples.append(e)
            used_ids.add(e["id"])

for i, e in enumerate(samples[:10], 1):
    preview = e["text_en"][:100].replace("\n", " ")
    print(f"{i:2}. [{e['game']:4}][{e['category']:6}] {e['source_name']}")
    print(f"    {preview}")
    print()
