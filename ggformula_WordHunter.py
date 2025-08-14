# app_streamlit_suffix_full_ui.py
"""
Streamlit web-app for suffix-based word search + meanings (Tamil translation optional).
— Kids-friendly UI, high contrast, large fonts
— Uses your Tkinter app logic/flow but as a web app

What changed per your asks:
1) "Matched words" என்ற heading / count காட்டப்படாது — கிடைக்கும் வார்த்தைகள் மட்டும்.
2) வார்த்தைகள் தெளிவாகப் பார்க்க scrollable, பெரிய font, high-contrast highlight.
3) Mobile/responsive CSS; even/odd row background வேறுபாடு.

Run:  streamlit run app_streamlit_suffix_full_ui.py
Install: pip install streamlit pandas nltk xlsxwriter deep-translator
"""

import streamlit as st
import pandas as pd
import textwrap
from pathlib import Path
from io import BytesIO

# Optional translator
try:
    from deep_translator import GoogleTranslator
except Exception:
    GoogleTranslator = None

# NLTK / WordNet
import nltk
from nltk.corpus import wordnet

# Ensure WordNet
try:
    nltk.data.find("corpora/wordnet")
except Exception:
    with st.spinner("Preparing NLTK WordNet (one-time)..."):
        nltk.download('wordnet')
        nltk.download('omw-1.4')

# ---------- Config ----------
st.set_page_config(page_title="Suffix Learner — Web", layout="wide")
DEFAULT_WORDLIST_PATH = Path("data/wordlist.txt")
DEFAULT_WORDLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
WRAP_EN = 80
WRAP_TA = 100
POS_MAP = {'n': 'Noun', 'v': 'Verb', 'a': 'Adjective', 's': 'Adjective Satellite', 'r': 'Adverb'}

# ---------- Helpers ----------
@st.cache_data(show_spinner=False)
def load_wordlist(path: str | Path):
    p = Path(path)
    if p.exists():
        try:
            text = p.read_text(encoding='utf-8')
            words = [w.strip() for w in text.split() if w.strip()]
            return sorted(set(words), key=lambda x: (len(x), x.lower()))
        except Exception as e:
            st.error(f"Failed reading wordlist file: {e}")
    # fallback to WordNet lemmas
    return sorted(set(wordnet.all_lemma_names()), key=lambda x: (len(x), x.lower()))

@st.cache_data(show_spinner=False)
def translate_to_tamil(text: str) -> str:
    if not text:
        return ""
    if GoogleTranslator:
        try:
            return GoogleTranslator(source='auto', target='ta').translate(text)
        except Exception:
            return ""
    return ""

