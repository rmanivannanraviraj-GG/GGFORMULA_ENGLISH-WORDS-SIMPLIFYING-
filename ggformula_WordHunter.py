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

# CSS Styling with improved padding, font, and box-shadow
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap');
body {
    font-family: 'Roboto', sans-serif;
}
.app-header {
    background: linear-gradient(90deg, #3498db, #2ecc71);
    padding: 20px;
    border-radius: 12px;
    color: white;
    text-align: center;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    margin-bottom: 20px;
}
.main-container {
    background-color: #f0f2f6;
    padding: 20px;
    border-radius: 12px;
    margin-top: 20px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}
.content-box {
    background-color: #ffffff;
    padding: 15px;
    border-radius: 8px;
    border: 1px solid #e0e0e0;
    max-height: 450px;
    overflow-y: auto;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}
.st-emotion-cache-1r65d8v {
    background: #f0f2f6;
}
.st-emotion-cache-12m3106 {
    padding-left: 1rem;
    padding-right: 1rem;
}
.st-emotion-cache-1f8p3j0 > div {
    margin-top: 0;
}
.st-emotion-cache-1f8p3j0 > div > div > h3 {
    margin-top: 0;
}
.st-emotion-cache-1f8p3j0 > div > div > p {
    margin-top: 0;
}
</style>
""", unsafe_allow_html=True)

# Streamlit page config
st.set_page_config(page_title="Word Suffix Finder", layout="wide")
CACHE_DIR = Path("data")
CACHE_DIR.mkdir(exist_ok=True)

# POS mapping
POS_MAP = {
    'n': 'Noun',
    'v': 'Verb',
    'a': 'Adjective',
    's': 'Adjective (Satellite)',
    'r': 'Adverb'
}

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

# Function to create the PDF content
# --- TRACER PDF generator (fixed settings per requirement) ---
def create_tracer_pdf_buffer(words):
    """
    Fixed behaviour:
      - 6 words per page (2 columns x 3 rows)
      - 5 clone rows per word (light-grey, bold)
      - full-width dashed underline
      - dotted font if available, else Courier-Bold
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

    font_main = "Dotted" if DO_TTF else "Courier-Bold"
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
# --- Main Streamlit App Layout ---
st.markdown("<div class='app-header'><h1 style='margin:0'>BRAIN-CHILD DICTIONARY</h1><small>Learn spellings and master words with suffixes and meanings</small></div>", unsafe_allow_html=True)

with st.container():
    st.markdown("<div class='main-container'>", unsafe_allow_html=True)
    
    col_input1, col_input2 = st.columns(2)
    with col_input1:
        before_letters = st.number_input("Letters Before Suffix (0 for any number)", min_value=0, step=1, value=0, key='before_letters_main')
    with col_input2:
        lang_choice = st.selectbox("Show Meaning in:", ["English Only", "Tamil Only", "English + Tamil"], key='lang_choice_main')

    # Layout for the main content sections
    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.subheader("🔎 Find Words")
        with st.form("find_words_form"):
            suffix_input = st.text_input("Suffix (e.g., 'ight')", value="ight", key='suffix_input_form')
            search_button = st.form_submit_button(label='Search Words')

        if search_button:
            all_words = sorted(set(wordnet.all_lemma_names()), key=lambda x: (len(x), x.lower()))
            matches = find_matches(all_words, suffix_input, before_letters)
            st.session_state['matches'] = matches
            st.session_state['search_triggered'] = True
            
            st.markdown(f"**Total Words Found:** {len(matches)}")
            
            if matches:
                matches_df = pd.DataFrame(matches, columns=["Word"])
                st.dataframe(matches_df, height=450, use_container_width=True)
            else:
                st.info("No results found.")

    with col2:
        st.subheader("📝 Word Tracer Generator")
        
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

    # Word Definitions section is now below
    st.markdown("---")
    st.subheader("📘 Word Definitions")

    if st.session_state.get('search_triggered'):
        if 'matches' in st.session_state:
            matches = st.session_state['matches']
            if matches:
                data_rows = []
                for word in matches:
                    syns = wordnet.synsets(word)
                    if not syns:
                        data_rows.append({"Word": word, "Word Type": "-", "English": "-", "Tamil": "-"})
                    else:
                        for syn in syns:
                            eng = syn.definition()
                            data_rows.append({
                                "Word": word,
                                "Word Type": POS_MAP.get(syn.pos(), "Noun"),
                                "English": eng,
                                "Tamil": "-"
                            })

                df_export = pd.DataFrame(data_rows)

                if st.session_state.lang_choice_main == "English Only":
                    df_view = df_export[["Word", "Word Type", "English"]]
                elif st.session_state.lang_choice_main == "Tamil Only":
                    df_view = df_export[["Word", "Word Type", "Tamil"]]
                else:
                    df_view = df_export

                st.dataframe(df_view, height=450, use_container_width=True)

                towrite = BytesIO()
                with pd.ExcelWriter(towrite, engine="xlsxwriter") as writer:
                    df_export.to_excel(writer, index=False, sheet_name="Meanings")
                towrite.seek(0)
                st.download_button("📥 Download as EXCEL SHEET", towrite, file_name="all_meanings.xlsx")
            else:
                st.info("No results found.")
        else:
            st.info("Please enter a suffix and click 'Search Words' to see definitions.")
    else:
        st.info("Please enter a suffix and click 'Search Words' to see definitions.")
    
    st.markdown("</div>", unsafe_allow_html=True)












