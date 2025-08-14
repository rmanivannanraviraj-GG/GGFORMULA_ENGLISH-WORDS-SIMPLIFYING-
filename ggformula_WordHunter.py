# app_streamlit_suffix_kids_hover_final.py
import streamlit as st
import pandas as pd
import textwrap
from io import BytesIO
from pathlib import Path
from deep_translator import GoogleTranslator
from nltk.corpus import wordnet
import nltk
import time

# 🔹 NLTK Data Download
@st.cache_resource
def load_nltk_data():
    nltk.download('wordnet')
    nltk.download('omw-1.4')

load_nltk_data()

# ---------- CONFIG ----------
st.set_page_config(
    page_title="சொல் விளையாட்டு - குழந்தைகளுக்கான ஆங்கிலம்", 
    layout="wide",
    page_icon="🌈"
)

# Colors based on PSD / kid-friendly
COLORS = {
    'primary': '#4285F4',
    'secondary': '#34A853',
    'accent': '#EA4335',
    'background': '#F8F9FA',
    'text': '#FFFFFF',
    'highlight': '#FBBC05',
    'footer': '#E8EAED',
    'card': '#EA4335',
    'border': '#DADCE0'
}

# ---------- Helpers ----------
@st.cache_data(show_spinner=False)
def translate_to_tamil(text: str):
    try:
        return GoogleTranslator(source='auto', target='ta').translate(text)
    except Exception:
        return ""

@st.cache_data(show_spinner=False, max_entries=100)
def find_matches(words, suffix, before_letters):
    suf = suffix.lower()
    matched = [w for w in words if w.lower().endswith(suf) and 
              (before_letters == 0 or len(w) - len(suf) == before_letters)]
    return sorted(matched, key=len)

def get_related_words(synset):
    related = {'ஒத்த பொருள்': [], 'எதிர் பொருள்': [], 'உதாரணங்கள்': []}
    for lemma in synset.lemmas():
        if lemma.name() != synset.name().split('.')[0]:
            related['ஒத்த பொருள்'].append(lemma.name())
        for antonym in lemma.antonyms():
            related['எதிர் பொருள்'].append(antonym.name())
    if synset.examples():
        related['உதாரணங்கள்'] = synset.examples()
    return related

# ---------- Styling ----------
st.markdown(f"""
<style>
body {{ background-color: {COLORS['background']}; font-family:'Comic Sans MS', cursive; }}
.stButton>button {{ background-color:{COLORS['secondary']}; color:white; border-radius:12px; }}
.word-item:hover {{ background-color:{COLORS['highlight']}22; cursor:pointer; }}
.related-word-item:hover {{ background-color:{COLORS['highlight']}44; cursor:pointer; }}
</style>
""", unsafe_allow_html=True)

# ---------- Title ----------
st.markdown(f"<h1 style='color:{COLORS['primary']}; text-align:center;'>🌈 சொல் விளையாட்டு</h1>", unsafe_allow_html=True)

# ---------- Add word ----------
CACHE_PATH = Path("data/wordlist.txt")
CACHE_PATH.parent.mkdir(exist_ok=True, parents=True)

st.markdown("<div class='card'>", unsafe_allow_html=True)
add_col1, add_col2 = st.columns([3,1])
with add_col1:
    add_w = st.text_input("புதிய சொல்லை இங்கே எழுதவும்", key="add_word")
with add_col2:
    if st.button("சேர்க்க", key="add_button"):
        if add_w.strip():
            with open(CACHE_PATH, "a", encoding="utf-8") as f:
                f.write("\n" + add_w.strip())
            st.success(f"'{add_w.strip()}' வெற்றிகரமாக சேர்க்கப்பட்டது!")
            time.sleep(1)
            st.rerun()
st.markdown("</div>", unsafe_allow_html=True)

# ---------- Columns ----------
col1, col2 = st.columns([1,2])

