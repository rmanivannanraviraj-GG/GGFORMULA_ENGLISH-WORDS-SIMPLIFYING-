# app.py
import os
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List

import requests
import streamlit as st
import pandas as pd
import nltk

from googletrans import Translator
from nltk.corpus import wordnet
from PyDictionary import PyDictionary

# Initialize
dictionary = PyDictionary()

# Example
word = "apple"

meaning = dictionary.meaning(word)
synonym = dictionary.synonym(word)
antonym = dictionary.antonym(word)

print("Word:", word)
print("Meaning:", meaning)
print("Synonyms:", synonym)
print("Antonyms:", antonym)


# Translator
try:
    from deep_translator import GoogleTranslator
    HAS_TRANSLATOR = True
except Exception:
    HAS_TRANSLATOR = False

# ReportLab for PDF
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Ensure WordNet
try: nltk.data.find('corpora/wordnet')
except LookupError: nltk.download('wordnet')
try: nltk.data.find('corpora/omw-1.4')
except LookupError: nltk.download('omw-1.4')

# ---------------- UI CONFIG ----------------
st.set_page_config(page_title="BRAIN-CHILD • Suffix → Tracer → Dictionary", layout="wide")
st.markdown("""
<style>
.header {
    padding: 14px;
    border-radius: 10px;
    color: white;
    background: linear-gradient(90deg,#28a745,#218838);
}
.card {
    background: #fff;
    border-radius: 10px;
    padding: 10px 12px;
    margin-bottom: 12px;
    box-shadow: 0 6px 18px rgba(0,0,0,0.04);
}
.stButton>button { padding:6px 10px; border-radius:8px; }
.stTextInput>div>div>input, .stNumberInput>div>div>input { padding:6px 8px; }
.block-container { padding: 8px; }
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='header'><h2 style='margin:0'>🌟 BRAIN-CHILD DICTIONARY</h2><div>Suffix Finder • Tracer • Dictionary</div></div>", unsafe_allow_html=True)

# ---------------- UTILS ----------------
st.set_page_config(page_title="🌟 BRAIN-CHILD DICTIONARY", layout="wide")

st.markdown(
    """
    <style>
    body {
        font-family: 'Inter', sans-serif;
        background: linear-gradient(90deg, #0f9b0f, #00b09b);
        color: #222;
    }
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
    }
    .card {
        background: white;
        padding: 1rem;
        border-radius: 1rem;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    h1 {
        text-align: center;
        color: white;
        padding: 0.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown("<h1>🌟 BRAIN-CHILD DICTIONARY</h1>", unsafe_allow_html=True)

translator = Translator()

# ---------------- TRACER PDF ----------------
def create_tracer_pdf_buffer(words: List[str]) -> BytesIO:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    page_w, page_h = A4
    col_gap, col_w = 32, (page_w-80-32)/2
    x_cols = [40, 40+col_w+col_gap]
    y_start, block_h = page_h-50, 200
    clones = 5

    for i,w in enumerate(words):
        if i%6==0 and i>0: c.showPage(); y_start = page_h-50
        col = i%2
        if col==0 and i%6!=0: y_start -= block_h
        x = x_cols[col]

        c.setFont("Helvetica-Bold",28); c.drawCentredString(x+col_w/2,y_start,w)
        y=y_start-40; c.setFillColor(colors.grey)
        for _ in range(clones):
            c.drawCentredString(x+col_w/2,y,w)
            c.line(x+6,y-6,x+col_w-6,y-6); y-=38
        c.setFillColor(colors.black)
    c.save(); buf.seek(0); return buf

# ---------------- UI ----------------
# Suffix Finder
with st.container():
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("Suffix Finder")

    before_count = st.number_input("Letters before suffix", min_value=1, max_value=10, value=3)
    suffix = st.text_input("Enter suffix", value="ing")
    top_n = st.slider("Include top N results", 10, 200, 50)

    words = []

    if suffix:
        # Datamuse API
        url = f"https://api.datamuse.com/words?sp={'?'*before_count}{suffix}&max={top_n}"
        res = requests.get(url).json()
        words = [w['word'] for w in res]

    st.write(f"✅ Total matches cached: {len(words)}")

    if words:
        data = []
        for w in words:
            synsets = wn.synsets(w)
            meaning = synsets[0].definition() if synsets else "N/A"
            tamil = translator.translate(w, src="en", dest="ta").text
            data.append([w, meaning, tamil])

        df = pd.DataFrame(data, columns=["Word", "English Meaning", "Tamil Meaning"])
        st.table(df.head(top_n))

    st.markdown("</div>", unsafe_allow_html=True)

# Tracer Generator
with st.container():

    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("Tracer PDF Generator")
    st.write("📄 PDF will generate worksheets with **6 words per page** (auto-set).")
    st.info("⚡ Auto tracer generator feature coming soon!")
    st.markdown("</div>", unsafe_allow_html=True)


# Dictionary Explorer
with st.container():
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("Dictionary Explorer")

    query = st.text_input("Enter a word to explore", "happy")
    if query:
        synsets = wn.synsets(query)
        if synsets:
            defs = [s.definition() for s in synsets[:3]]
            synonyms = list(set([l.name() for s in synsets for l in s.lemmas()]))[:5]
        else:
            defs, synonyms = ["N/A"], []

        tamil = translator.translate(query, src="en", dest="ta").text

        df2 = pd.DataFrame({
            "Word": [query],
            "English Meaning": ["; ".join(defs)],
            "Tamil Meaning": [tamil],
            "Synonyms": [", ".join(synonyms)]
        })

        st.table(df2)

    st.markdown("</div>", unsafe_allow_html=True)



