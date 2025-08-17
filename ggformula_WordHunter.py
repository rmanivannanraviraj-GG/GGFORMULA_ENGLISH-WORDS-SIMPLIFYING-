# app_full.py
import os
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List

import requests
import streamlit as st
import pandas as pd
import nltk
from nltk.corpus import wordnet as wn
from PyDictionary import PyDictionary
from googletrans import Translator

# ------------------ Init ------------------
dictionary = PyDictionary()
translator = Translator()

try:
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('wordnet')
try:
    nltk.data.find('corpora/omw-1.4')
except LookupError:
    nltk.download('omw-1.4')

# ------------------ Streamlit config ------------------
st.set_page_config(page_title="🌟 BRAIN-CHILD DICTIONARY", layout="wide")
st.markdown("""
<style>
.card { background: #fff; border-radius:10px; padding:12px; margin-bottom:12px; box-shadow:0 6px 18px rgba(0,0,0,0.04);}
.stButton>button { padding:6px 10px; border-radius:8px; }
.stTextInput>div>div>input, .stNumberInput>div>div>input { padding:6px 8px; }
.block-container { padding: 8px; }
.header { padding:14px; border-radius:10px; color:white; background: linear-gradient(90deg,#28a745,#218838);}
</style>
""", unsafe_allow_html=True)
st.markdown("<div class='header'><h2>🌟 BRAIN-CHILD DICTIONARY</h2><div>Suffix Finder • Tracer • Dictionary</div></div>", unsafe_allow_html=True)

# ------------------ UTILS ------------------
@st.cache_data
def fetch_datamuse_suffix(suffix: str, before_letters: int = 0, top_n: int = 50) -> List[str]:
    pattern = f"{'?'*before_letters}{suffix}"
    try:
        res = requests.get(f"https://api.datamuse.com/words?sp={pattern}&max={top_n}").json()
        return [w['word'] for w in res]
    except:
        return []

def get_meaning_tamil(word: str):
    meaning = dictionary.meaning(word)
    eng_mean = "; ".join([f"{k}: {', '.join(v)}" for k,v in meaning.items()]) if meaning else "N/A"
    try:
        tamil_mean = translator.translate(eng_mean, src='en', dest='ta').text
    except:
        tamil_mean = "(translation unavailable)"
    return eng_mean, tamil_mean

# ------------------ TRACER PDF ------------------
def create_tracer_pdf(words: List[str]) -> BytesIO:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib import colors
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    page_w, page_h = A4
    col_gap, col_w = 32, (page_w-80-32)/2
    x_cols = [40, 40+col_w+col_gap]
    y_start, block_h = page_h-50, 200
    clones = 5
    for i, w in enumerate(words):
        if i%6==0 and i>0: c.showPage(); y_start=page_h-50
        col = i%2
        if col==0 and i%6!=0: y_start-=block_h
        x = x_cols[col]
        c.setFont("Helvetica-Bold",28); c.drawCentredString(x+col_w/2,y_start,w)
        y=y_start-40; c.setFillColor(colors.grey)
        for _ in range(clones):
            c.drawCentredString(x+col_w/2,y,w)
            c.line(x+6,y-6,x+col_w-6,y-6); y-=38
        c.setFillColor(colors.black)
    c.save(); buf.seek(0)
    return buf

# ------------------ SESSION ------------------
if 'suffix_matches' not in st.session_state:
    st.session_state['suffix_matches'] = []

# ------------------ Suffix Finder ------------------
with st.container():
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("🔎 Suffix Finder (WordNet + Datamuse)")

    before_count = st.number_input("Letters before suffix", min_value=0, max_value=10, value=0)
    suffix = st.text_input("Enter suffix", value="ing")
    top_n = st.slider("Include top N results", 10, 200, 50)
    run = st.button("Find Words")

    if run and suffix:
        words = fetch_datamuse_suffix(suffix, before_count, top_n)
        st.session_state['suffix_matches'] = words
        st.success(f"Found {len(words)} words!")
    else:
        words = st.session_state.get('suffix_matches', [])

    if words:
        data = []
        for w in words[:top_n]:
            eng_mean, tamil_mean = get_meaning_tamil(w)
            data.append([w, eng_mean, tamil_mean])
        df = pd.DataFrame(data, columns=["Word", "English Meaning", "Tamil Meaning"])
        st.dataframe(df, height=300, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ------------------ Tracer PDF ------------------
with st.container():
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("✏️ Tracer PDF Generator")
    if words:
        n_words_pdf = st.number_input("Number of top words for PDF", 1, min(480,len(words)), value=min(24,len(words)))
        gen_pdf = st.button("Generate & Download PDF")
        if gen_pdf:
            pdf_buf = create_tracer_pdf(words[:n_words_pdf])
            st.download_button("📥 Download PDF", data=pdf_buf, file_name="tracer.pdf", mime="application/pdf")
    else:
        st.info("No words available for PDF generation.")
    st.markdown("</div>", unsafe_allow_html=True)

# ------------------ Dictionary Explorer ------------------
with st.container():
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("📘 Dictionary Explorer")

    query = st.text_input("Enter a word to explore", "happy")
    if query:
        eng_mean, tamil_mean = get_meaning_tamil(query)
        synonyms = dictionary.synonym(query) or []
        df2 = pd.DataFrame({
            "Word": [query],
            "English Meaning": [eng_mean],
            "Tamil Meaning": [tamil_mean],
            "Synonyms": [", ".join(synonyms)]
        })
        st.dataframe(df2, height=200, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)
