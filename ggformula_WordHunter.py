# app_streamlit_suffix_ready_kids.py
import streamlit as st
import pandas as pd
import textwrap
from io import BytesIO
from pathlib import Path
from deep_translator import GoogleTranslator
from nltk.corpus import wordnet
import nltk

# 🔹 NLTK Data Download
nltk.download('wordnet')
nltk.download('omw-1.4')

# ---------- CONFIG ----------
st.set_page_config(
    page_title="சொல் விளையாட்டு - Suffix Learner", 
    layout="wide",
    page_icon="🧒"
)

CACHE_DIR = Path("data")
CACHE_DIR.mkdir(exist_ok=True)
CACHE_PATH = CACHE_DIR / "wordlist.txt"

POS_MAP = {'n': 'பெயர்ச்சொல்', 'v': 'வினைச்சொல்', 'a': 'பெயரடை', 's': 'பெயரடை', 'r': 'வினையடை'}
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
        return f"<div style='font-size:20px; padding:6px;'><span>{p}</span><span style='color:#FF6B6B; font-weight:700'>{s}</span></div>"
    else:
        return f"<div style='font-size:20px; padding:6px;'>{word}</div>"

# ---------- UI Styling ----------
st.markdown("""
<style>
/* குழந்தைகளுக்கான வண்ணங்கள் மற்றும் எளிய வடிவமைப்பு */
.app-header {
    background: linear-gradient(90deg,#74b9ff,#a29bfe); 
    padding: 16px; 
    border-radius: 12px;
    color: white;
    text-align: center;
}

.kid-card {
    background:#fff9f9; 
    border-radius:12px; 
    padding:16px; 
    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    border: 2px solid #ffeaa7;
}

.word-box {
    background:#fff; 
    border-radius:8px; 
    padding:10px; 
    margin-bottom:8px;
    border: 1px solid #dfe6e9;
}

/* பெரிய எழுத்துருக்கள் மற்றும் எளிதான வாசிப்பு */
body {
    font-family: 'Comic Sans MS', cursive, sans-serif;
}

h1, h2, h3, h4 {
    color: #2d3436;
}

/* பொத்தான் வடிவமைப்பு */
.stButton>button {
    background-color: #00b894;
    color: white;
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 16px;
}

.stButton>button:hover {
    background-color: #55efc4;
    color: white;
}

/* தெரிவு பெட்டி வடிவமைப்பு */
.stSelectbox>div>div>select {
    font-size: 16px;
    padding: 10px;
    border-radius: 8px;
}
</style>
""", unsafe_allow_html=True)

# தலைப்பு பகுதி
st.markdown("""
<div class='app-header'>
    <h1 style='margin:0; color:white'>🧒 சொல் விளையாட்டு - Suffix Learner</h1>
    <p style='margin:0; font-size:18px'>சொற்களின் இறுதிப் பகுதிகளைக் கண்டுபிடித்து, அர்த்தங்களைத் தெரிந்துகொள்ளுங்கள்!</p>
</div>
""", unsafe_allow_html=True)

st.write("")

# பக்கப்பட்டை (Sidebar)
with st.sidebar:
    st.markdown("""
    <div class='kid-card'>
        <h3>⚙️ அமைப்புகள்</h3>
    """, unsafe_allow_html=True)
    
    before_letters = st.number_input(
        "இறுதிப் பகுதிக்கு முன் எத்தனை எழுத்துகள் இருக்க வேண்டும்?", 
        min_value=0, 
        step=1, 
        value=0,
        help="0 எனில் எத்தனை எழுத்துகள் இருந்தாலும் பரவாயில்லை"
    )
    
    st.markdown("---")
    
    st.markdown("""
    <h3>➕ புதிய சொல் சேர்க்க</h3>
    <p>உங்களுக்குத் தெரிந்த புதிய சொல்லைச் சேர்க்கவும்</p>
    """, unsafe_allow_html=True)
    
    add_w = st.text_input("சொல்லை இங்கே எழுதவும்", key="add_word")
    if st.button("சேர்க்க"):
        if not add_w.strip():
            st.warning("ஒரு சொல்லை எழுதவும்.")
        else:
            CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(CACHE_PATH, "a", encoding="utf-8") as f:
                f.write("\n" + add_w.strip())
            st.success(f"'{add_w.strip()}' சொல் சேர்க்கப்பட்டது!")

# WordNet சொற்களை ஏற்றுகிறது
ensure_wordnet()
all_words = sorted(set(wordnet.all_lemma_names()), key=lambda x: (len(x), x.lower()))

# முக்கிய பக்க வடிவமைப்பு
col1, col2 = st.columns([1, 2])

with col1:
    st.markdown("""
    <div class='kid-card'>
        <h2>🔍 சொற்களைத் தேடு</h2>
    """, unsafe_allow_html=True)
    
    suffix_input = st.text_input(
        "சொல்லின் இறுதிப் பகுதியை உள்ளிடவும் (எ.கா. 'ing')", 
        value="ing",
        key="suffix_input"
    )
    
    matches = find_matches(all_words, suffix_input, before_letters)
    
    st.markdown(f"**கிடைத்த சொற்கள்:** {len(matches)}")
    
    st.markdown("""
    <div style='max-height:520px; overflow:auto; padding:10px; background:#f7f1e3; border-radius:10px; border: 2px solid #fdcb6e;'>
    """, unsafe_allow_html=True)
    
    for w in matches[:5000]:
        st.markdown(make_highlight_html(w, suffix_input), unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)  # kid-card close

