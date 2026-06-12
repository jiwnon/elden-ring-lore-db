import sqlite3
import sys
sys.stdout.reconfigure(encoding="utf-8")

conn = sqlite3.connect("data/lore.db")
conn.row_factory = sqlite3.Row

QUERIES = ["Melina", "Ranni", "Elden Lord"]

for q in QUERIES:
    fts_q = f'"{q}"'
    rows = conn.execute(
        "SELECT e.category, e.source_name, e.text_en "
        "FROM entries_fts f JOIN entries e ON e.rowid = f.rowid "
        "WHERE entries_fts MATCH ? ORDER BY rank LIMIT 5",
        (fts_q,)
    ).fetchall()
    print(f"=== {q} ({len(rows)} hits) ===")
    for r in rows:
        print(f"  [{r['category']:8}|{r['source_name']:<30}] {r['text_en'][:70]}")
    print()

conn.close()
