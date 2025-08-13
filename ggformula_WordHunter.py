# app_streamlit_suffix_kids.py
import streamlit as st
import pandas as pd
import textwrap
from pathlib import Path
from io import BytesIO
from deep_translator import GoogleTranslator
from nltk.corpus import wordnet
import nltk

# 🔹 NLTK Data
nltk.download('wordnet')
nltk.download('omw-1.4')

# ---------- CONFIG ----------
st.set_page_config(page_title="Suffix Learner", layout="wide")
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
            if before_letters is None or before_letters==0:
                matched.append(w)
            else:
                before_part = w[:-len(suf)]
                if len(before_part) == before_letters:
                    matched.append(w)
    matched.sort(key=len)
    return matched

def make_highlight_html(word, suf):
    if suf and word.lower().endswith(suf.lower()):
        p = word[:-len(suf)]
        s = word[-len(suf):]
        return f"<div style='font-size:20px; padding:6px;'><span>{p}</span><span style='color:#ff6f61; font-weight:700'>{s}</span></div>"
    else:
        return f"<div style='font-size:20px; padding:6px;'>{word}</div>"

# ---------- UI ----------
st.markdown("""
<style>
.app-header {background: linear-gradient(90deg,#ffecd2,#fcb69f); padding: 16px; border-radius: 10px;}
.word-box {background:#fff8dc; border-radius:8px; padding:8px; margin-bottom:4px; box-shadow: 1px 1px 4px rgba(0,0,0,0.1);}
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='app-header'><h1 style='margin:0'>🎈 Suffix Learner — Fun with Words</h1><small>Find words by suffix, see English meanings & Tamil translations</small></div>", unsafe_allow_html=True)
st.write(" ")

# ---------- Input ----------
suffix = st.text_input("Enter a word suffix (like 'ight'):")
before_letters = st.number_input("Letters before suffix (0 for any):", min_value=0, step=1, value=0)

# ---------- Load words from WordNet ----------
all_words = list(set(wordnet.all_lemma_names()))

if suffix:
    matches = find_matches(all_words, suffix, before_letters)
    st.write(f"### 🔎 Found {len(matches)} words")
    st.markdown("<div style='max-height:500px; overflow:auto;'>", unsafe_allow_html=True)
    for w in matches[:500]:
        st.markdown(make_highlight_html(w, suffix), unsafe_allow_html=True)
    if len(matches)>500:
        st.info("Showing first 500 words. Narrow suffix or before-letters for more precise results.")
    st.markdown("</div>", unsafe_allow_html=True)

# ---------- Select a word for meanings ----------
st.subheader("📘 Meanings & Tamil Translations")
query_params = st.experimental_get_query_params()
selected_word = st.text_input("Type or pick a word:", value=query_params.get("selected", [""])[0] if query_params else "")

if selected_word:
    syns = wordnet.synsets(selected_word)
    if not syns:
        st.info("No WordNet meanings found for this word.")
    else:
        rows = []
        for i, syn in enumerate(syns, start=1):
            pos = POS_MAP.get(syn.pos(), syn.pos())
            eng = syn.definition()
            ta = translate_to_tamil(eng)
            eng_w = "<br>".join(textwrap.wrap(eng, WRAP_EN))
            ta_w = "<br>".join(textwrap.wrap(ta, WRAP_TA)) if ta else ""
            rows.append((str(i), pos, eng_w, ta_w))
        html = "<table style='width:100%; border-collapse:collapse;'>"
        html += "<tr style='background:#ffe0b2'><th>No</th><th>POS</th><th>English</th><th>Tamil</th></tr>"
        for no,pos,eng_w,ta_w in rows:
            html += f"<tr><td style='padding:6px;border-bottom:1px solid #eee'>{no}</td>"
            html += f"<td style='padding:6px;border-bottom:1px solid #eee'>{pos}</td>"
            html += f"<td style='padding:6px;border-bottom:1px solid #eee'>{eng_w}</td>"
            html += f"<td style='padding:6px;border-bottom:1px solid #eee'>{ta_w}</td></tr>"
        html += "</table>"
        st.markdown(html, unsafe_allow_html=True)

        # Export to Excel
        towrite = BytesIO()
        df = pd.DataFrame([{"No": i+1, "POS": POS_MAP.get(s.pos(), s.pos()), 
                            "English": s.definition(), 
                            "Tamil": translate_to_tamil(s.definition())} for i,s in enumerate(syns)])
        with pd.ExcelWriter(towrite, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Meanings")
            writer.save()
        towrite.seek(0)
        st.download_button("📥 Download Excel", towrite, file_name=f"{selected_word}_meanings.xlsx")
