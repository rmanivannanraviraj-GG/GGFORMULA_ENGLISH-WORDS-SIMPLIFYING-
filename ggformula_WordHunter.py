# app_streamlit_suffix_full_ui.py
"""
Streamlit web-app version of the Suffix Search tool.
This preserves core logic from your Tkinter app (load_wordlist, search by suffix,
get WordNet meanings, translate via GoogleTranslator if available, append words,
export meanings to Excel) and provides a simple, child-friendly web UI.

Features:
- Load default wordlist file or use WordNet lemma names if none found
- Upload your own wordlist file (one word per line)
- Search by suffix, optional exact "letters before suffix" count
- Highlight suffix in the results list (big font, kid-friendly)
- Select a word to view WordNet meanings and Tamil translations
- Export meanings to Excel (download button)
- Add a new word (appends to the chosen wordlist file)

Run: `streamlit run app_streamlit_suffix_full_ui.py`

Dependencies: streamlit, pandas, nltk, deep_translator (optional), xlsxwriter

"""

import streamlit as st
import pandas as pd
import textwrap
import os
from pathlib import Path
from io import BytesIO

# optional translator
try:
    from deep_translator import GoogleTranslator
except Exception:
    GoogleTranslator = None

# NLTK / WordNet
import nltk
from nltk.corpus import wordnet

# Ensure NLTK wordnet available (download only if necessary)
try:
    nltk.data.find("corpora/wordnet")
except Exception:
    with st.spinner("Preparing NLTK WordNet (one-time)..."):
        nltk.download('wordnet')
        nltk.download('omw-1.4')

# ---------- Config ----------
st.set_page_config(page_title="Suffix Learner — Web", layout="wide")

DEFAULT_WORDLIST_PATH = Path("data/wordlist.txt")
WRAP_EN = 80
WRAP_TA = 100
POS_MAP = {'n': 'Noun', 'v': 'Verb', 'a': 'Adjective', 's': 'Adjective Satellite', 'r': 'Adverb'}

# Create data dir
DEFAULT_WORDLIST_PATH.parent.mkdir(parents=True, exist_ok=True)

# ---------- Helpers ----------
@st.cache_data(show_spinner=False)
def load_wordlist(path: str | Path):
    """Load words from path if exists; otherwise fall back to WordNet lemmas."""
    p = Path(path)
    if p.exists():
        try:
            text = p.read_text(encoding='utf-8')
            words = [w.strip() for w in text.split() if w.strip()]
            # unique, keep case, sort by length then lexicographically
            words = sorted(set(words), key=lambda x: (len(x), x.lower()))
            return words
        except Exception as e:
            st.error(f"Failed reading wordlist file: {e}")
    # fallback: use WordNet lemmas
    lemmas = sorted(set(wordnet.all_lemma_names()), key=lambda x: (len(x), x.lower()))
    return lemmas

@st.cache_data
def translate_to_tamil(text: str):
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
        f.write('\n' + word.strip())


def get_wordnet_meanings_for_table(word: str):
    syns = wordnet.synsets(word)
    rows = []
    if not syns:
        return rows
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
        if suf and w.lower().endswith(suf):
            if before_letters is None or before_letters == 0:
                matched.append(w)
            else:
                if len(w) - len(suf) == before_letters:
                    matched.append(w)
        elif not suf:
            matched.append(w)
    matched.sort(key=len)
    return matched


def make_highlight_html(word, suf):
    if suf and word.lower().endswith(suf.lower()):
        p = word[:-len(suf)]
        s = word[-len(suf):]
        return f"<div style='font-size:20px; padding:6px;'><span>{p}</span><span style='color:#d32f2f; font-weight:700'>{s}</span></div>"
    else:
        return f"<div style='font-size:20px; padding:6px;'>{word}</div>"


