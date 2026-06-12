"""
Build SQLite database with FTS5 full-text search index.

Input:  data/processed/lore_entries.json
Output: data/lore.db

Tables:
  entries        — main data table
  entries_fts    — FTS5 virtual table (searches text_en + source_name)

Usage:
    python scripts/build_db.py
"""

import json
import sqlite3
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent.parent
JSON_PATH = ROOT / "data" / "processed" / "lore_entries.json"
DB_PATH = ROOT / "data" / "lore.db"


def build(entries: list[dict], conn: sqlite3.Connection):
    cur = conn.cursor()

    cur.executescript("""
        DROP TABLE IF EXISTS entries_fts;
        DROP TABLE IF EXISTS entries;

        CREATE TABLE entries (
            id          TEXT PRIMARY KEY,
            category    TEXT NOT NULL,
            source_name TEXT NOT NULL,
            text_en     TEXT NOT NULL,
            text_ko     TEXT DEFAULT '',
            location    TEXT DEFAULT '',
            game        TEXT NOT NULL
        );

        CREATE INDEX idx_entries_category ON entries(category);
        CREATE INDEX idx_entries_game     ON entries(game);
        CREATE INDEX idx_entries_source   ON entries(source_name);

        CREATE VIRTUAL TABLE entries_fts USING fts5(
            id UNINDEXED,
            source_name,
            text_en,
            content='entries',
            content_rowid='rowid',
            tokenize='unicode61'
        );
    """)

    cur.executemany(
        "INSERT INTO entries(id, category, source_name, text_en, text_ko, location, game) "
        "VALUES(:id, :category, :source_name, :text_en, :text_ko, :location, :game)",
        entries,
    )

    # Populate FTS index
    cur.execute("""
        INSERT INTO entries_fts(rowid, id, source_name, text_en)
        SELECT rowid, id, source_name, text_en FROM entries
    """)

    conn.commit()


def run():
    print(f"Loading {JSON_PATH.name}...")
    with open(JSON_PATH, encoding="utf-8") as f:
        entries = json.load(f)
    print(f"  {len(entries)} entries loaded")

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")

    print(f"Building {DB_PATH.name}...")
    build(entries, conn)
    conn.close()

    size_kb = DB_PATH.stat().st_size / 1024
    print(f"  Done. DB size: {size_kb:.0f} KB")

    # Quick sanity check
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM entries")
    total = cur.fetchone()[0]

    print(f"\n--- Sanity check ---")
    print(f"  Total rows: {total}")

    print("\n  FTS search: 'Melina'")
    cur.execute("""
        SELECT e.id, e.source_name, e.text_en
        FROM entries_fts f
        JOIN entries e ON e.rowid = f.rowid
        WHERE entries_fts MATCH 'Melina'
        ORDER BY rank
        LIMIT 5
    """)
    for row in cur.fetchall():
        print(f"  [{row[1]}] {row[2][:80]}")

    print("\n  FTS search: 'Erdtree'")
    cur.execute("""
        SELECT COUNT(*) FROM entries_fts WHERE entries_fts MATCH 'Erdtree'
    """)
    print(f"  {cur.fetchone()[0]} hits")

    conn.close()


if __name__ == "__main__":
    run()
