"""
Parse Elden Ring NPC dialogue and cutscene subtitles from HTML FMG dumps.

Input:
  data/raw/fromsoft_fts/elden_ring_base.html  (1.8 MB)
  data/raw/fromsoft_fts/elden_ring_sote.html  (387 KB)

Output:
  data/processed/dialogue_entries.json

Schema per entry:
  {
    "id":          str,   e.g. "base_talk_20580200"
    "category":    "dialogue" | "cutscene"
    "source_name": str,   NPC name if identified, else "NPC_<group>"
    "text_en":     str,
    "text_ko":     "",
    "location":    "",
    "game":        "base" | "sote"
  }

Usage:
    python scripts/parse_html.py
"""

import re
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent.parent
HTML_DIR = ROOT / "data" / "raw" / "fromsoft_fts"
OUT_DIR = ROOT / "data" / "processed"
OUT_DIR.mkdir(parents=True, exist_ok=True)

HTML_SOURCES = [
    ("elden_ring_base.html", "base"),
    ("elden_ring_sote.html", "sote"),
]

# Lines to skip — generic filler with no lore value
SKIP_PATTERNS = re.compile(
    r"^(\.{1,3}|!+|\?+|<[^>]+>|\s*)$"
    r"|^(hmm+|hm+|ha+|ah+|oh+|ugh|ngh)[\.,!]*$",
    re.IGNORECASE,
)


def load_html(path: Path) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def get_section(content: str, fmg_name: str) -> str | None:
    """Try exact name first, then _dlc01/_dlc02 variants (SOTE HTML uses suffixes)."""
    for variant in [fmg_name, fmg_name.replace(".fmg", "_dlc01.fmg"), fmg_name.replace(".fmg", "_dlc02.fmg")]:
        m = re.search(
            rf"<h2[^>]*>\s*{re.escape(variant)}\s*</h2>(.*?)(?=<h2|$)",
            content,
            re.DOTALL,
        )
        if m:
            return m.group(1)
    return None


def get_all_sections(content: str, fmg_name: str) -> list[str]:
    """Get all matching sections (e.g. both _dlc01 and _dlc02 for SOTE)."""
    base = fmg_name.replace(".fmg", "")
    pattern = re.compile(
        rf"<h2[^>]*>\s*{re.escape(base)}(?:_dlc\d+)?\.fmg\s*</h2>(.*?)(?=<h2|$)",
        re.DOTALL,
    )
    return [m.group(1) for m in pattern.finditer(content)]


def extract_lines(raw_section: str) -> list[tuple[str, str]]:
    """Return [(text_id, text)] from a section, with <br> as line separator."""
    clean = re.sub(r"<br\s*/?>", "\n", raw_section)
    clean = re.sub(r"<[^>]+>", "", clean)
    pairs = re.findall(r"\[(\d+)\]\s*([^\[\n]{2,})", clean)
    result = []
    for id_, text in pairs:
        text = text.strip()
        if not SKIP_PATTERNS.match(text):
            result.append((id_, text))
    return result


def build_npc_name_map(content: str) -> dict[str, str]:
    """Build {npc_id_str: name} from NpcName.fmg (handles _dlc01/_dlc02 variants)."""
    npc_map: dict[str, str] = {}
    for section in get_all_sections(content, "NpcName.fmg"):
        for id_, name in extract_lines(section):
            npc_map[id_] = name.strip()
    return npc_map


def build_speaker_hints(npc_map: dict[str, str]) -> list[tuple[re.Pattern, str]]:
    """Build regex patterns to detect speaker from dialogue text."""
    hints = []
    for name in sorted(npc_map.values(), key=len, reverse=True):
        # match "I am Melina", "I'm Melina", "This is Melina", "...Melina..."
        pattern = re.compile(
            rf"\bI(?:'m| am| am\.\.\.)?\s+{re.escape(name)}\b"
            rf"|^{re.escape(name)}[,\.:]",
            re.IGNORECASE,
        )
        hints.append((pattern, name))
    return hints


