"""
Elden Ring Lore DB — Streamlit chatbot
Search in-game text and generate lore reasoning via Ollama (llama3.1).

Run:
    streamlit run app/app.py
"""

import sqlite3
import json
import sys
import urllib.request
import urllib.error
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))
from character_aliases import get_aliases

DB_PATH = Path(__file__).parent.parent / "data" / "lore.db"
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.1"

MAX_FTS_RESULTS = 20
MAX_CONTEXT_CHARS = 6000

st.set_page_config(
    page_title="Elden Ring Lore DB",
    page_icon="🌳",
    layout="wide",
)

st.markdown("""
<style>
.official-box {
    background: #1a1a2e;
    border-left: 4px solid #c9a84c;
    padding: 10px 14px;
    border-radius: 4px;
    margin-bottom: 6px;
    font-size: 0.88rem;
    color: #e0d5b7;
    line-height: 1.55;
}
.inference-box {
    background: #16213e;
    border-left: 4px solid #4a90e2;
    padding: 14px 16px;
    border-radius: 4px;
    color: #d0e0ff;
    font-size: 0.95rem;
    line-height: 1.7;
}
.source-tag {
    font-size: 0.72rem;
    color: #888;
    margin-bottom: 2px;
}
.char-header {
    font-size: 1.6rem;
    font-weight: bold;
    color: #c9a84c;
    margin-bottom: 0;
}
.stat-chip {
    display: inline-block;
    background: #2a2a3e;
    border-radius: 12px;
    padding: 2px 10px;
    font-size: 0.78rem;
    color: #aaa;
    margin-right: 6px;
    margin-bottom: 8px;
}
</style>
""", unsafe_allow_html=True)


# ── DB ───────────────────────────────────────────────────────────────────────
@st.cache_resource
def get_conn():
    if not DB_PATH.exists():
        st.error(f"DB not found: {DB_PATH}\nRun build_db.py first.")
        st.stop()
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def fts_search(terms: list[str], category_filter: list[str], limit: int) -> list[sqlite3.Row]:
    """FTS5 search over multiple terms (OR logic)."""
    conn = get_conn()
    # Build FTS query: "term1" OR "term2" OR ...
    fts_q = " OR ".join(f'"{t}"' for t in terms)
    cat_clause, cat_params = "", []
    if category_filter:
        ph = ",".join("?" * len(category_filter))
        cat_clause = f"AND e.category IN ({ph})"
        cat_params = category_filter

    sql = f"""
        SELECT e.id, e.category, e.source_name, e.text_en, e.game
        FROM entries_fts f
        JOIN entries e ON e.rowid = f.rowid
        WHERE entries_fts MATCH ?
        {cat_clause}
        ORDER BY rank
        LIMIT ?
    """
    try:
        return conn.execute(sql, [fts_q] + cat_params + [limit]).fetchall()
    except sqlite3.OperationalError:
        like = f"%{terms[0]}%"
        sql2 = f"""
            SELECT id, category, source_name, text_en, game FROM entries
            WHERE (text_en LIKE ? OR source_name LIKE ?)
            {cat_clause}
            LIMIT ?
        """
        return conn.execute(sql2, [like, like] + cat_params + [limit]).fetchall()


def get_character_dialogue(name: str) -> list[sqlite3.Row]:
    """All dialogue lines where source_name matches the character."""
    conn = get_conn()
    return conn.execute(
        "SELECT id, category, source_name, text_en, game FROM entries "
        "WHERE source_name = ? AND category = 'dialogue' "
        "ORDER BY game, id",
        (name,)
    ).fetchall()


def get_character_mentions(name: str, aliases: list[str], limit: int = 50) -> list[sqlite3.Row]:
    """FTS search for character name + aliases across non-dialogue entries."""
    conn = get_conn()
    all_terms = [name] + aliases
    fts_q = " OR ".join(f'"{t}"' for t in all_terms)
    try:
        return conn.execute(
            "SELECT e.id, e.category, e.source_name, e.text_en, e.game "
            "FROM entries_fts f JOIN entries e ON e.rowid = f.rowid "
            "WHERE entries_fts MATCH ? AND e.category != 'dialogue' "
            "ORDER BY rank LIMIT ?",
            (fts_q, limit)
        ).fetchall()
    except sqlite3.OperationalError:
        return []


