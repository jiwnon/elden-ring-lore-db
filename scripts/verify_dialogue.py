import json
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")

with open("data/processed/dialogue_entries.json", encoding="utf-8") as f:
    data = json.load(f)

cat_count = Counter(e["category"] for e in data)
game_count = Counter(e["game"] for e in data)
speaker_count = Counter(e["source_name"] for e in data)

print("카테고리:")
for k, v in cat_count.most_common():
    print(f"  {k}: {v}")

print("\n게임별:")
for k, v in game_count.most_common():
    print(f"  {k}: {v}")

print("\n화자 TOP 20:")
for k, v in speaker_count.most_common(20):
    print(f"  {v:>4}  {k}")

melina = [e for e in data if "melina" in e["source_name"].lower() or "melina" in e["text_en"].lower()]
print(f"\nMelina 관련: {len(melina)}건")
for e in melina[:6]:
    print(f"  [{e['source_name']}] {e['text_en'][:90]}")