def append_word_to_file(path: Path, word: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a', encoding='utf-8') as f:
        f.write("
" + word.strip())

def get_wordnet_meanings_for_table(word: str):
    syns = wordnet.synsets(word)
    rows = []
    for i, syn in enumerate(syns, start=1):
        pos_full = POS_MAP.get(syn.pos(), syn.pos())
        eng = syn.definition()
        ta = translate_to_tamil(eng)
        rows.append({"No": i, "POS": pos_full, "English": eng, "Tamil": ta})
    return rows

def find_matches(words, suffix: str, before_letters: int | None):
    suf = (suffix or "").strip().lower()
    matched = []
    for w in words:
        if not w:
            continue
        lw = w.lower()
        if suf:
            if lw.endswith(suf):
                if before_letters is None or before_letters == 0:
                    matched.append(w)
                else:
                    if len(w) - len(suf) == before_letters:
                        matched.append(w)
        else:
            matched.append(w)
    matched.sort(key=len)
    return matched

def make_highlight_html(word, suf):
    if suf and word.lower().endswith(suf.lower()):
        p = word[:-len(suf)]
        s = word[-len(suf):]
        return f"<span class='w-prefix'>{p}</span><span class='w-suffix'>{s}</span>"
    return f"<span class='w-prefix'>{word}</span>"

def df_to_excel_bytes(df: pd.DataFrame, sheet_name: str = "Meanings") -> bytes:
    towrite = BytesIO()
    with pd.ExcelWriter(towrite, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
        workbook = writer.book
        ws = writer.sheets[sheet_name]
        head = workbook.add_format({"bold": True, "bg_color": "#FFD700"})
        wrap = workbook.add_format({"text_wrap": True})
        for c, col in enumerate(df.columns):
            ws.write(0, c, col, head)
            if col.lower().startswith('english'):
                ws.set_column(c, c, 60, wrap)
            elif col.lower().startswith('tamil'):
                ws.set_column(c, c, 80, wrap)
            else:
                ws.set_column(c, c, 20, wrap)
    return towrite.getvalue()

# ---------- Styling (kid-friendly + visible) ----------
st.markdown(
    """
    <style>
    .header {background: linear-gradient(90deg,#ffecd2,#fcb69f); padding: 12px; border-radius: 10px;}
    .small-muted {color:#555; font-size:13px}
    .word-scroll {max-height: 560px; overflow:auto; padding: 8px; background:#fffef6; border-radius: 12px; border: 1px solid #f0e6d6;}
    .word-list {list-style:none; margin:0; padding:0}
    .word-item {font-size: 22px; line-height: 1.6; padding: 6px 10px; border-radius:8px;}
    .word-item:nth-child(odd){background:#ffffff}
    .word-item:nth-child(even){background:#f9f9ff}
    .w-suffix {color:#d32f2f; font-weight:800}
    .w-prefix {color:#222; font-weight:600}
    .pick-label {margin-top:8px; font-weight:600}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown("<div class='header'><h1 style='margin:0'>🎈 Suffix Learner — Web</h1><div class='small-muted'>Search by suffix • Meanings & Tamil • Easy for kids</div></div>", unsafe_allow_html=True)

# ---------- Sidebar ----------
with st.sidebar:
    st.header("🔧 Settings")
    before_letters = st.number_input("Letters before suffix (exact). 0 = any", min_value=0, value=0)
    st.markdown("---")
    st.header("Wordlist source")
    st.code(str(DEFAULT_WORDLIST_PATH))
    uploaded = st.file_uploader("Upload a wordlist (.txt, one word per line)", type=["txt"])

# ---------- Load words ----------
if uploaded is not None:
    try:
        content = uploaded.read().decode('utf-8')
        words = [w.strip() for w in content.split() if w.strip()]
        words = sorted(set(words), key=lambda x: (len(x), x.lower()))
        st.info(f"Using uploaded wordlist: {len(words)} words (session)")
    except Exception as e:
        st.error(f"Failed reading uploaded file: {e}")
        words = load_wordlist(DEFAULT_WORDLIST_PATH)
else:
    words = load_wordlist(DEFAULT_WORDLIST_PATH)

if 'session_words' in st.session_state:
    words = sorted(set(list(words) + list(st.session_state['session_words'])), key=lambda x: (len(x), x.lower()))

# ---------- Main layout ----------
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("🔎 Search")
    suffix_input = st.text_input("Suffix (e.g., ing, ight)", value="")
    exact_before = int(before_letters)
    c1, c2 = st.columns(2)
    with c1:
        do_search = st.button("Search (with before-count)")
    with c2:
        show_all  = st.button("Show all related words")

    if do_search:
        matches = find_matches(words, suffix_input, exact_before)
        st.session_state['last_matches'] = matches
    elif show_all:
        matches = find_matches(words, suffix_input, None)
        st.session_state['last_matches'] = matches
    else:
        matches = st.session_state.get('last_matches', [])

    # 🚫 No "Matched: X" text — only the words list (as requested)
    # Visible, scrollable list
    st.markdown("<div class='word-scroll'>", unsafe_allow_html=True)
    st.markdown("<ul class='word-list'>", unsafe_allow_html=True)
    for w in matches[:3000]:  # cap for performance
        st.markdown(f"<li class='word-item'>{make_highlight_html(w, suffix_input)}</li>", unsafe_allow_html=True)
    st.markdown("</ul>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.subheader("📘 Meanings & Translations")
    chosen = st.selectbox("Quick pick — choose a word", [""] + (st.session_state.get('last_matches') or [])[:1000])

    if chosen:
        st.markdown(f"### 🔤 {chosen}")
        rows = get_wordnet_meanings_for_table(chosen)
        if not rows:
            st.info("No WordNet meanings found for this word.")
        else:
            df = pd.DataFrame(rows)
            st.dataframe(
                df.style.set_properties(**{'white-space': 'pre-wrap'}),
                height=420,
                use_container_width=True,
            )
            xbytes = df_to_excel_bytes(df)
            st.download_button("📥 Download Meanings (Excel)", data=xbytes,
                               file_name=f"{chosen}_meanings.xlsx",
                               mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    # Bulk export (first sense only) for current matches
    current = st.session_state.get('last_matches')
    if current:
        if st.button("Export meanings for ALL shown words (first sense)"):
            progress = st.progress(0)
            rows_all = []
            limit = min(len(current), 500)
            for i, w in enumerate(current[:limit], start=1):
                syns = get_wordnet_meanings_for_table(w)
                if syns:
                    first = syns[0]
                    rows_all.append({"Word": w, **first})
                else:
                    rows_all.append({"Word": w, "No": "", "POS": "", "English": "", "Tamil": ""})
                progress.progress(int(i/limit*100))
            df_all = pd.DataFrame(rows_all)
            xbytes = df_to_excel_bytes(df_all, sheet_name='AllShown')
            st.download_button("📥 Download All (Excel)", data=xbytes,
                               file_name="shown_words_meanings.xlsx",
                               mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

# Footer tip
st.markdown("<div class='small-muted' style='margin-top:10px'>Tip: Short suffixes (ex: 'ing', 'ight') + exact letters-before-suffix help you narrow results. Upload your own wordlist.</div>", unsafe_allow_html=True)