def get_character_other_dialogue(name: str, aliases: list[str], limit: int = 60) -> list[sqlite3.Row]:
    """Other NPCs' dialogue that mentions this character."""
    conn = get_conn()
    all_terms = [name] + aliases
    fts_q = " OR ".join(f'"{t}"' for t in all_terms)
    try:
        return conn.execute(
            "SELECT e.id, e.category, e.source_name, e.text_en, e.game "
            "FROM entries_fts f JOIN entries e ON e.rowid = f.rowid "
            "WHERE entries_fts MATCH ? AND e.category = 'dialogue' AND e.source_name != ? "
            "ORDER BY rank LIMIT ?",
            (fts_q, name, limit)
        ).fetchall()
    except sqlite3.OperationalError:
        return []


# ── Ollama ────────────────────────────────────────────────────────────────────
def ollama_available() -> bool:
    try:
        urllib.request.urlopen("http://localhost:11434", timeout=2)
        return True
    except Exception:
        return False


def ask_ollama(prompt: str) -> str:
    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.3, "num_predict": 1000},
    }).encode()
    req = urllib.request.Request(
        OLLAMA_URL, data=payload,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read()).get("response", "").strip()


def build_summary_prompt(name: str, dialogue: list, mentions: list, others: list) -> str:
    parts = []
    total = 0

    def add(label, rows):
        nonlocal total
        for r in rows:
            s = f"[{label} | {r['source_name']}]\n{r['text_en']}"
            if total + len(s) > MAX_CONTEXT_CHARS:
                return
            parts.append(s)
            total += len(s)

    add("SELF DIALOGUE", dialogue)
    add("LORE / ITEM", mentions)
    add("OTHER NPC", others)

    context = "\n\n---\n\n".join(parts)
    return f"""You are an Elden Ring lore scholar. Using ONLY the official in-game texts below, write a comprehensive lore summary of {name}.
Structure your answer as:
1. Who is {name}? (identity, role, origin)
2. Key events and actions
3. Relationships with other characters
4. Mysteries or unresolved lore points

Do NOT invent anything not in the texts. If information is absent, say so.

=== OFFICIAL TEXTS ===
{context}

=== LORE SUMMARY OF {name.upper()} ==="""


def build_search_prompt(query: str, rows: list) -> str:
    parts, total = [], 0
    for r in rows:
        s = f"[{r['category'].upper()} | {r['source_name']}]\n{r['text_en']}"
        if total + len(s) > MAX_CONTEXT_CHARS:
            break
        parts.append(s)
        total += len(s)
    context = "\n\n---\n\n".join(parts)
    return f"""You are an Elden Ring lore scholar. Answer using ONLY the official in-game texts below.

=== OFFICIAL IN-GAME TEXTS ===
{context}

=== QUESTION ===
{query}

=== ANSWER ==="""


# ── Render helpers ─────────────────────────────────────────────────────────────
CAT_EMOJI = {
    "dialogue": "💬", "item": "📦", "skill": "⚔️",
    "spell": "✨", "cutscene": "🎬", "event": "🗺️",
}
GAME_LABEL = {"base": "🌿 Base", "sote": "🌑 SOTE"}


def render_row(row, show_speaker: bool = True):
    cat_e = CAT_EMOJI.get(row["category"], "📄")
    game_l = GAME_LABEL.get(row["game"], row["game"])
    speaker = f" · {row['source_name']}" if show_speaker else ""
    st.markdown(
        f'<p class="source-tag">{cat_e} {row["category"]}{speaker} · {game_l}</p>'
        f'<div class="official-box">{row["text_en"]}</div>',
        unsafe_allow_html=True,
    )


# ── Main UI ───────────────────────────────────────────────────────────────────
st.title("🌳 Elden Ring Lore DB")
st.caption("Official in-game text only · Powered by Ollama llama3.1")

col_search, col_opts = st.columns([3, 1])
with col_search:
    query = st.text_input(
        "Query", placeholder='예: Melina, Ranni, Elden Lord, "Frenzied Flame"',
        label_visibility="collapsed",
    )
with col_opts:
    category_filter = st.multiselect(
        "Category",
        options=["dialogue", "item", "skill", "spell", "cutscene", "event"],
        default=[], placeholder="All", label_visibility="collapsed",
    )