def identify_speaker(text: str, hints: list[tuple[re.Pattern, str]]) -> str | None:
    for pattern, name in hints:
        if pattern.search(text):
            return name
    return None


def parse_talkmsg(content: str, game: str, npc_map: dict[str, str]) -> list[dict]:
    sections = get_all_sections(content, "TalkMsg.fmg")
    if not sections:
        print(f"  [WARN] TalkMsg.fmg not found for game={game}")
        return []

    hints = build_speaker_hints(npc_map)
    entries: list[dict] = []
    seen_ids: set[str] = set()

    for section in sections:
        # Split by h3 groups (each group = one NPC talk script cluster)
        group_blocks = re.split(r"<h3[^>]*>", section)[1:]
        group_ids = re.findall(r"<h3[^>]*>\s*(\S+)\s*</h3>", section)

        for group_id, block in zip(group_ids, group_blocks):
            lines = extract_lines(block)
            if not lines:
                continue

            # Try to identify speaker from any line in this group
            group_speaker: str | None = None
            for _, text in lines:
                speaker = identify_speaker(text, hints)
                if speaker:
                    group_speaker = speaker
                    break

            source_name = group_speaker or f"NPC_{group_id}"

            for text_id, text in lines:
                entry_id = f"{game}_talk_{text_id}"
                if entry_id in seen_ids:
                    continue
                seen_ids.add(entry_id)
                entries.append({
                    "id": entry_id,
                    "category": "dialogue",
                    "source_name": source_name,
                    "text_en": text,
                    "text_ko": "",
                    "location": "",
                    "game": game,
                })

    return entries


def parse_movie_subtitles(content: str, game: str) -> list[dict]:
    entries = []
    seen: set[str] = set()
    for section in get_all_sections(content, "MovieSubtitle.fmg"):
        for text_id, text in extract_lines(section):
            eid = f"{game}_subtitle_{text_id}"
            if eid not in seen:
                seen.add(eid)
                entries.append({
                    "id": eid,
                    "category": "cutscene",
                    "source_name": "Cutscene",
                    "text_en": text,
                    "text_ko": "",
                    "location": "",
                    "game": game,
                })
    return entries


def parse_event_text(content: str, game: str) -> list[dict]:
    """EventTextForMap — location/event prompts with lore value (skip short UI labels)."""
    entries = []
    seen: set[str] = set()
    for section in get_all_sections(content, "EventTextForMap.fmg"):
        for text_id, text in extract_lines(section):
            if len(text) < 30:
                continue
            eid = f"{game}_event_{text_id}"
            if eid not in seen:
                seen.add(eid)
                entries.append({
                    "id": eid,
                    "category": "event",
                    "source_name": "In-World Text",
                    "text_en": text,
                    "text_ko": "",
                    "location": "",
                    "game": game,
                })
    return entries


def run():
    all_entries: list[dict] = []

    for filename, game in HTML_SOURCES:
        path = HTML_DIR / filename
        if not path.exists():
            print(f"  [SKIP] {filename} not found — run fetch_erdb.py first")
            continue

        print(f"Parsing {filename} ({game})...")
        content = load_html(path)

        npc_map = build_npc_name_map(content)
        print(f"  NpcName: {len(npc_map)} NPCs loaded")

        talk = parse_talkmsg(content, game, npc_map)
        subs = parse_movie_subtitles(content, game)
        events = parse_event_text(content, game)

        # Count identified vs unknown speakers in dialogue
        identified = sum(1 for e in talk if not e["source_name"].startswith("NPC_"))
        print(f"  TalkMsg:       {len(talk):>5} lines  ({identified} with identified speaker)")
        print(f"  MovieSubtitle: {len(subs):>5} lines")
        print(f"  EventTextForMap: {len(events):>4} lines (lore-worthy)")
        print()

        all_entries.extend(talk + subs + events)

    out_path = OUT_DIR / "dialogue_entries.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_entries, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(all_entries)} dialogue/event entries -> {out_path}")


if __name__ == "__main__":
    run()