# ---------- Left: Suffix search & hover ----------
with col1:
    st.markdown("<div class='card'><h3>🔍 சொற்களைத் தேடு</h3>", unsafe_allow_html=True)
    suffix_input = st.text_input("இறுதி எழுத்துகள்", value="ing", key="suffix_input")
    before_letters = st.number_input("முன் எழுத்துகள்", min_value=0, step=1, value=0)

    all_words = sorted(set(wordnet.all_lemma_names()), key=lambda x:(len(x),x.lower()))
    if suffix_input:
        matches = find_matches(all_words, suffix_input, before_letters)
        st.success(f"**கிடைத்த சொற்கள்:** {len(matches)}")
        st.markdown('<div class="word-list">', unsafe_allow_html=True)
        for w in matches[:300]:
            parts = w.rsplit(suffix_input,1)
            st.markdown(f"<div class='word-item' title='Click to see meanings'>{parts[0]}<span class='highlight'>{suffix_input}</span></div>" 
                        if len(parts)>1 else f"<div class='word-item' title='Click to see meanings'>{w}</div>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ---------- Right: Meanings & Excel ----------
with col2:
    st.markdown("<div class='card'><h3>📚 அர்த்தங்கள்</h3>", unsafe_allow_html=True)
    if 'matches' in locals() and matches:
        chosen = st.selectbox("Quick pick (click to load meanings):", [""]+matches[:200], key="quick_pick")
        if chosen:
            syns = wordnet.synsets(chosen)
            data_rows=[]
            for i, syn in enumerate(syns,start=1):
                pos = "வினை" if syn.pos()=='v' else "பெயர்" if syn.pos()=='n' else "பெயரடை" if syn.pos() in ('a','s') else "வினையடை"
                eng = syn.definition()
                ta = translate_to_tamil(eng)
                data_rows.append({"எண்":i,"வகை":pos,"ஆங்கிலம்":eng,"தமிழ்":ta})
            df_export = pd.DataFrame(data_rows)
            towrite=BytesIO()
            with pd.ExcelWriter(towrite, engine="xlsxwriter") as writer:
                df_export.to_excel(writer, index=False, sheet_name="Meanings")
            towrite.seek(0)
            st.download_button("📊 அனைத்து அர்த்தங்களையும் பதிவிறக்குக", towrite,
                               file_name=f"{chosen}_அர்த்தங்கள்.xlsx")
            
            # Word meanings
            for i, syn in enumerate(syns,start=1):
                pos = "வினை" if syn.pos()=='v' else "பெயர்" if syn.pos()=='n' else "பெயரடை" if syn.pos() in ('a','s') else "வினையடை"
                eng = syn.definition()
                ta = translate_to_tamil(eng)
                with st.expander(f"அர்த்தம் {i} ({pos})", expanded=True if i==1 else False):
                    st.markdown(f"**🌍 ஆங்கிலம்:** {eng}")
                    if ta:
                        st.markdown(f"**🇮🇳 தமிழ்:** {ta}")
            
            # Related words under selected
            if syns:
                related = get_related_words(syns[0])
                if any(related.values()):
                    st.markdown("<div class='related-words-card'><h4>🔗 தொடர்புடைய சொற்கள் & உதாரணங்கள்</h4>", unsafe_allow_html=True)
                    for k,v in related.items():
                        if v:
                            st.markdown(f"**{k}:** {' , '.join(set(v))}" if k!="உதாரணங்கள்" else "\n".join(f"- {x}" for x in v))
                    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ---------- Footer ----------
st.markdown(f"""
<div class="footer" style="color:#202124; text-align:center;">
<p>💡 குறிப்பு: குறுகிய suffix களை முதலில் முயற்சிக்கவும். இப்பயன்பாடு குழந்தைகளின் ஆங்கில கற்றலை மகிழ்ச்சியாக மாற்ற உதவும்!</p>
</div>
""", unsafe_allow_html=True)
