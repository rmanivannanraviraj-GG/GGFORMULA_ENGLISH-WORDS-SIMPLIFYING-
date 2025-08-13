# app_streamlit_suffix_pro.py
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
    page_title="சொல் ஆய்வு கருவி", 
    layout="wide",
    page_icon="🔍"
)

POS_MAP = {'n': 'பெயர்ச்சொல்', 'v': 'வினைச்சொல்', 'a': 'பெயரடை', 's': 'பெயரடை', 'r': 'வினையடை'}
WRAP_LEN = 60  # ஒரு வரியில் அதிகபட்ச எழுத்துகள்

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
        # Length check for Google Translate API
        if len(text) > 5000:
            return "மொழிபெயர்ப்பு நீளம் அதிகம்"
        return GoogleTranslator(source='auto', target='ta').translate(text)
    except Exception as e:
        return f"மொழிபெயர்ப்பு பிழை: {str(e)}"

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

def wrap_text(text, width):
    """உரையை வரிகளாக மடிக்கும் செயல்பாடு"""
    if not text:
        return ""
    return "<br>".join(textwrap.wrap(text, width=width))

# ---------- UI Styling ----------
st.markdown("""
<style>
/* மேம்பட்ட அட்டவணை வடிவமைப்பு */
.meaning-table {
    width: 100%;
    border-collapse: collapse;
    margin: 16px 0;
    font-family: Arial, sans-serif;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.meaning-table th {
    background-color: #4a89dc;
    color: white;
    padding: 12px;
    text-align: left;
    font-weight: 600;
}

.meaning-table td {
    padding: 12px;
    border-bottom: 1px solid #e0e0e0;
    vertical-align: top;
}

.meaning-table tr:nth-child(even) {
    background-color: #f8f9fa;
}

.meaning-table tr:hover {
    background-color: #f1f5fd;
}

/* பொது வடிவமைப்பு */
.definition-block {
    line-height: 1.6;
    margin-bottom: 4px;
}

.tamil-def {
    color: #2d572c;
    font-style: italic;
}

/* உள்ளீடு பெட்டிகள் */
.stTextInput>div>div>input {
    padding: 10px;
    font-size: 14px;
}

/* தலைப்புகள் */
h2, h3 {
    color: #2c3e50;
    margin-top: 1.2em;
    margin-bottom: 0.8em;
}
</style>
""", unsafe_allow_html=True)

# தலைப்பு பகுதி
st.markdown("<h1 style='text-align:center; color:#2c3e50; margin-bottom:0.5em;'>🔍 சொல் ஆய்வு கருவி</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; color:#7f8c8d; margin-top:0;'>சொற்களின் அர்த்தங்களையும் மொழிபெயர்ப்புகளையும் ஆராயுங்கள்</p>", unsafe_allow_html=True)

# பக்கப்பட்டை (Sidebar)
with st.sidebar:
    st.header("⚙️ அமைப்புகள்")
    before_letters = st.number_input(
        "இறுதி எழுத்துகளுக்கு முன் உள்ள எழுத்துகள்", 
        min_value=0, 
        step=1, 
        value=0,
        help="சரியான எழுத்து எண்ணிக்கையை குறிப்பிடவும் (0 என்பது எந்த எண்ணையும்)"
    )
    
    st.markdown("---")
    st.header("➕ புதிய சொல் சேர்க்க")
    add_w = st.text_input("சொல்லை இங்கு உள்ளிடுக", key="add_word")
    if st.button("சேர்க்க"):
        if not add_w.strip():
            st.warning("தயவு செய்து ஒரு சொல்லை உள்ளிடவும்")
        else:
            st.success(f"'{add_w.strip()}' சேர்க்கப்பட்டது!")

# WordNet சொற்களை ஏற்றுகிறது
ensure_wordnet()
all_words = sorted(set(wordnet.all_lemma_names()), key=lambda x: (len(x), x.lower()))

# முக்கிய பக்க வடிவமைப்பு
col1, col2 = st.columns([1, 2])

with col1:
    st.header("சொல் தேடல்")
    suffix_input = st.text_input(
        "இறுதி எழுத்துத் தொடர் (எ.கா. 'tion')", 
        value="tion",
        key="suffix_input"
    )
    
    matches = find_matches(all_words, suffix_input, before_letters)
    st.markdown(f"**பொருந்திய சொற்கள்:** {len(matches)}")
    
    # சொல் பட்டியல்
    st.markdown("<div style='max-height:500px; overflow-y:auto; margin-top:12px; border:1px solid #eee; padding:8px; border-radius:4px;'>", unsafe_allow_html=True)
    for w in matches[:1000]:  # செயல்திறனுக்காக 1000 சொற்கள் மட்டும்
        st.markdown(f"<div style='padding:4px 0;'>{make_highlight_html(w, suffix_input)}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.header("சொல் விவரங்கள்")
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
                    data_rows.append({
                        "எண்": i, 
                        "பகுபாடு": pos, 
                        "ஆங்கிலம்": eng, 
                        "தமிழ்": ta
                    })
                
                df_export = pd.DataFrame(data_rows)
                with pd.ExcelWriter(towrite, engine="xlsxwriter") as writer:
                    df_export.to_excel(writer, index=False, sheet_name="Meanings")
                towrite.seek(0)
                st.download_button(
                    "📊 Excel-ஆக எடுக்க", 
                    towrite, 
                    file_name=f"{chosen}_meanings.xlsx",
                    help="இந்த சொல்லின் அர்த்தங்களை Excel கோப்பாக சேமிக்க"
                )
        
        st.subheader(f"'{chosen}' - விரிவான அர்த்தங்கள்")
        
        syns = wordnet.synsets(chosen)
        if not syns:
            st.info("இந்த சொல்லுக்கு வரையறைகள் கிடைக்கவில்லை")
        else:
            # மேம்பட்ட அர்த்தங்கள் அட்டவணை
            html = """
            <table class="meaning-table">
                <thead>
                    <tr>
                        <th style="width:5%">எண்</th>
                        <th style="width:15%">சொல் வகை</th>
                        <th style="width:40%">ஆங்கில வரையறை</th>
                        <th style="width:40%">தமிழ் மொழிபெயர்ப்பு</th>
                    </tr>
                </thead>
                <tbody>
            """
            
            for i, syn in enumerate(syns, start=1):
                pos = POS_MAP.get(syn.pos(), syn.pos())
                eng = syn.definition()
                ta = translate_to_tamil(eng)
                
                # உரையை வரிகளாக மடிக்கும் பகுதி
                eng_wrapped = wrap_text(eng, WRAP_LEN)
                ta_wrapped = wrap_text(ta, WRAP_LEN) if ta else "மொழிபெயர்ப்பு இல்லை"
                
                html += f"""
                <tr>
                    <td>{i}</td>
                    <td>{pos}</td>
                    <td><div class="definition-block">{eng_wrapped}</div></td>
                    <td><div class="definition-block tamil-def">{ta_wrapped}</div></td>
                </tr>
                """
            
            html += "</tbody></table>"
            st.markdown(html, unsafe_allow_html=True)

# அடிக்குறிப்பு
st.markdown("---")
st.markdown("<p style='text-align:center; color:#7f8c8d; font-size:0.9em;'>💡 உதவி: துல்லியமான முடிவுகளுக்கு குறுகிய இறுதி எழுத்துத் தொடர்களை பயன்படுத்தவும்</p>", unsafe_allow_html=True)
