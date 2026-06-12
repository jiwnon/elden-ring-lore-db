"""
Elden Ring Lore DB — Streamlit chatbot
Search in-game text and generate lore reasoning via Ollama (llama3.1).

Run:
    streamlit run app/app.py
"""

import sqlite3
import json
import urllib.request
import urllib.error
from pathlib import Path

import streamlit as st

DB_PATH = Path(__file__).parent.parent / "data" / "lore.db"
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.1"

MAX_RESULTS = 15       # max FTS rows returned
MAX_CONTEXT_CHARS = 6000  # max chars sent to Ollama

st.set_page_config(
    page_title="Elden Ring Lore DB",
    page_icon="🌳",
    layout="wide",
)

# ── Styles ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.official-box {
    background: #1a1a2e;
    border-left: 4px solid #c9a84c;
    padding: 12px 16px;
    border-radius: 4px;
    margin-bottom: 8px;
    font-size: 0.9rem;
    color: #e0d5b7;
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
    font-size: 0.75rem;
    color: #888;
    margin-bottom: 4px;
}
.result-count {
    color: #888;
    font-size: 0.8rem;
}
</style>
""", unsafe_allow_html=True)


# ── DB helpers ───────────────────────────────────────────────────────────────
@st.cache_resource
def get_conn():
    if not DB_PATH.exists():
        st.error(f"DB not found: {DB_PATH}\nRun `python scripts/build_db.py` first.")
        st.stop()
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def search(query: str, category_filter: list[str], limit: int = MAX_RESULTS) -> list[sqlite3.Row]:
    conn = get_conn()
    # Sanitize query for FTS5: wrap multi-word in quotes
    fts_query = f'"{query}"' if " " in query else query
    cat_clause = ""
    params: list = [fts_query]
    if category_filter:
        placeholders = ",".join("?" * len(category_filter))
        cat_clause = f"AND e.category IN ({placeholders})"
        params.extend(category_filter)
    params.append(limit)

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
        return conn.execute(sql, params).fetchall()
    except sqlite3.OperationalError:
        # FTS5 query syntax error — fall back to LIKE
        like = f"%{query}%"
        params_like: list = [like, like]
        cat_clause2 = ""
        if category_filter:
            placeholders = ",".join("?" * len(category_filter))
            cat_clause2 = f"AND category IN ({placeholders})"
            params_like.extend(category_filter)
        params_like.append(limit)
        sql2 = f"""
            SELECT id, category, source_name, text_en, game
            FROM entries
            WHERE (text_en LIKE ? OR source_name LIKE ?)
            {cat_clause2}
            LIMIT ?
        """
        return conn.execute(sql2, params_like).fetchall()


# ── Ollama ───────────────────────────────────────────────────────────────────
def ollama_available() -> bool:
    try:
        urllib.request.urlopen("http://localhost:11434", timeout=2)
        return True
    except Exception:
        return False


def build_prompt(query: str, rows: list[sqlite3.Row]) -> str:
    context_parts = []
    total = 0
    for row in rows:
        snippet = f"[{row['category'].upper()} | {row['source_name']}]\n{row['text_en']}"
        if total + len(snippet) > MAX_CONTEXT_CHARS:
            break
        context_parts.append(snippet)
        total += len(snippet)

    context = "\n\n---\n\n".join(context_parts)
    return f"""You are a lore scholar of Elden Ring.
Your job is to answer lore questions using ONLY the official in-game texts provided below.
Do NOT invent details not present in the texts. If texts are insufficient, say so.
Keep your answer focused and cite which text you're drawing from when possible.

=== OFFICIAL IN-GAME TEXTS ===
{context}

=== QUESTION ===
{query}

=== YOUR ANSWER ==="""


def ask_ollama(prompt: str) -> str:
    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.3, "num_predict": 800},
    }).encode()

    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read())
    return result.get("response", "").strip()


# ── UI ───────────────────────────────────────────────────────────────────────
st.title("🌳 Elden Ring Lore DB")
st.caption("Official in-game text only · Powered by Ollama llama3.1")

col_search, col_opts = st.columns([3, 1])

with col_search:
    query = st.text_input(
        "검색어 / Query",
        placeholder='예: Melina, Erdtree, Ranni, "Fingers of the Rot"',
        label_visibility="collapsed",
    )

with col_opts:
    category_filter = st.multiselect(
        "Category",
        options=["dialogue", "item", "skill", "spell", "cutscene", "event"],
        default=[],
        placeholder="All categories",
        label_visibility="collapsed",
    )

use_ollama = st.toggle("🤖 Ollama 추론 생성", value=True)

if query:
    rows = search(query, category_filter)

    col_left, col_right = st.columns([1, 1])

    # ── [오피셜] Official texts ─────────────────────────────────────────────
    with col_left:
        st.subheader("📜 오피셜 원문")
        if not rows:
            st.info("검색 결과 없음")
        else:
            st.markdown(f'<p class="result-count">{len(rows)}건 조회됨</p>', unsafe_allow_html=True)
            for row in rows:
                game_label = "🌿 Base" if row["game"] == "base" else "🌑 SOTE"
                cat_emoji = {
                    "dialogue": "💬", "item": "📦", "skill": "⚔️",
                    "spell": "✨", "cutscene": "🎬", "event": "🗺️",
                }.get(row["category"], "📄")
                st.markdown(
                    f'<p class="source-tag">{cat_emoji} {row["category"]} · '
                    f'{row["source_name"]} · {game_label}</p>'
                    f'<div class="official-box">{row["text_en"]}</div>',
                    unsafe_allow_html=True,
                )

    # ── [추론] Ollama inference ─────────────────────────────────────────────
    with col_right:
        st.subheader("🔮 로어 추론 (Ollama)")
        if not use_ollama:
            st.info("Ollama 추론이 꺼져 있습니다.")
        elif not rows:
            st.info("검색 결과가 없어 추론할 수 없습니다.")
        elif not ollama_available():
            st.warning(
                "Ollama가 실행 중이지 않습니다.\n\n"
                "터미널에서 `ollama serve` 를 먼저 실행하세요.\n"
                f"모델: `ollama pull {OLLAMA_MODEL}`"
            )
        else:
            with st.spinner(f"{OLLAMA_MODEL} 추론 중..."):
                try:
                    prompt = build_prompt(query, rows)
                    answer = ask_ollama(prompt)
                    st.markdown(
                        f'<div class="inference-box">{answer}</div>',
                        unsafe_allow_html=True,
                    )
                except Exception as e:
                    st.error(f"Ollama 오류: {e}")
