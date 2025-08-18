# app.py
import os
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import streamlit as st
import pandas as pd
import requests
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

# Ensure WordNet
try:
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('wordnet')
try:
    nltk.data.find('corpora/omw-1.4')
except LookupError:
    nltk.download('omw-1.4')

# UI config
st.set_page_config(page_title="BRAIN-CHILD DICTIONARY", layout="wide")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.app-header {
  background: linear-gradient(90deg, #6a11cb, #2575fc);
  padding: 20px; border-radius: 12px; color: white; text-align: center;
  box-shadow: 0 6px 20px rgba(0,0,0,0.12); margin-bottom: 18px;
}
.card { background:#fff; padding:16px; border-radius:12px; box-shadow:0 6px 18px rgba(0,0,0,0.06); margin-bottom:12px; }
.small { color:#666; font-size:0.9rem; }
.code-note { background:#f7f7fb; padding:10px; border-radius:8px; font-size:0.9rem; }
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='app-header'><h1 style='margin:0'>🌟 BRAIN-CHILD DICTIONARY 🌟</h1><div class='small'>Tracing Sheet Generator • Suffix Finder • Dictionary Explorer</div></div>", unsafe_allow_html=True)

# Data dir
DATA_DIR = Path("data"); DATA_DIR.mkdir(exist_ok=True)

POS_MAP = {'n':'Noun','v':'Verb','a':'Adjective','s':'Adjective (Satellite)','r':'Adverb'}

# Cached WordNet words
@st.cache_data(show_spinner=False)
def get_all_words():
    return sorted(set(wordnet.all_lemma_names()), key=lambda x: (len(x), x.lower()))

def find_matches(words, suffix, before_letters):
    suf = suffix.lower()
    return sorted([w for w in words if w.lower().endswith(suf) and (before_letters == 0 or len(w) - len(suf) == before_letters)], key=len)

def find_synonyms(word):
    s = set()
    for syn in wordnet.synsets(word):
        for lem in syn.lemmas():
            s.add(lem.name().replace('_',' '))
    return list(s)

# Translate helpers
def translate_to_tamil(text):
    if HAS_TRANSLATOR:
        try:
            return GoogleTranslator(source='auto', target='ta').translate(text)
        except Exception:
            pass
    # fallback to google translate public endpoint
    try:
        res = requests.get("https://translate.googleapis.com/translate_a/single", params={"client":"gtx","sl":"en","tl":"ta","dt":"t","q": text}, timeout=8)
        if res.status_code == 200:
            return res.json()[0][0][0]
    except Exception:
        pass
    return "(translation unavailable)"

def translate_list_parallel(texts, max_workers=min(5, os.cpu_count() or 2)):
    if not texts:
        return []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        return list(ex.map(translate_to_tamil, texts))

# dictionaryapi.dev fallback
def dictapi_defs(word, timeout=8):
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
                defs.append((pos, d.get("definition","")))
        # dedupe & cap
        seen=set(); out=[]
        for pos, d in defs:
            key=(pos, d.strip())
            if d and key not in seen:
                seen.add(key); out.append((pos, d))
            if len(out)>=4: break
        return out
    except Exception:
        return []

# Optional dotted font support (if KGPrimaryDots.ttf present)
DO_TTF = os.path.exists("KGPrimaryDots.ttf")
if DO_TTF:
    try:
        pdfmetrics.registerFont(TTFont("Dotted", "KGPrimaryDots.ttf"))
    except Exception:
        DO_TTF = False

# --- TRACER PDF generator (fixed settings per requirement) ---
def create_tracer_pdf_buffer(words):
    """
    Fixed behaviour:
      - 6 words per page (2 columns x 3 rows)
      - 5 clone rows per word (light-grey, bold)
      - full-width dashed underline
      - dotted font if available, else Helvetica-Bold
    Returns BytesIO buffer.
    """
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    page_w, page_h = A4

    # fixed margins / sizes
    left_margin = right_margin = 50
    top_margin = 50
    bottom_margin = 50
    usable_w = page_w - left_margin - right_margin
    col_gap = 40
    col_w = (usable_w - col_gap)/2.0
    x_cols = [left_margin, left_margin + col_w + col_gap]

    font_main = "Dotted" if DO_TTF else "Helvetica-Bold"
    font_clone = font_main
    font_size_main = 28
    font_size_clone = 28
    clones_per_word = 5
    line_height = 40
    clone_gap = 10
    block_height = font_size_main + (font_size_clone + clone_gap)*clones_per_word + 60

    y_start_orig = page_h - top_margin
    count_on_page = 0
    y_start = y_start_orig

    for idx, word in enumerate(words):
        # if starting a new page (count_on_page == 0 and idx>0)
        if count_on_page == 0 and idx > 0:
            c.showPage()
            y_start = y_start_orig

        col = count_on_page % 2
        if col == 0 and count_on_page > 0:
            # moved from right col of previous row, go down
            y_start -= block_height

        x = x_cols[col]

        # Model word
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
            # full-width underline across column for comfortable writing
            c.line(x+4, underline_y, x + col_w - 4, underline_y)
            c.setDash()
            y_clone -= (font_size_clone + clone_gap)

        count_on_page += 1
        if count_on_page >= 6:
            count_on_page = 0

    c.save()
    buf.seek(0)
    return buf

# ------------------ UI: Suffix Finder (left) & Tracer Generator (right) ------------------
with st.container():
    left_col, right_col = st.columns([1,1])

    # LEFT: Suffix Finder
    with left_col:
        st.markdown("<div class='card'><h3>🔎 Suffix Finder</h3>", unsafe_allow_html=True)
        suffix = st.text_input("Suffix (e.g., 'ing' or 'ight')", value="ing", key="suffix_input")
        before_letters = st.number_input("Letters before suffix (0 = any)", min_value=0, step=1, value=0, key="before_letters")
        run_search = st.button("Find Words", key="find_words_btn")
        matches = []
        if run_search:
            all_words = get_all_words()
            matches = find_matches(all_words, suffix, before_letters)
            st.success(f"Found {len(matches)} words that end with '{suffix}'.")
            if matches:
                # Save matches to session for use in other actions
                st.session_state['matches'] = matches
                # show a first page of matches (cap)
                st.dataframe(pd.DataFrame(matches[:200], columns=["Word"]), height=min(400, max(200, len(matches[:200])*28)), use_container_width=True)
            else:
                st.info("No matches. Try another suffix or set 'letters before' = 0.")
        st.markdown("</div>", unsafe_allow_html=True)

    # RIGHT: Tracer Generator
    with right_col:
        st.markdown("<div class='card'><h3>✏️ Tracer PDF Generator (6 words/page)</h3>", unsafe_allow_html=True)
        st.markdown("<div class='small'>Fixed: 5 clones / word • full-width dashed underline • 6 words/page</div>", unsafe_allow_html=True)

        # Use matches if available, else sample defaults
        words_source = st.session_state.get('matches', None)
        if words_source:
            st.markdown(f"**Using {len(words_source)} match(es) from suffix search.**")
            use_count = st.number_input("How many matches to include (max 48)", min_value=1, max_value=min(200, len(words_source)), value=min(24, len(words_source)), key="use_count")
            selected_words = words_source[:use_count]
        else:
            # default example set (no manual input box)
            default_words = ["apple","ball","cat","dog","egg","fish","goat","hat","ice","jug","kite","lion"]
            st.markdown("No suffix search run — using default sample words.")
            selected_words = default_words

        if st.button("Generate Tracing PDF (from selected list)", key="gen_pdf_btn"):
            if not selected_words:
                st.warning("No words available to generate PDF.")
            else:
                pdf_buf = create_tracer_pdf_buffer(selected_words)
                st.download_button("📥 Download Tracing PDF", data=pdf_buf, file_name="tracing_practice.pdf", mime="application/pdf", key="dl_pdf")
                st.success("PDF generated — download ready.")

        st.markdown("</div>", unsafe_allow_html=True)

# ------------------ Dictionary Explorer ------------------
st.markdown("<div class='card'><h3>📘 Dictionary Explorer</h3>", unsafe_allow_html=True)
lang_choice = st.selectbox("Show meaning in:", ["English Only", "Tamil Only", "English + Tamil"], index=0, key="lang_choice")

build_label = "Build Meanings Table from suffix results" if 'matches' in st.session_state and st.session_state['matches'] else "Build Meanings Table (use default sample)"
if st.button(build_label, key="build_meanings"):
    if 'matches' in st.session_state and st.session_state['matches']:
        words_for_defs = list(dict.fromkeys(st.session_state['matches']))
    else:
        words_for_defs = ["apple","ball","cat","dog","egg","fish","goat","hat","ice","jug","kite","lion"]

    rows=[]
    for w in words_for_defs:
        synsets = wordnet.synsets(w)
        if synsets:
            for syn in synsets[:3]:
                rows.append({"Word": w, "Word Type": POS_MAP.get(syn.pos(), "Noun"), "English": syn.definition(), "Tamil":"", "Synonyms": ", ".join(find_synonyms(w)[:10]) or "-"})
        else:
            defs = dictapi_defs(w)
            if defs:
                for pos, d in defs:
                    rows.append({"Word": w, "Word Type": pos or "-", "English": d, "Tamil":"", "Synonyms": ", ".join(find_synonyms(w)[:10]) or "-"})
            else:
                rows.append({"Word": w, "Word Type":"-","English":"-","Tamil":"-","Synonyms":"-"})

    df = pd.DataFrame(rows)

    # Tamil translations (parallel)
    if lang_choice != "English Only" and not df.empty:
        eng_list = df["English"].fillna("-").tolist()
        with st.spinner("Fetching Tamil translations..."):
            ta_list = translate_list_parallel(eng_list)
        df["Tamil"] = ta_list

    # Display chosen columns
    if lang_choice == "English Only":
        df_view = df[["Word","Word Type","English","Synonyms"]]
    elif lang_choice == "Tamil Only":
        df_view = df[["Word","Word Type","Tamil","Synonyms"]]
    else:
        df_view = df[["Word","Word Type","English","Tamil","Synonyms"]]

    st.dataframe(df_view, height=min(600, max(300, len(df_view)*28)), use_container_width=True)

    # Excel export
    xbuf = BytesIO()
    with pd.ExcelWriter(xbuf, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Meanings")
    xbuf.seek(0)
    st.download_button("📥 Download Meanings (Excel)", xbuf, file_name="meanings.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

st.markdown("</div>", unsafe_allow_html=True)

st.caption("© BRAIN-CHILD — Tracing Generator + Dictionary Explorer • Fixed 6 words/page layout")