use_ollama = st.toggle("🤖 Ollama 추론 생성", value=True)

if not query:
    st.stop()

# ── Detect Character Mode ──────────────────────────────────────────────────────
char_info = get_aliases(query)

# ════════════════════════════════════════════════════════════
# CHARACTER MODE
# ════════════════════════════════════════════════════════════
if char_info:
    char_name, aliases = char_info
    dialogue = get_character_dialogue(char_name)
    mentions = get_character_mentions(char_name, aliases)
    others   = get_character_other_dialogue(char_name, aliases)

    st.markdown(f'<p class="char-header">⚔ {char_name}</p>', unsafe_allow_html=True)
    st.markdown(
        f'<span class="stat-chip">💬 본인 대사 {len(dialogue)}건</span>'
        f'<span class="stat-chip">📦 아이템/이벤트 언급 {len(mentions)}건</span>'
        f'<span class="stat-chip">🗣 타 NPC 언급 {len(others)}건</span>',
        unsafe_allow_html=True,
    )
    st.divider()

    tab1, tab2, tab3, tab4 = st.tabs([
        f"💬 본인 대사 ({len(dialogue)})",
        f"📦 아이템 · 이벤트 ({len(mentions)})",
        f"🗣 타 NPC 언급 ({len(others)})",
        "🔮 Ollama 종합 요약",
    ])

    with tab1:
        if not dialogue:
            st.info("본인 대사 데이터 없음")
        else:
            base_d = [r for r in dialogue if r["game"] == "base"]
            sote_d = [r for r in dialogue if r["game"] == "sote"]
            if base_d:
                st.markdown("**🌿 Base Game**")
                for row in base_d:
                    render_row(row, show_speaker=False)
            if sote_d:
                st.markdown("**🌑 Shadow of the Erdtree**")
                for row in sote_d:
                    render_row(row, show_speaker=False)

    with tab2:
        if not mentions:
            st.info("관련 아이템/이벤트 텍스트 없음")
        for row in mentions:
            render_row(row)

    with tab3:
        if not others:
            st.info("타 NPC 언급 없음")
        for row in others:
            render_row(row)

    with tab4:
        if not use_ollama:
            st.info("Ollama 토글을 켜세요.")
        elif not ollama_available():
            st.warning(
                "Ollama가 실행 중이지 않습니다.\n\n"
                f"`ollama serve` 후 `ollama pull {OLLAMA_MODEL}`"
            )
        else:
            with st.spinner(f"{OLLAMA_MODEL}이 {char_name} 로어를 정리 중..."):
                try:
                    prompt = build_summary_prompt(char_name, dialogue, mentions, others)
                    answer = ask_ollama(prompt)
                    st.markdown(
                        f'<div class="inference-box">{answer}</div>',
                        unsafe_allow_html=True,
                    )
                except Exception as e:
                    st.error(f"Ollama 오류: {e}")

# ════════════════════════════════════════════════════════════
# NORMAL SEARCH MODE
# ════════════════════════════════════════════════════════════
else:
    rows = fts_search([query], category_filter, MAX_FTS_RESULTS)

    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.subheader("📜 오피셜 원문")
        if not rows:
            st.info("검색 결과 없음")
        else:
            st.markdown(f'<p style="color:#888;font-size:.8rem">{len(rows)}건 조회됨</p>', unsafe_allow_html=True)
            for row in rows:
                render_row(row)

    with col_right:
        st.subheader("🔮 로어 추론 (Ollama)")
        if not use_ollama:
            st.info("Ollama 추론이 꺼져 있습니다.")
        elif not rows:
            st.info("검색 결과가 없어 추론할 수 없습니다.")
        elif not ollama_available():
            st.warning(
                "Ollama가 실행 중이지 않습니다.\n\n"
                f"`ollama serve` 후 `ollama pull {OLLAMA_MODEL}`"
            )
        else:
            with st.spinner(f"{OLLAMA_MODEL} 추론 중..."):
                try:
                    answer = ask_ollama(build_search_prompt(query, rows))
                    st.markdown(
                        f'<div class="inference-box">{answer}</div>',
                        unsafe_allow_html=True,
                    )
                except Exception as e:
                    st.error(f"Ollama 오류: {e}")
