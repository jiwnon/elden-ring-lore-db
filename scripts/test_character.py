import sqlite3, sys
sys.path.insert(0, "app")
sys.stdout.reconfigure(encoding="utf-8")
from character_aliases import get_aliases

conn = sqlite3.connect("data/lore.db")
conn.row_factory = sqlite3.Row

char_name, aliases = get_aliases("melina")
print(f"Character : {char_name}")
print(f"Aliases   : {aliases}\n")

dialogue = conn.execute(
    "SELECT id, source_name, text_en, game FROM entries "
    "WHERE source_name = ? AND category = 'dialogue' ORDER BY game, id",
    (char_name,)
).fetchall()
print(f"본인 대사: {len(dialogue)}건")
for r in dialogue[:5]:
    print(f"  [{r['game']}] {r['text_en'][:75]}")

fts_q = " OR ".join(f'"{t}"' for t in [char_name] + aliases)

mentions = conn.execute(
    "SELECT e.id, e.category, e.source_name, e.text_en "
    "FROM entries_fts f JOIN entries e ON e.rowid = f.rowid "
    "WHERE entries_fts MATCH ? AND e.category != 'dialogue' ORDER BY rank LIMIT 50",
    (fts_q,)
).fetchall()
print(f"\n아이템/이벤트 언급: {len(mentions)}건")
for r in mentions[:5]:
    print(f"  [{r['category']}|{r['source_name']}] {r['text_en'][:75]}")

others = conn.execute(
    "SELECT e.id, e.source_name, e.text_en "
    "FROM entries_fts f JOIN entries e ON e.rowid = f.rowid "
    "WHERE entries_fts MATCH ? AND e.category = 'dialogue' AND e.source_name != ? "
    "ORDER BY rank LIMIT 60",
    (fts_q, char_name)
).fetchall()
print(f"\n타 NPC 언급: {len(others)}건")
for r in others[:5]:
    print(f"  [{r['source_name']}] {r['text_en'][:75]}")

conn.close()
