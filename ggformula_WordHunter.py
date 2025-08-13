# app_streamlit_suffix_simple.py
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
    page_title="சொல் விளையாட்டு", 
    layout="wide",
    page_icon="🧒"
)

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
        return f"<span>{p}<span style='color:#FF6B6B; font-weight:700'>{s}</span></span>"
    else:
        return word

# ---------- UI Styling ----------
st.markdown("""
<style>
/* எளிமையான மற்றும் தெளிவான வடிவமைப்பு */
body {
    font-family: 'Arial', sans-serif;
    line-height: 1.6;
}

h1, h2, h3 {
    color: #2d3436;
    margin-top: 0.5em;
    margin-bottom: 0.5em;
}

/* பொத்தான் வடிவமைப்பு */
.stButton>button {
    background-color: #00b894;
    color: white;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 14px;
    border: none;
}

.stButton>button:hover {
    background-color: #55efc4;
}

/* தெரிவு பெட்டி வடிவமைப்பு */
.stSelectbox>div>div>select {
    font-size: 14px;
    padding: 8px;
}

/* அட்டவணை வடிவமைப்பு */
table {
    width: 100%;
    border-collapse: collapse;
    margin: 12px 0;
}

th {
    background-color: #74b9ff;
    color: white;
    padding: 10px;
    text-align: left;
}

td {
    padding: 10px;
    border-bottom: 1px solid #dfe6e9;
}

tr:nth-child(even) {
    background-color: #f5f5f5;
}

/* உள்ளீடு பெட்டி வடிவமைப்பு */
.stTextInput>div>div>input {
    padding: 8px;
    font-size: 14px;
}
</style>
""", unsafe_allow_html=True)

# தலைப்பு பகுதி
st.markdown("<h1 style='text-align:center; color:#2d3436;'>🧒 சொல் விளையாட்டு - Suffix Learner</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; color:#636e72;'>சொற்களின் இறுதிப் பகுதிகளைக் கண்டுபிடித்து, அர்த்தங்களைத் தெரிந்துகொள்ளுங்கள்!</p>", unsafe_allow_html=True)

# பக்கப்பட்டை (Sidebar)
with st.sidebar:
    st.header("⚙️ அமைப்புகள்")
    
    before_letters = st.number_input(
        "இறுதிப் பகுதிக்கு முன் எத்தனை எழுத்துகள்?", 
        min_value=0, 
        step=1, 
        value=0,
        help="0 எனில் எத்தனை எழுத்துகள் இருந்தாலும் பரவாயில்லை"
    )
    
    st.markdown("---")
    st.header("➕ புதிய சொல் சேர்க்க")
    add_w = st.text_input("சொல்லை இங்கே எழுதவும்", key="add_word")
    if st.button("சேர்க்க"):
        if not add_w.strip():
            st.warning("ஒரு சொல்லை எழுதவும்.")
        else:
            st.success(f"'{add_w.strip()}' சொல் சேர்க்கப்பட்டது!")

# WordNet சொற்களை ஏற்றுகிறது
ensure_wordnet()
all_words = sorted(set(wordnet.all_lemma_names()), key=lambda x: (len(x), x.lower()))

# முக்கிய பக்க வடிவமைப்பு
col1, col2 = st.columns([1, 2])

with col1:
    st.header("🔍 சொற்களைத் தேடு")
    suffix_input = st.text_input(
        "சொல்லின் இறுதிப் பகுதி (எ.கா. 'ing')", 
        value="ing",
        key="suffix_input"
    )
    
    matches = find_matches(all_words, suffix_input, before_letters)
    st.markdown(f"**கிடைத்த சொற்கள்:** {len(matches)}")
    
    # சொல் பட்டியல்
    st.markdown("<div style='max-height:500px; overflow:auto; margin-top:10px;'>", unsafe_allow_html=True)
    for w in matches[:5000]:
        st.markdown(make_highlight_html(w, suffix_input), unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.header("🔁 விரைவான தேர்வு")
    chosen = st.selectbox(
        "ஒரு சொல்லைத் தேர்ந்தெடுக்கவும்", 
        [""] + matches[:200],
        key="word_select",
        label_visibility="collapsed"
    )
    
    if chosen:
        # தலைப்பு வரிசை
        col_dl, _ = st.columns([1, 4])
        with col_dl:
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
                    file_name=f"{chosen}_meanings.xlsx"
                )
        
        st.header(f"📖 {chosen} - அர்த்தங்கள்")
        
        syns = wordnet.synsets(chosen)
        if not syns:
            st.info("இந்த சொல்லுக்கு அர்த்தங்கள் கிடைக்கவில்லை.")
        else:
            # அர்த்தங்கள் அட்டவணை
            html = """
            <table>
                <tr>
                    <th>எண்</th>
                    <th>பகுபாடு</th>
                    <th>ஆங்கிலம்</th>
                    <th>தமிழ்</th>
                </tr>
            """
            
            for i, syn in enumerate(syns, start=1):
                pos = POS_MAP.get(syn.pos(), syn.pos())
                eng = syn.definition()
                ta = translate_to_tamil(eng)
                eng_wrapped = "<br>".join(textwrap.wrap(eng, WRAP_EN))
                ta_wrapped = "<br>".join(textwrap.wrap(ta, WRAP_TA)) if ta else ""
                
                html += f"""
                <tr>
                    <td>{i}</td>
                    <td>{pos}</td>
                    <td>{eng_wrapped}</td>
                    <td>{ta_wrapped}</td>
                </tr>
                """
            
            html += "</table>"
            st.markdown(html, unsafe_allow_html=True)

# அடிக்குறிப்பு
st.markdown("---")
st.markdown("<p style='text-align:center; color:#636e72;'>💡 உதவி: குறுகிய இறுதிப்பகுதிகளை (எ.கா. 'ing') பயன்படுத்தி சொற்களை எளிதாக கண்டறியலாம்</p>", unsafe_allow_html=True)