with col2:
    st.markdown("""
    <div class='kid-card'>
        <h2>🔁 விரைவான தேர்வு</h2>
        <p>சொல்லைத் தேர்ந்தெடுத்து அர்த்தங்களைப் பார்க்கவும்</p>
    """, unsafe_allow_html=True)
    
    chosen = st.selectbox(
        "ஒரு சொல்லைத் தேர்ந்தெடுக்கவும்", 
        [""] + matches[:200],
        key="word_select",
        label_visibility="collapsed"
    )
    
    st.markdown("</div>", unsafe_allow_html=True)  # kid-card close
    
    if chosen:
        # தலைப்பு வரிசை - Download பொத்தான் மற்றும் Meanings & Translations
        col_header1, col_header2 = st.columns([1, 4])
        
        with col_header1:
            # Excel ஏற்றுமதி
            towrite = BytesIO()
            syns = wordnet.synsets(chosen)
            if syns:
                data_rows = []
                for i, syn in enumerate(syns, start=1):
                    pos = POS_MAP.get(syn.pos(), syn.pos())
                    eng = syn.definition()
                    ta = translate_to_tamil(eng)
                    data_rows.append({"எண்": i, "பகுபாடு": pos, "ஆங்கிலம்": eng, "தமிழ்": ta})
                
                df_export = pd.DataFrame(data_rows)
                with pd.ExcelWriter(towrite, engine="xlsxwriter") as writer:
                    df_export.to_excel(writer, index=False, sheet_name="Meanings")
                towrite.seek(0)
                st.download_button(
                    "📝 Excel-ஆக சேமிக்க", 
                    towrite, 
                    file_name=f"{chosen}_meanings.xlsx",
                    help="இந்த சொல்லின் அர்த்தங்களை Excel கோப்பாக சேமிக்க"
                )
        
        with col_header2:
            st.markdown("""
            <div class='kid-card'>
                <h2>📖 அர்த்தங்கள் மற்றும் மொழிபெயர்ப்புகள்</h2>
            """, unsafe_allow_html=True)
        
        # சொல் விவரங்கள்
        st.markdown(f"### ✨ **{chosen}**")
        
        syns = wordnet.synsets(chosen)
        if not syns:
            st.info("இந்த சொல்லுக்கு WordNet-ல் அர்த்தங்கள் கிடைக்கவில்லை.")
        else:
            html = """
            <div style='border-radius:10px; overflow:hidden; box-shadow:0 2px 8px rgba(0,0,0,0.1);'>
                <table style='width:100%; border-collapse:collapse;'>
                    <tr style='background:#74b9ff; color:white;'>
                        <th style='padding:12px; text-align:left;'>எண்</th>
                        <th style='padding:12px; text-align:left;'>பகுபாடு</th>
                        <th style='padding:12px; text-align:left;'>ஆங்கிலம்</th>
                        <th style='padding:12px; text-align:left;'>தமிழ்</th>
                    </tr>
            """
            
            for i, syn in enumerate(syns, start=1):
                pos = POS_MAP.get(syn.pos(), syn.pos())
                eng = syn.definition()
                ta = translate_to_tamil(eng)
                eng_wrapped = "<br>".join(textwrap.wrap(eng, WRAP_EN))
                ta_wrapped = "<br>".join(textwrap.wrap(ta, WRAP_TA)) if ta else ""
                
                row_color = "#ffffff" if i % 2 == 1 else "#f5f5f5"
                
                html += f"""
                <tr style='background:{row_color};'>
                    <td style='padding:12px; border-bottom:1px solid #dfe6e9;'>{i}</td>
                    <td style='padding:12px; border-bottom:1px solid #dfe6e9;'>{pos}</td>
                    <td style='padding:12px; border-bottom:1px solid #dfe6e9;'>{eng_wrapped}</td>
                    <td style='padding:12px; border-bottom:1px solid #dfe6e9;'>{ta_wrapped}</td>
                </tr>
                """
            
            html += "</table></div>"
            st.markdown(html, unsafe_allow_html=True)
            
            st.markdown("</div>", unsafe_allow_html=True)  # kid-card close

# அடிக்குறிப்பு
st.markdown("""
<div style='margin-top:24px; padding:12px; background:#f5f6fa; border-radius:8px; text-align:center; color:#636e72;'>
    <p style='margin:0; font-size:16px;'>💡 உதவி: குறுகிய இறுதிப்பகுதிகளை (எ.கா. 'ing') பயன்படுத்தி சொற்களை எளிதாக கண்டறியலாம். புதிய சொற்களை பக்கப்பட்டையில் சேர்க்கலாம்.</p>
</div>
""", unsafe_allow_html=True)
