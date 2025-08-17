# app.py
import os
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List, Tuple

import requests
import streamlit as st
import pandas as pd
import nltk
from nltk.corpus import wordnet

# Optional translator
try:
    from deep_translator import GoogleTranslator
    HAS_TRANSLATOR = True
except Exception:
    HAS_TRANSLATOR = False

# ReportLab
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Ensure WordNet resources
try:
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('wordnet')
try:
    nltk.data.find('corpora/omw-1.4')
except LookupError:
    nltk.download('omw-1.4')

# ------------------------ App config + CSS (minimal padding) ------------------------
st.set_page_config(page_title="BRAIN-CHILD • Suffix → Tracer → Dictionary", layout="wide")

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=Nunito+Sans:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', 'Nunito Sans', sans-serif; }
    .header {
        margin: 0 0 8px 0;
        padding: 12px 14px;
        border-radius: 10px;
        color: white;
        background: linear-gradient(90deg,#2575fc,#6a11cb);
        box-shadow: 0 6px 20px rgba(37,117,252,0.08);
    }
    .card {
        background: #fff;
        border-radius: 10px;
        padding: 10px 12px;
        margin-bottom: 12px;
        box-shadow: 0 6px 18px rgba(0,0,0,0.04);
    }
    .small { color:#666; font-size:13px; }
    .muted { color:#777; font-size:12px; }
    /* compact controls */
    .stButton>button { padding:6px 10px; border-radius:8px; }
    .stTextInput>div>div>input, .stNumberInput>div>div>input { padding:6px 8px; }
    .block-container { padding-top: 8px; padding-left:8px; padding-right:8px; padding-bottom:8px; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown("<div class='header'><h2 style='margin:0'>🌟 BRAIN-CHILD DICTIONARY</h2><div class='small'>Suffix Finder • Tracer PDF Generator • Dictionary Explorer</div></div>", unsafe_allow_html=True)


# ------------------------ Utilities ------------------------
DATA_DIR = Path("data"); DATA_DIR.mkdir(exist_ok=True)
POS_MAP = {'n': 'Noun', 'v': 'Verb', 'a': 'Adjective', 's': 'Adjective (Satellite)', 'r': 'Adverb'}

@st.cache_data(show_spinner=False)
def cached_wordnet_lemmas() -> List[str]:
    return sorted(set(wordnet.all_lemma_names()), key=lambda x: (len(x), x.lower()))

def find_synonyms(word: str) -> List[str]:
    s = set()
    for syn in wordnet.synsets(word):
        for lem in syn.lemmas():
            s.add(lem.name().replace('_', ' '))
    return list(s)

# Datamuse online suffix search
def datamuse_suffix_search(suffix: str, max_results: int = 500) -> List[str]:
    q = f"*{suffix}"
    try:
        resp = requests.get("https://api.datamuse.com/words", params={"sp": q, "max": max_results}, timeout=6)
        if resp.status_code == 200:
            data = resp.json()
            return [d['word'] for d in data if 'word' in d]
    except Exception:
        return []
    return []

# Combine WordNet and Datamuse: union, preserve order (datamuse first)
def combined_suffix_search(suffix: str, before_letters: int = 0, datamuse_max: int = 500) -> List[str]:
    suffix = suffix.strip().lower()
    # Datamuse
    dm = datamuse_suffix_search(suffix, max_results=datamuse_max)
    # WordNet lemmas that end with suffix
    wn_lemmas = cached_wordnet_lemmas()
    wn_matches = [w for w in wn_lemmas if w.lower().endswith(suffix)]
    # merge: datamuse results first, then wn unique ones
    seen = set()
    merged = []
    for w in dm + wn_matches:
        wl = w.lower()
        if wl not in seen:
            # apply before_letters filter if required
            if before_letters == 0 or (len(wl) - len(suffix) == before_letters):
                seen.add(wl)
                merged.append(w)
    return merged

# dictionaryapi.dev fallback
def dictapi_defs(word: str, timeout: int = 8):
    try:
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
        r = requests.get(url, timeout=timeout)
        if r.status_code != 200:
            return []
        data = r.json()
        defs = []
        for meaning in data[0].get("meanings", []):
            pos = meaning.get("partOfSpeech", "")
            for d in meaning.get("definitions", []):
                defs.append((pos, d.get("definition", "")))
        # dedupe + cap
        seen = set(); out = []
        for pos, d in defs:
            key = (pos, d.strip())
            if d and key not in seen:
                seen.add(key); out.append((pos, d))
            if len(out) >= 4: break
        return out
    except Exception:
        return []

# Tamil translate helper
def translate_to_tamil(text: str) -> str:
    if not text:
        return ""
    if HAS_TRANSLATOR:
        try:
            return GoogleTranslator(source='auto', target='ta').translate(text)
        except Exception:
            pass
    # fallback to public google translate endpoint
    try:
        res = requests.get("https://translate.googleapis.com/translate_a/single",
                           params={"client": "gtx", "sl": "en", "tl": "ta", "dt": "t", "q": text}, timeout=8)
        if res.status_code == 200:
            return res.json()[0][0][0]
    except Exception:
        pass
    return "(translation unavailable)"

def translate_list_parallel(texts: List[str], max_workers: int = None) -> List[str]:
    if not texts:
        return []
    max_workers = min(max_workers or 6, os.cpu_count() or 2)
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        return list(ex.map(translate_to_tamil, texts))

# Optional dotted handwriting font if present
DO_TTF = os.path.exists("KGPrimaryDots.ttf")
if DO_TTF:
    try:
        pdfmetrics.registerFont(TTFont("Dotted", "KGPrimaryDots.ttf"))
    except Exception:
        DO_TTF = False

# ------------------------ Tracer PDF generator (fixed) ------------------------
def create_tracer_pdf_buffer(words: List[str]) -> BytesIO:
    """
    Fixed settings:
      - 6 words/page (2 cols x 3 rows)
      - 5 clones/word
      - full-width dashed underline
      - dotted font if KGPrimaryDots.ttf exists else Helvetica-Bold
    """
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    page_w, page_h = A4

    left_margin = right_margin = 40
    top_margin = 44
    col_gap = 32
    usable_w = page_w - left_margin - right_margin
    col_w = (usable_w - col_gap) / 2.0
    x_cols = [left_margin, left_margin + col_w + col_gap]

    font_main = "Dotted" if DO_TTF else "Helvetica-Bold"
    font_clone = font_main
    font_size_main = 28
    font_size_clone = 28
    clones_per_word = 5
    line_height = 38
    clone_gap = 10
    block_height = font_size_main + (font_size_clone + clone_gap) * clones_per_word + 62

    y_start_orig = page_h - top_margin
    y_start = y_start_orig
    count_on_page = 0

    for idx, w in enumerate(words):
        if count_on_page == 0 and idx > 0:
            c.showPage()
            y_start = y_start_orig

        col = count_on_page % 2
        if col == 0 and count_on_page > 0:
            y_start -= block_height

        x = x_cols[col]

        c.setFont(font_main, font_size_main)
        c.setFillColor(colors.black)
        c.drawCentredString(x + col_w / 2, y_start, w)

        # clones
        c.setFont(font_clone, font_size_clone)
        c.setFillColor(colors.lightgrey)
        y_clone = y_start - line_height
        for _ in range(clones_per_word):
            c.drawCentredString(x + col_w / 2, y_clone, w)
            underline_y = y_clone - 6
            c.setDash(3, 3)
            c.setStrokeColor(colors.lightgrey)
            c.line(x + 6, underline_y, x + col_w - 6, underline_y)
            c.setDash()
            y_clone -= (font_size_clone + clone_gap)

        count_on_page += 1
        if count_on_page >= 6:
            count_on_page = 0

    c.save()
    buf.seek(0)
    return buf

# ------------------------ UI: Sections (stacked cards) ------------------------
# Suffix Finder Card
st.markdown("<div class='card'><h3 style='margin:4px 0;'>🔎 Suffix Finder (WordNet + Datamuse)</h3>", unsafe_allow_html=True)
with st.container():
    col1, col2, col3 = st.columns([2, 1, 1], gap="small")
    with col1:
        st.write("Enter suffix (e.g. 'ing' or 'ight'):")
        suffix_input = st.text_input("Suffix", value="ing", key="suffix_input")
    with col2:
        before_letters = st.number_input("Letters before suffix (0 = any)", min_value=0, step=1, value=0, key="before_letters")
    with col3:
        include_count = st.number_input("Include top N results", min_value=1, max_value=1000, value=200, step=1, key="include_count")
    run_search = st.button("Find suffix words (online + WordNet)", key="run_suffix_search")
    if run_search:
        with st.spinner("Searching Datamuse + WordNet..."):
            combined = combined_suffix_search(suffix_input, before_letters, datamuse_max= max(500, include_count))
            # cap to include_count
            combined = combined[:include_count]
            st.session_state['combined_matches'] = combined
        st.success(f"Found {len(combined)} words (combined). Showing top {min(len(combined), include_count)}.")
    # show results if exists
    matches = st.session_state.get('combined_matches', [])
    if matches:
        st.write(f"Total matches cached: {len(matches)}")
        st.dataframe(pd.DataFrame(matches[:500], columns=["Word"]), height=300, use_container_width=True)
    else:
        st.info("No matches yet — run the suffix search to fetch online results.")
st.markdown("</div>", unsafe_allow_html=True)

# Tracer PDF Generator Card
st.markdown("<div class='card'><h3 style='margin:4px 0;'>✏️ Tracer PDF Generator (6 words / page)</h3>", unsafe_allow_html=True)
with st.container():
    st.write("Fixed settings: 5 clone rows per word, full-width dashed underline, 6 words/page.")
    # choose source: use session matches or fallback sample
    matches = st.session_state.get('combined_matches', None)
    if matches:
        max_avail = len(matches)
        n_for_pdf = st.number_input("Select how many top matches to include in PDF", min_value=1, max_value=min(480, max_avail), value=min(24, max_avail), step=1, key="n_for_pdf")
        selected_for_pdf = matches[:n_for_pdf]
        st.write(f"Using top {n_for_pdf} words for PDF.")
    else:
        sample = ["apple", "ball", "cat", "dog", "egg", "fish", "goat", "hat", "ice", "jug", "kite", "lion"]
        st.write("No suffix results — using default sample words.")
        selected_for_pdf = sample

    gen_pdf_btn = st.button("Generate & Download Tracing PDF", key="generate_pdf")
    if gen_pdf_btn:
        if not selected_for_pdf:
            st.warning("Nothing selected for PDF.")
        else:
            with st.spinner("Generating PDF..."):
                pdf_buf = create_tracer_pdf_buffer(selected_for_pdf)
            st.download_button("📥 Download Tracing PDF", data=pdf_buf, file_name="tracing_practice.pdf", mime="application/pdf", key="dl_pdf")
            st.success("PDF ready for download.")
st.markdown("</div>", unsafe_allow_html=True)

# Dictionary Explorer Card
st.markdown("<div class='card'><h3 style='margin:4px 0;'>📘 Dictionary Explorer</h3>", unsafe_allow_html=True)
with st.container():
    st.write("Build a meanings table for matches (WordNet → fallback dictionaryapi.dev). English + Tamil columns available.")
    lang_choice = st.selectbox("Show meaning in:", ["English Only", "Tamil Only", "English + Tamil"], index=2, key="dict_lang")
    build_btn = st.button("Build Meanings Table (use matches)", key="build_meanings")
    if build_btn:
        words_source = st.session_state.get('combined_matches', None)
        if not words_source:
            st.info("No matches available — run suffix search first.")
        else:
            # limit to reasonable number
            words_to_process = list(dict.fromkeys(words_source))[:200]  # keep uniqueness and cap
            rows = []
            for w in words_to_process:
                synsets = wordnet.synsets(w)
                if synsets:
                    for syn in synsets[:2]:
                        rows.append({
                            "Word": w,
                            "Word Type": POS_MAP.get(syn.pos(), "Noun"),
                            "English": syn.definition(),
                            "Tamil": "",
                            "Synonyms": ", ".join(find_synonyms(w)[:8]) or "-"
                        })
                else:
                    defs = dictapi_defs(w)
                    if defs:
                        for pos, d in defs[:2]:
                            rows.append({
                                "Word": w,
                                "Word Type": pos or "-",
                                "English": d,
                                "Tamil": "",
                                "Synonyms": ", ".join(find_synonyms(w)[:8]) or "-"
                            })
                    else:
                        rows.append({"Word": w, "Word Type": "-", "English": "-", "Tamil": "-", "Synonyms": "-"})

            df = pd.DataFrame(rows)

            # Tamil translations (parallel) if requested
            if lang_choice != "English Only" and not df.empty:
                eng_list = df["English"].fillna("-").tolist()
                with st.spinner("Translating English definitions to Tamil..."):
                    ta_list = translate_list_parallel(eng_list)
                df["Tamil"] = ta_list

            # Choose view
            if lang_choice == "English Only":
                df_view = df[["Word", "Word Type", "English", "Synonyms"]]
            elif lang_choice == "Tamil Only":
                df_view = df[["Word", "Word Type", "Tamil", "Synonyms"]]
            else:
                df_view = df[["Word", "Word Type", "English", "Tamil", "Synonyms"]]

            st.dataframe(df_view, height=min(700, max(300, len(df_view)*28)), use_container_width=True)

            # Excel export
            xbuf = BytesIO()
            with pd.ExcelWriter(xbuf, engine="xlsxwriter") as writer:
                df.to_excel(writer, index=False, sheet_name="Meanings")
            xbuf.seek(0)
            st.download_button("📥 Download Meanings (Excel)", xbuf, file_name="meanings.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_excel")
st.markdown("</div>", unsafe_allow_html=True)

st.caption("© BRAIN-CHILD — Suffix Finder • Tracer Generator • Dictionary Explorer — minimal UI")
