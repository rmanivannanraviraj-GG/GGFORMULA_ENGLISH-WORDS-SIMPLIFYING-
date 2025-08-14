# app_streamlit_suffix_ready_with_count_nosource.py
import streamlit as st
import pandas as pd
import textwrap
from io import BytesIO
from pathlib import Path
from deep_translator import GoogleTranslator
from nltk.corpus import wordnet
import nltk

# NLTK Data Download
nltk.download('wordnet')
nltk.download('omw-1.4')

# ---------- CONFIG ----------
st.set_page_config(page_title="Suffix Learner", layout="wide")
CACHE_DIR = Path("data")
CACHE_DIR.mkdir(exist_ok=True)
CACHE_PATH = CACHE_DIR / "wordlist.txt"

POS_MAP = {'n': 'Noun', 'v': 'Verb', 'a': 'Adjective', 's': 'Adjective Satellite', 'r': 'Adverb'}
WRAP_EN = 80
WRAP_TA = 100

# ---------- Helpers ----------
@st.cache_data(show_spinner=False)
def translate_to_tamil(text: str):
    try:
        return GoogleTranslator(source='auto', target='ta').translate(text)
    except Exception:
        return ""

def find_matches(words, suffix, before_letters):
    suf = suffix.lower()
    matched = []
    for w in words:
        if w.lower().endswith(suf):
            if before_letters == 0:
                matched.append(w)
            else:
                if len(w) - len(suf) == before_letters:
                    matched.append(w)
    matched.sort(key=len)
    return matched

def make_highlight_html(word, suf):
    if suf and word.lower().endswith(suf.lower()):
        p = word[:-len(suf)]
        s = word[-len(suf):]
        return f"<div style='font-size:20px; padding:6px;'><span>{p}</span><span style='color:#e53935; font-weight:700'>{s}</span></div>"
    else:
        return f"<div style='font-size:20px; padding:6px;'>{word}</div>"

# ---------- UI Styling ----------
st.markdown("""
<style>
.app-header {background: linear-gradient(90deg,#a1c4fd,#c2e9fb); padding: 12px; border-radius: 8px;}
.kid-card {background:#fffbe6; border-radius:8px; padding:12px; box-shadow: 0 2px 6px rgba(0,0,0,0.08);}
.word-box {background:#fff; border-radius:6px; padding:8px; margin-bottom:6px;}
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='app-header'><h1 style='margin:0'>🎈 Suffix Learner — Fun with Words</h1><small>Find words by suffix, see English meanings & Tamil translations</small></div>", unsafe_allow_html=True)
st.write(" ")

# Sidebar
with st.sidebar:
    st.header("🔧 Settings")
    before_letters = st.number_input("Letters before suffix (exact). Leave 0 for any", min_value=0, step=1, value=0)

# Load WordNet words
all_words = sorted(set(wordnet.all_lemma_names()), key=lambda x: (len(x), x.lower()))

# Layout
col1, col2 = st.columns([1,2])

with col1:
    st.subheader("🔎 Search Words")
    suffix_input = st.text_input("Suffix (e.g., 'ight')", value="ight")
    matches = find_matches(all_words, suffix_input, before_letters)

    # ✅ Show total count
    st.markdown(f"**Total Words Found:** {len(matches)}")

    # Word list display
    st.markdown("<div style='max-height:520px; overflow:auto; padding:6px; background:#fff8e1; border-radius:6px;'>", unsafe_allow_html=True)
    for w in matches[:5000]:
        st.markdown(make_highlight_html(w, suffix_input), unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.markdown("🔁 Quick pick (click to load meanings):")
    chosen = st.selectbox("Choose a word", [""] + matches[:200], label_visibility="collapsed")
    
    header_col1, header_col2 = st.columns([1,4])
    with header_col1:
        if chosen:
            towrite = BytesIO()
            syns = wordnet.synsets(chosen)
            if syns:
                data_rows = []
                for i, syn in enumerate(syns, start=1):
                    pos = POS_MAP.get(syn.pos(), syn.pos())
                    eng = syn.definition()
                    ta = translate_to_tamil(eng)
                    data_rows.append({"No": i, "POS": pos, "English": eng, "Tamil": ta})
                
                df_export = pd.DataFrame(data_rows)
                with pd.ExcelWriter(towrite, engine="xlsxwriter") as writer:
                    df_export.to_excel(writer, index=False, sheet_name="Meanings")
                towrite.seek(0)
                st.download_button("📥 Download Excel", towrite, file_name=f"{chosen}_meanings.xlsx")
    
    with header_col2:
        st.subheader("📘 Meanings & Translations")
    
    if chosen:
        st.markdown(f"### 🔤 **{chosen}**")
        syns = wordnet.synsets(chosen)
        if not syns:
            st.info("No WordNet meanings found for this word.")
        else:
            html = "<table style='width:100%; border-collapse:collapse;'>"
            html += "<tr style='background:#a1c4fd'><th style='padding:8px'>No</th><th>POS</th><th>English</th><th>Tamil</th></tr>"
            for i, syn in enumerate(syns, start=1):
                pos = POS_MAP.get(syn.pos(), syn.pos())
                eng = syn.definition()
                ta = translate_to_tamil(eng)
                eng_wrapped = "<br>".join(textwrap.wrap(eng, WRAP_EN))
                ta_wrapped = "<br>".join(textwrap.wrap(ta, WRAP_TA)) if ta else ""
                html += f"<tr><td style='padding:8px;border-bottom:1px solid #eee'>{i}</td>"
                html += f"<td style='padding:8px;border-bottom:1px solid #eee'>{pos}</td>"
                html += f"<td style='padding:8px;border-bottom:1px solid #eee'>{eng_wrapped}</td>"
                html += f"<td style='padding:8px;border-bottom:1px solid #eee'>{ta_wrapped}</td></tr>"
            html += "</table>"
            st.markdown(html, unsafe_allow_html=True)

st.markdown("<div style='margin-top:12px; color:#555'>Tip: Use short suffixes (like 'ight') and exact letters-before-suffix count to narrow results.</div>", unsafe_allow_html=True)
