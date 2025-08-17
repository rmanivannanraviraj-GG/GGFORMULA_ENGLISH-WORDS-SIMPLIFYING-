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
from nltk.corpus import wordnet

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
@st.cache_data(show_spinner=False)
def cached_wordnet_lemmas() -> List[str]:
    return sorted(set(wordnet.all_lemma_names()), key=lambda x: (len(x), x.lower()))

def datamuse_suffix_search(suffix: str, max_results: int = 500) -> List[str]:
    try:
        r = requests.get("https://api.datamuse.com/words", params={"sp": f"*{suffix}", "max": max_results}, timeout=6)
        return [d['word'] for d in r.json()] if r.status_code == 200 else []
    except: return []

def combined_suffix_search(suffix: str, before_letters: int = 0, datamuse_max: int = 500) -> List[str]:
    suffix = suffix.strip().lower()
    dm = datamuse_suffix_search(suffix, datamuse_max)
    wn = [w for w in cached_wordnet_lemmas() if w.endswith(suffix)]
    merged, seen = [], set()
    for w in dm + wn:
        if w not in seen:
            if before_letters == 0 or (len(w) - len(suffix) == before_letters):
                merged.append(w); seen.add(w)
    return merged

def dictapi_defs(word: str):
    try:
        r = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}", timeout=6)
        data = r.json() if r.status_code == 200 else []
        defs = []
        for m in data[0].get("meanings", []):
            for d in m.get("definitions", []):
                defs.append(d.get("definition",""))
        return defs[:2]
    except: return []

def translate_to_tamil(text: str) -> str:
    if HAS_TRANSLATOR:
        try: return GoogleTranslator(source='auto', target='ta').translate(text)
        except: pass
    try:
        r = requests.get("https://translate.googleapis.com/translate_a/single",
            params={"client":"gtx","sl":"en","tl":"ta","dt":"t","q":text},timeout=6)
        return r.json()[0][0][0] if r.status_code==200 else ""
    except: return ""

def translate_list_parallel(texts: List[str]) -> List[str]:
    with ThreadPoolExecutor(max_workers=6) as ex:
        return list(ex.map(translate_to_tamil, texts))

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
st.markdown("<div class='card'><h3>🔎 Suffix Finder</h3>", unsafe_allow_html=True)
col1,col2,col3=st.columns([2,1,1])
with col1: suffix_input=st.text_input("Suffix","ing")
with col2: before_letters=st.number_input("Letters before suffix (0=any)",0,10,0)
with col3: include_count=st.number_input("Include top N results",1,1000,200)

if suffix_input:
    with st.spinner("Searching..."):
        matches=combined_suffix_search(suffix_input,before_letters,datamuse_max=max(500,include_count))
        matches=matches[:include_count]
        st.session_state["matches"]=matches
    st.success(f"Total matches cached: {len(matches)}")
    if matches:
        # meanings English + Tamil
        eng_defs=[]; ta_defs=[]
        for w in matches[:200]:
            defs=dictapi_defs(w)
            eng_defs.append(defs[0] if defs else "-")
        if eng_defs: ta_defs=translate_list_parallel(eng_defs)
        df=pd.DataFrame({"Word":matches[:200],"English":eng_defs,"Tamil":ta_defs})
        st.dataframe(df,use_container_width=True,height=400)
st.markdown("</div>", unsafe_allow_html=True)

# Tracer Generator
st.markdown("<div class='card'><h3>✏️ Tracer PDF Generator</h3>", unsafe_allow_html=True)
matches=st.session_state.get("matches",["apple","ball","cat","dog","egg","fish"])
n_for_pdf=st.number_input("How many words to include?",1,min(480,len(matches)),min(24,len(matches)))
selected=matches[:n_for_pdf]
if st.button("Generate PDF"):
    pdf_buf=create_tracer_pdf_buffer(selected)
    st.download_button("📥 Download Tracing PDF",pdf_buf,"tracing.pdf","application/pdf")
st.markdown("</div>", unsafe_allow_html=True)

# Dictionary Explorer
st.markdown("<div class='card'><h3>📘 Dictionary Explorer</h3>", unsafe_allow_html=True)
matches=st.session_state.get("matches",[])
if matches:
    eng_defs=[]; ta_defs=[]
    for w in matches[:100]:
        defs=dictapi_defs(w)
        eng_defs.append(defs[0] if defs else "-")
    if eng_defs: ta_defs=translate_list_parallel(eng_defs)
    df=pd.DataFrame({"Word":matches[:100],"English":eng_defs,"Tamil":ta_defs})
    st.dataframe(df,use_container_width=True,height=500)
else:
    st.info("No matches yet. Run suffix search.")
st.markdown("</div>", unsafe_allow_html=True)

st.caption("© BRAIN-CHILD — compact UI — auto refresh — English+Tamil")