def df_to_excel_bytes(df: pd.DataFrame, sheet_name: str = "Meanings") -> bytes:
    towrite = BytesIO()
    with pd.ExcelWriter(towrite, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
        workbook = writer.book
        worksheet = writer.sheets[sheet_name]
        header_fmt = workbook.add_format({"bold": True, "bg_color": "#FFD700"})
        wrap_fmt = workbook.add_format({"text_wrap": True})
        for cnum, col in enumerate(df.columns):
            worksheet.write(0, cnum, col, header_fmt)
            if col.lower().startswith('english'):
                worksheet.set_column(cnum, cnum, 60, wrap_fmt)
            elif col.lower().startswith('tamil'):
                worksheet.set_column(cnum, cnum, 80, wrap_fmt)
            else:
                worksheet.set_column(cnum, cnum, 20, wrap_fmt)
    return towrite.getvalue()

# ---------- UI Styling (kid-friendly) ----------
st.markdown("""
<style>
.header {background: linear-gradient(90deg,#ffecd2,#fcb69f); padding: 12px; border-radius: 10px;}
.kid-box {background:#fffef6; border-radius:10px; padding:10px; box-shadow: 0 3px 8px rgba(0,0,0,0.06);}
.word-list {background:#ffffff; border-radius:8px; padding:6px;}
.small-muted {color:#666; font-size:13px}
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='header'><h1 style='margin:0'>🎈 Suffix Learner — Web</h1><div class='small-muted'>Easy, big UI for kids — search by suffix, view meanings & Tamil translations</div></div>", unsafe_allow_html=True)
st.write("")

# ---------- Sidebar: settings and wordlist management ----------
with st.sidebar:
    st.header("🔧 Settings")
    before_letters = st.number_input("Letters before suffix (exact). 0 = any", min_value=0, value=0)
    st.markdown("---")
    st.header("Wordlist source")
    st.text("Default file:")
    st.code(str(DEFAULT_WORDLIST_PATH))
    uploaded = st.file_uploader("Upload a wordlist file (one word per line)", type=["txt"], help="If you upload, the app will use this list for the session")
    use_default_button = st.button("Use default wordlist file (save/addable)")
    st.markdown("---")
    st.header("➕ Add a new word")
    new_word = st.text_input("Add word (single token)")
    add_target = st.selectbox("Save to:", ["Default file (data/wordlist.txt)", "Don't save (session only)"])
    if st.button("Add word"):
        w = (new_word or "").strip()
        if not w:
            st.warning("Enter a non-empty word to add")
        else:
            if add_target.startswith("Default"):
                try:
                    append_word_to_file(DEFAULT_WORDLIST_PATH, w)
                    st.success(f"Added '{w}' to {DEFAULT_WORDLIST_PATH}")
                except Exception as e:
                    st.error(f"Failed to write: {e}")
            else:
                st.success(f"'{w}' added to session (will not persist).")
                if 'session_words' not in st.session_state:
                    st.session_state['session_words'] = set()
                st.session_state['session_words'].add(w)

# ---------- Load words ----------
if uploaded is not None:
    # read uploaded file into memory and use it
    try:
        content = uploaded.read().decode('utf-8')
        session_words = [w.strip() for w in content.split() if w.strip()]
        words = sorted(set(session_words), key=lambda x: (len(x), x.lower()))
        st.info(f"Loaded uploaded wordlist: {len(words)} words (session only)")
    except Exception as e:
        st.error(f"Failed reading uploaded file: {e}")
        words = load_wordlist(DEFAULT_WORDLIST_PATH)
else:
    words = load_wordlist(DEFAULT_WORDLIST_PATH)

# include session only words
if 'session_words' in st.session_state:
    words = sorted(set(list(words) + list(st.session_state['session_words'])), key=lambda x: (len(x), x.lower()))

# ---------- Main layout ----------
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("🔎 Search")
    suffix_input = st.text_input("Suffix (e.g., 'ing', 'ight')", value="")
    exact_before = int(before_letters) if before_letters >= 0 else 0
    btn_search = st.button("Search (with before-count)")
    btn_show_all = st.button("Show all related words")

    if btn_search:
        matched = find_matches(words, suffix_input, exact_before)
        st.session_state['last_matches'] = matched
    elif btn_show_all:
        matched = find_matches(words, suffix_input, None)
        st.session_state['last_matches'] = matched
    else:
        matched = st.session_state.get('last_matches', [])

    st.markdown(f"**Matched:** {len(matched)}    (Total words in list: {len(words)})")
    st.markdown("<div style='max-height:520px; overflow:auto; padding:6px; background:#fffef6; border-radius:8px;'>", unsafe_allow_html=True)
    # show top 2000 to keep UI responsive
    for w in matched[:2000]:
        st.markdown(make_highlight_html(w, suffix_input), unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.subheader("📘 Meanings & Translations")
    chosen = st.selectbox("Quick pick (choose a word to load meanings)", [""] + (st.session_state.get('last_matches') or [])[:1000])

    if chosen:
        st.markdown(f"### 🔤 {chosen}")
        syns = get_wordnet_meanings_for_table(chosen)
        if not syns:
            st.info("No WordNet meanings found for this word.")
        else:
            df = pd.DataFrame(syns)
            # display table
            st.dataframe(df.style.set_properties(**{'white-space': 'pre-wrap'}), height=420)
            # prepare excel download
            excel_bytes = df_to_excel_bytes(df)
            st.download_button(label="📥 Download Meanings as Excel", data=excel_bytes, file_name=f"{chosen}_meanings.xlsx", mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    # Export all matched words' meanings if any
    if st.session_state.get('last_matches'):
        if st.button("Export meanings for ALL matched words (first sense each)"):
            progress = st.progress(0)
            rows = []
            m = st.session_state['last_matches']
            total = min(len(m), 500)  # limit to 500 to avoid timeouts
            for i, w in enumerate(m[:total], start=1):
                syns = get_wordnet_meanings_for_table(w)
                if syns:
                    first = syns[0]
                    rows.append({"Word": w, "No": first['No'], "POS": first['POS'], "English": first['English'], "Tamil": first['Tamil']})
                else:
                    rows.append({"Word": w, "No": "", "POS": "", "English": "", "Tamil": ""})
                progress.progress(int(i / total * 100))
            df_all = pd.DataFrame(rows)
            excel_bytes = df_to_excel_bytes(df_all, sheet_name='AllMatched')
            st.download_button("📥 Download All Matched Meanings", data=excel_bytes, file_name="matched_meanings.xlsx", mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

# Footer tips
st.markdown("<div style='margin-top:12px; color:#555'>Tip: Use short suffixes (like 'ight') and the exact letters-before-suffix to narrow down results. Upload a custom wordlist or add words from the sidebar.</div>", unsafe_allow_html=True)

# End
