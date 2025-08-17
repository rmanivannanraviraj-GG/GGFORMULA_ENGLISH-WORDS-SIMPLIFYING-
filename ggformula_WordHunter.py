# app.py
import os
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests
import streamlit as st
import pandas as pd
import nltk
from nltk.corpus import wordnet

# Translator (optional)
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

# ------------------ ensure WordNet data ------------------
try:
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('wordnet')
try:
    nltk.data.find('corpora/omw-1.4')
except LookupError:
    nltk.download('omw-1.4')

# ------------------ app config & compact CSS ------------------
st.set_page_config(page_title="Brain-Child • Compact Suffix→Tracer→Dictionary", layout="wide")
st.markdown(
    """
    <style>
    /* Compact layout: remove most paddings/margins */
    .app-header { margin:0; padding:12px 8px; border-radius:8px; text-align:center; color:white;
        background: linear-gradient(90deg,#2575fc,#6a11cb); font-weight:700; font-size:18px; }
    .row-card { background:#ffffff; border-radius:8px; padding:8px; margin:0 4px; box-shadow:0 2px 8px rgba(0,0,0,0.06);}
    .stButton>button { padding:6px 10px; }
    .small-note { color:#666; font-size:12px; margin-top:4px; }
    .streamlit-expanderHeader { padding: 0; }
    /* Reduce dataframe padding */
    .element-container .stDataFrame { padding: 6px 6px 6px 6px; }
    /* Compact columns spacing */
    .block-container { padding-top: 8px; padding-left: 8px; padding-right: 8px; padding-bottom: 8px; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown("<div class='app-header'>🌟 BRAIN-CHILD • Suffix → Tracer → Dictionary (Compact)</div>", unsafe_allow_html=True)

# ------------------ Utilities ------------------
DATA_DIR = Path("data"); DATA_DIR.mkdir(exist_ok=True)
POS_MAP = {'n':'Noun','v':'Verb','a':'Adjective','s':'Adjective (Satellite)','r':'Adverb'}

@st.cache_data(show_spinner=False)
def get_all_wordnet_lemmas():
    return sorted(set(wordnet.all_lemma_names()), key=lambda x: (len(x), x.lower()))

def find_synonyms(w):
    s = set()
    for syn in wordnet.synsets(w):
        for lem in syn.lemmas():
            s.add(lem.name().replace('_',' '))
    return list(s)

# Datamuse suffix search (online)
def datamuse_suffix_search(suffix, max_results=200):
    # Datamuse query: words that end with suffix
    q = f"*{suffix}"
    try:
        resp = requests.get("https://api.datamuse.com/words", params={"sp": q, "max": max_results}, timeout=6)
        if resp.status_code == 200:
            data = resp.json()
            # datamuse returns dicts with 'word'
            return [d['word'] for d in data if 'word' in d]
    except Exception:
        pass
    return []

# dictionaryapi.dev fallback
def dictapi_defs(word, timeout=8):
    try:
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
        r = requests.get(url, timeout=timeout)
        if r.status_code != 200:
            return []
        data = r.json()
        defs=[]
        for meaning in data[0].get("meanings", []):
            pos = meaning.get("partOfSpeech","")
            for d in meaning.get("definitions",[]):
                defs.append((pos, d.get("definition","")))
        # dedupe + cap
        seen=set(); out=[]
        for pos,d in defs:
            key=(pos, d.strip())
            if d and key not in seen:
                seen.add(key); out.append((pos,d))
            if len(out)>=4: break
        return out
    except Exception:
        return []

# Tamil translate helper (deep_translator preferred, else google public)
def translate_to_tamil(text):
    if not text:
        return ""
    if HAS_TRANSLATOR:
        try:
            return GoogleTranslator(source='auto', target='ta').translate(text)
        except Exception:
            pass
    # fallback
    try:
        res = requests.get("https://translate.googleapis.com/translate_a/single",
                           params={"client":"gtx","sl":"en","tl":"ta","dt":"t","q": text}, timeout=8)
        if res.status_code == 200:
            return res.json()[0][0][0]
    except Exception:
        pass
    return "(translation unavailable)"

def translate_list_parallel(texts, max_workers=min(6, os.cpu_count() or 2)):
    if not texts:
        return []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        return list(ex.map(translate_to_tamil, texts))

# Optional dotted font
DO_TTF = os.path.exists("KGPrimaryDots.ttf")
if DO_TTF:
    try:
        pdfmetrics.registerFont(TTFont("Dotted", "KGPrimaryDots.ttf"))
    except Exception:
        DO_TTF = False

# ------------------ Fixed Tracer PDF generator (6 words/page, 5 clones, full-width dashed underline) ------------------
def create_tracer_pdf_buffer(words):
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    page_w, page_h = A4

    left_margin = right_margin = 38
    top_margin = 42
    col_gap = 28
    usable_w = page_w - left_margin - right_margin
    col_w = (usable_w - col_gap)/2.0
    x_cols = [left_margin, left_margin + col_w + col_gap]

    font_main = "Dotted" if DO_TTF else "Helvetica-Bold"
    font_clone = font_main
    font_size_main = 28
    font_size_clone = 28
    clones_per_word = 5
    line_height = 38
    clone_gap = 10
    block_height = font_size_main + (font_size_clone + clone_gap)*clones_per_word + 58

    y_start_orig = page_h - top_margin
    y_start = y_start_orig
    count_on_page = 0

    for idx, word in enumerate(words):
        # New page when starting (except first)
        if count_on_page == 0 and idx > 0:
            c.showPage()
            y_start = y_start_orig

        col = count_on_page % 2
        if col == 0 and count_on_page > 0:
            y_start -= block_height

        x = x_cols[col]

        # Model bold main word
        c.setFont(font_main, font_size_main)
        c.setFillColor(colors.black)
        c.drawCentredString(x + col_w/2, y_start, word)

        # Clone rows (light grey) + full-width dashed underline
        c.setFont(font_clone, font_size_clone)
        c.setFillColor(colors.lightgrey)
        y_clone = y_start - line_height
        for _ in range(clones_per_word):
            c.drawCentredString(x + col_w/2, y_clone, word)
            underline_y = y_clone - 6
            c.setDash(3,3)
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

# ------------------ UI: compact 1-row layout ------------------
cols = st.columns([1,1,1], gap="small")

# LEFT: Datamuse Suffix Finder
with cols[0]:
    st.markdown("<div class='row-card'>", unsafe_allow_html=True)
    st.write("### 🔎 Suffix Finder")
    suffix = st.text_input("Suffix (e.g. 'ing')", value="ing", key="suffix_input_compact")
    max_results = st.number_input("Max results (online)", min_value=20, max_value=2000, value=500, step=20, key="max_res")
    find_btn = st.button("Find (online)", key="find_datamuse")
    st.markdown("<div class='small-note'>Datamuse online lookup — returns many English words ending with the suffix.</div>", unsafe_allow_html=True)

    matches = []
    if find_btn and suffix:
        with st.spinner("Querying Datamuse..."):
            matches = datamuse_suffix_search(suffix, max_results=max_results)
        st.session_state['matches'] = matches
        st.success(f"Found {len(matches)} words ending with '{suffix}'. (Showing top 200)")
        if matches:
            st.dataframe(pd.DataFrame(matches[:200], columns=["Word"]), height=300, use_container_width=True)
    else:
        # show prior results if exist
        if 'matches' in st.session_state:
            matches = st.session_state['matches']
            st.write(f"Stored matches: {len(matches)}")
            st.dataframe(pd.DataFrame(matches[:200], columns=["Word"]), height=300, use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)

# MIDDLE: Tracer PDF Generator (fixed behavior)
with cols[1]:
    st.markdown("<div class='row-card'>", unsafe_allow_html=True)
    st.write("### ✏️ Tracer PDF Generator (6 words / page)")
    st.markdown("<div class='small-note'>Fixed: 5 clones/word • full-width dashed underline • 6 words/page</div>", unsafe_allow_html=True)

    # choose how many top matches to include (compact numeric input)
    available = st.session_state.get('matches', None)
    if available:
        total_avail = len(available)
        include_n = st.number_input("Include top N matches for PDF", min_value=1, max_value=min(200, total_avail), value=min(24, total_avail), key="include_n")
        selected_words = available[:include_n]
        st.write(f"Using top {include_n} matches.")
    else:
        # fallback sample words (no manual input box)
        sample = ["apple","ball","cat","dog","egg","fish","goat","hat","ice","jug","kite","lion"]
        st.write("No suffix search results — using sample set.")
        selected_words = sample

    gen_btn = st.button("Generate & Download Tracing PDF", key="gen_tracer_pdf")
    if gen_btn:
        if not selected_words:
            st.warning("Nothing to generate.")
        else:
            with st.spinner("Generating PDF..."):
                pdf_buf = create_tracer_pdf_buffer(selected_words)
            st.download_button("📥 Download Tracing PDF", data=pdf_buf, file_name="tracing_practice.pdf", mime="application/pdf", key="dl_tracer")
            st.success("Tracing PDF ready for download.")
    st.markdown("</div>", unsafe_allow_html=True)

# RIGHT: Dictionary Explorer
with cols[2]:
    st.markdown("<div class='row-card'>", unsafe_allow_html=True)
    st.write("### 📘 Dictionary Explorer")
    st.markdown("<div class='small-note'>WordNet definitions + synonyms; fallback to dictionaryapi.dev; Tamil translations fetched.</div>", unsafe_allow_html=True)

    build_btn = st.button("Build Meanings Table (use matches or sample)", key="build_meanings")
    if build_btn:
        words_source = st.session_state.get('matches', None)
        if words_source:
            words_for_defs = list(dict.fromkeys(words_source))[:200]  # cap
        else:
            words_for_defs = ["apple","ball","cat","dog","egg","fish","goat","hat","ice","jug","kite","lion"]

        rows=[]
        for w in words_for_defs:
            synsets = wordnet.synsets(w)
            if synsets:
                for syn in synsets[:2]:
                    rows.append({"Word": w, "Word Type": POS_MAP.get(syn.pos(), "Noun"), "English": syn.definition(), "Tamil": "", "Synonyms": ", ".join(find_synonyms(w)[:8]) or "-"})
            else:
                defs = dictapi_defs(w)
                if defs:
                    for pos, d in defs[:2]:
                        rows.append({"Word": w, "Word Type": pos or "-", "English": d, "Tamil":"", "Synonyms": ", ".join(find_synonyms(w)[:8]) or "-"})
                else:
                    rows.append({"Word": w, "Word Type":"-","English":"-","Tamil":"-","Synonyms":"-"})

        df = pd.DataFrame(rows)

        # Tamil translations for English column (parallel)
        if not df.empty:
            eng_texts = df["English"].fillna("-").tolist()
            with st.spinner("Fetching Tamil translations..."):
                ta_list = translate_list_parallel(eng_texts)
            df["Tamil"] = ta_list

        # show compact table (cap rows)
        st.dataframe(df.head(300), height=min(600, max(240, len(df.head(300))*28)), use_container_width=True)

        # Excel export (English + Tamil + synonyms)
        xbuf = BytesIO()
        with pd.ExcelWriter(xbuf, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Meanings")
        xbuf.seek(0)
        st.download_button("📥 Download Meanings (Excel)", xbuf, file_name="meanings.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_excel")

    st.markdown("</div>", unsafe_allow_html=True)

# footer
st.caption("© BRAIN-CHILD — Compact Suffix Finder • Tracer PDF Generator • Dictionary Explorer")
