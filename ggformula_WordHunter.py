# app_streamlit_suffix_full.py
import streamlit as st
import pandas as pd
import textwrap
import os
import requests
import gzip
from io import BytesIO
from pathlib import Path
from deep_translator import GoogleTranslator
from nltk.corpus import wordnet
import nltk

# 🔹 NLTK Data Download
nltk.download('wordnet')
nltk.download('omw-1.4')

# Title
st.title("📚 Word Hunter - English to Tamil Dictionary")

# ---------- CONFIG ----------
st.set_page_config(page_title="Suffix Learner", layout="wide")
CACHE_DIR = Path("data")
CACHE_DIR.mkdir(exist_ok=True)
CACHE_PATH = CACHE_DIR / "wordlist.txt"
CACHE_GZ_PATH = CACHE_DIR / "wordlist.txt.gz"

POS_MAP = {'n': 'Noun', 'v': 'Verb', 'a': 'Adjective', 's': 'Adjective Satellite', 'r': 'Adverb'}
WRAP_EN = 80
WRAP_TA = 100
# ---------- Helpers ----------
@st.cache_data(show_spinner=False)
def ensure_wordnet():
    try:
        nltk.data.find("corpora/wordnet")
    except Exception:
        nltk.download("wordnet")
        nltk.download("omw-1.4")

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
            if before_letters is None or before_letters == 0:
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

# ---------- UI ----------
ensure_wordnet()

st.markdown("""
<style>
.app-header {background: linear-gradient(90deg,#ffecd2,#fcb69f); padding: 12px; border-radius: 8px;}
.kid-card {background:#fffbe6; border-radius:8px; padding:12px; box-shadow: 0 2px 6px rgba(0,0,0,0.08);}
.word-box {background:#fff; border-radius:6px; padding:8px; margin-bottom:6px;}
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='app-header'><h1 style='margin:0'>🎈 Suffix Learner — Fun with Words</h1><small>Find words by suffix, see English meanings & Tamil translations</small></div>", unsafe_allow_html=True)
st.write(" ")

# Sidebar: settings / add word
with st.sidebar:
    st.header("🔧 Settings")
    st.markdown("**Remote wordlist URL**:")
    remote_input = st.text_input("Remote wordlist URL (optional)", value=WORDLIST_REMOTE_URL)
    before_letters = st.number_input("Letters before suffix (exact). Leave 0 for any", min_value=0, step=1, value=1)
    st.markdown("---")
    st.header("➕ Add a new word (local)")
    add_w = st.text_input("Add word (single token)")
    if st.button("Add to local list"):
        if add_w.strip():
            CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(CACHE_PATH, "a", encoding="utf-8") as f:
                f.write("\n" + add_w.strip())
            st.success(f"Added '{add_w.strip()}' to local cache.")

# Load words
remote_url = remote_input.strip() or WORDLIST_REMOTE_URL
words = get_words(remote_url)

# Layout
col1, col2 = st.columns([1,2])

# ---------- Left: Suffix Search ----------
with col1:
    st.subheader("🔎 Search Suffix")
    suff = st.text_input("Suffix (e.g. ight)", value="ight")
    exact_before = st.number_input("Letters before suffix (exact count)", min_value=0, step=1, value=before_letters)
    matches_exact = find_matches(words, suff, exact_before if exact_before>0 else None)
    matches_related = [w for w in words if w.lower().endswith(suff.lower())] if suff else []

    st.markdown(f"**Exact matches:** {len(matches_exact)}  —  **Related:** {len(matches_related)}")
    st.markdown("<div style='max-height:520px; overflow:auto; padding:6px; background:#fff8e1; border-radius:6px;'>", unsafe_allow_html=True)
    display_list = matches_exact if matches_exact else matches_related
    for w in display_list[:5000]:
        st.markdown(make_highlight_html(w, suff), unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ---------- Right: Meanings & Translations ----------
with col2:
    st.subheader("📘 Meanings & Translations")

    # Quick pick + Excel download side by side
    if display_list:
        chosen = st.selectbox("Quick pick (click to load meanings):", [""] + display_list[:200], key="quick_pick")
        if chosen:
            syns = wordnet.synsets(chosen)
            data = []
            for i, syn in enumerate(syns, start=1):
                pos = POS_MAP.get(syn.pos(), syn.pos())
                eng = syn.definition()
                ta = translate_to_tamil(eng) if GoogleTranslator else ""
                data.append({"No": i, "POS": pos, "English": eng, "Tamil": ta})
            df = pd.DataFrame(data)
            towrite = BytesIO()
            with pd.ExcelWriter(towrite, engine="xlsxwriter") as writer:
                df.to_excel(writer, index=False, sheet_name="Meanings")
                writer.save()
            towrite.seek(0)
            st.download_button("📥 Download Excel", towrite, file_name=f"{chosen}_meanings.xlsx", key="excel_download")

            # Show meanings below
            if not syns:
                st.info("No WordNet meanings found.")
            else:
                rows = []
                for i, syn in enumerate(syns, start=1):
                    pos = POS_MAP.get(syn.pos(), syn.pos())
                    eng = syn.definition()
                    ta = translate_to_tamil(eng) if GoogleTranslator else ""
                    eng_w = "<br>".join(textwrap.wrap(eng, WRAP_EN))
                    ta_w = "<br>".join(textwrap.wrap(ta, WRAP_TA)) if ta else ""
                    rows.append((str(i), pos, eng_w, ta_w))

                html = "<table style='width:100%; border-collapse:collapse;'>"
                html += "<tr style='background:#ffe0b2'><th style='padding:8px'>No</th><th>POS</th><th>English</th><th>Tamil</th></tr>"
                for no,pos,eng_w,ta_w in rows:
                    html += f"<tr><td style='padding:8px;border-bottom:1px solid #eee'>{no}</td>"
                    html += f"<td style='padding:8px;border-bottom:1px solid #eee'>{pos}</td>"
                    html += f"<td style='padding:8px;border-bottom:1px solid #eee'>{eng_w}</td>"
                    html += f"<td style='padding:8px;border-bottom:1px solid #eee'>{ta_w}</td></tr>"
                html += "</table>"
                st.markdown(html, unsafe_allow_html=True)
    else:
        st.info("No words to select. Please search for a suffix first.")

# Footer tip
st.markdown("<div style='margin-top:12px; color:#555'>Tip: Use short suffixes (like 'ight') and 'Letters before suffix' to narrow results. Add words using the sidebar.</div>", unsafe_allow_html=True)


