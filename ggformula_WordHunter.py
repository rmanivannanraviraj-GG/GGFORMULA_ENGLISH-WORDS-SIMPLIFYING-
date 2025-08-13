# app_streamlit_suffix.py
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

# ---------- CONFIG ----------
st.set_page_config(page_title="Suffix Learner", layout="wide")
WORDLIST_REMOTE_URL = "https://drive.google.com/uc?export=download&id=<your_file_id>"  # Google Drive direct download link
CACHE_DIR = Path("data")
CACHE_DIR.mkdir(exist_ok=True)
CACHE_PATH = CACHE_DIR / "wordlist.txt"
CACHE_GZ_PATH = CACHE_DIR / "wordlist.txt.gz"

POS_MAP = {'n': 'Noun', 'v': 'Verb', 'a': 'Adjective', 's': 'Adjective Satellite', 'r': 'Adverb'}
WRAP_EN = 80
WRAP_TA = 100

# ---------- HELPERS ----------
@st.cache_data(show_spinner=False)
def ensure_wordnet():
    try:
        nltk.data.find("corpora/wordnet")
    except:
        nltk.download("wordnet")
        nltk.download("omw-1.4")

def download_remote_wordlist(url: str, dest: Path):
    resp = requests.get(url, stream=True, timeout=120)
    resp.raise_for_status()
    total = int(resp.headers.get("content-length", 0))
    chunk_size = 1024 * 1024
    with st.spinner("Downloading wordlist (first-time)..."):
        with open(dest, "wb") as f:
            downloaded = 0
            p = st.progress(0)
            for chunk in resp.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        p.progress(min(100, int(downloaded / total * 100)))
    return dest

def load_wordlist_from_path(path: Path):
    if not path.exists():
        return []
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8", errors="ignore") as f:
            words = [w.strip() for w in f if w.strip()]
    else:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            words = [w.strip() for w in f if w.strip()]
    words = sorted(set(words), key=lambda x: (len(x), x.lower()))
    return words

@st.cache_data(show_spinner=False)
def get_words(remote_url: str):
    if CACHE_PATH.exists() and CACHE_PATH.stat().st_size > 0:
        return load_wordlist_from_path(CACHE_PATH)
    if CACHE_GZ_PATH.exists() and CACHE_GZ_PATH.stat().st_size > 0:
        return load_wordlist_from_path(CACHE_GZ_PATH)
    if not remote_url:
        return []
    dest = CACHE_GZ_PATH if remote_url.endswith(".gz") else CACHE_PATH
    try:
        download_remote_wordlist(remote_url, dest)
    except Exception as e:
        st.error(f"Failed to download wordlist: {e}")
        return []
    return load_wordlist_from_path(dest)

@st.cache_data(show_spinner=False)
def translate_to_tamil(text: str):
    try:
        return GoogleTranslator(source='auto', target='ta').translate(text)
    except:
        return ""

def find_matches(words, suffix, before_letters):
    suf = suffix.lower()
    matched = []
    for w in words:
        if w.lower().endswith(suf):
            if before_letters is None or len(w[:-len(suf)]) == before_letters:
                matched.append(w)
    matched.sort()
    return matched

def make_highlight_html(word, suf):
    if suf and word.lower().endswith(suf.lower()):
        p = word[:-len(suf)]
        s = word[-len(suf):]
        return f"<div style='font-size:20px; padding:6px;'><span>{p}</span><span style='color:#e53935; font-weight:700'>{s}</span></div>"
    return f"<div style='font-size:20px; padding:6px;'>{word}</div>"

# ---------- UI ----------
ensure_wordnet()

st.markdown("""
<style>
.app-header {background: linear-gradient(90deg,#ffecd2,#fcb69f); padding: 12px; border-radius: 8px;}
.word-box {background:#fff; border-radius:6px; padding:8px; margin-bottom:6px;}
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='app-header'><h1 style='margin:0'>🎈 Suffix Learner — Fun with Words</h1><small>Find words by suffix, see English meanings & Tamil translations</small></div>", unsafe_allow_html=True)
st.write(" ")

# Sidebar
with st.sidebar:
    st.header("🔧 Settings")
    remote_input = st.text_input("Remote wordlist URL", value=WORDLIST_REMOTE_URL)
    before_letters = st.number_input("Letters before suffix (exact). 0 = any", min_value=0, step=1, value=1)
    st.markdown("---")
    st.header("➕ Add a new word (local)")
    add_w = st.text_input("Add word")
    if st.button("Add to local list"):
        if add_w.strip():
            CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(CACHE_PATH, "a", encoding="utf-8") as f:
                f.write("\n" + add_w.strip())
            st.success(f"Added '{add_w.strip()}' to local cache.")
        else:
            st.warning("Enter a word.")

# Load words
remote_url = remote_input.strip() or WORDLIST_REMOTE_URL
words = get_words(remote_url)

# Columns
col1, col2 = st.columns([1,2])

# Left: Search
with col1:
    st.subheader("🔎 Search")
    suff = st.text_input("Suffix (e.g. ight)", value="ight")
    exact_before = st.number_input("Letters before suffix (exact count)", min_value=0, step=1, value=before_letters)
    search_clicked = st.button("Search")

    if suff:
        matches_exact = find_matches(words, suff, exact_before if exact_before>0 else None)
        matches_related = [w for w in words if w.lower().endswith(suff.lower())]
        matches_exact.sort()
        matches_related.sort()

        st.markdown(f"**Matches found:** {len(matches_exact)} exact — {len(matches_related)} related")
        st.markdown("<div style='max-height:520px; overflow:auto; padding:6px; background:#fff8e1; border-radius:6px;'>", unsafe_allow_html=True)
        display_list = matches_exact if matches_exact else matches_related
        for w in display_list[:5000]:
            st.markdown(make_highlight_html(w, suff), unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

# Right: Meanings & Translations
with col2:
    st.subheader("📘 Meanings & Translations")
    st.markdown("Quick pick (click to load meanings):")
    chosen = st.selectbox("Choose a word", [""] + (display_list[:200] if 'display_list' in locals() else []))

    if chosen:
        st.markdown(f"### 🔤 **{chosen}**")
        syns = wordnet.synsets(chosen)
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

            # Download Excel
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
            st.download_button("📥 Download Excel", towrite, file_name=f"{chosen}_meanings.xlsx")

st.markdown("<div style='margin-top:12px; color:#555'>Tip: Use short suffixes and 'Letters before suffix' to narrow results. Add words in sidebar. Persistent additions require updating upstream wordlist.</div>", unsafe_allow_html=True)
