# app_streamlit_suffix_kids_simple.py
import streamlit as st
import pandas as pd
import textwrap
from io import BytesIO
from pathlib import Path
from deep_translator import GoogleTranslator
from nltk.corpus import wordnet
import nltk
import time

# 🔹 NLTK Data Download (cache செய்யப்பட்டது)
@st.cache_resource
def load_nltk_data():
    nltk.download('wordnet')
    nltk.download('omw-1.4')

load_nltk_data()

# ---------- CONFIG ----------
st.set_page_config(
    page_title="சொல் விளையாட்டு", 
    layout="wide",
    page_icon="🧩"
)

# எளிய வண்ணத் திட்டம்
COLORS = {
    'primary': '#3498db',
    'secondary': '#2ecc71',
    'accent': '#e74c3c',
    'background': '#f9f9f9',
    'text': '#2c3e50'
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

# ---------- UI Styling ----------
st.markdown(f"""
<style>
/* எளிமையான மற்றும் வேகமான UI */
body {{
    background-color: {COLORS['background']};
    font-family: 'Arial', sans-serif;
}}

.stApp {{
    max-width: 1200px;
    margin: 0 auto;
}}

h1, h2, h3 {{
    color: {COLORS['primary']};
}}

.stButton>button {{
    background-color: {COLORS['secondary']};
    color: white;
    border: none;
    border-radius: 8px;
    padding: 10px 20px;
    font-size: 16px;
}}

.stButton>button:hover {{
    background-color: #{COLORS['secondary']}dd;
}}

.stSelectbox>div>div>select {{
    font-size: 16px;
    padding: 10px;
}}

/* எளிமையான அட்டவணை வடிவமைப்பு */
table {{
    width: 100%;
    border-collapse: collapse;
    margin: 15px 0;
}}

th {{
    background-color: {COLORS['primary']};
    color: white;
    padding: 12px;
    text-align: left;
}}

td {{
    padding: 10px;
    border-bottom: 1px solid #ddd;
}}

tr:nth-child(even) {{
    background-color: #f2f2f2;
}}

/* சொல் முன்னிலைப்படுத்தல் */
.highlight {{
    color: {COLORS['accent']};
    font-weight: bold;
}}
</style>
""", unsafe_allow_html=True)

# தலைப்பு பகுதி
st.markdown(f"""
<div style="text-align:center; padding:20px 0;">
    <h1 style="color:{COLORS['primary']};">🧩 சொல் விளையாட்டு</h1>
    <p>சொற்களின் இறுதி எழுத்துகளைக் கண்டுபிடித்து அர்த்தங்களைத் தெரிந்துகொள்ளுங்கள்!</p>
</div>
""", unsafe_allow_html=True)

# முக்கிய பக்க வடிவமைப்பு
col1, col2 = st.columns([1, 2])

with col1:
    # தேடல் பகுதி
    st.subheader("🔍 சொற்களைத் தேடு")
    
    suffix_input = st.text_input(
        "இறுதி எழுத்துகளை உள்ளிடவும் (எ.கா. 'ing')", 
        value="ing",
        key="suffix_input"
    )
    
    before_letters = st.number_input(
        "இறுதி எழுத்துகளுக்கு முன் எத்தனை எழுத்துகள்?", 
        min_value=0, 
        step=1, 
        value=0,
        help="0 எனில் எத்தனை இருந்தாலும் பரவாயில்லை"
    )
    
    # வேகமான தேடலுக்கு progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # சொற்களை வேகமாக ஏற்றுகிறது
    with st.spinner("சொற்கள் ஏற்றப்படுகின்றன..."):
        all_words = sorted(set(wordnet.all_lemma_names()), key=lambda x: (len(x), x.lower()))
        progress_bar.progress(100)
        status_text.success("✅ சொற்கள் தயார்!")
        time.sleep(0.5)
        progress_bar.empty()
        status_text.empty()
    
    # பொருத்தமான சொற்களைக் கண்டறிதல்
    if suffix_input:
        with st.spinner("சொற்கள் தேடப்படுகின்றன..."):
            matches = find_matches(all_words, suffix_input, before_letters)
            st.success(f"**கிடைத்த சொற்கள்:** {len(matches)}")
            
            # சொற்களின் பட்டியல்
            for w in matches[:300]:  # முதல் 300 சொற்களை மட்டும் காட்டுகிறது
                if suffix_input.lower() in w.lower():
                    parts = w.rsplit(suffix_input, 1)
                    st.markdown(
                        f"{parts[0]}<span class='highlight'>{suffix_input}</span>" if len(parts) > 1 else w,
                        unsafe_allow_html=True
                    )

with col2:
    # விரைவான தேர்வு மற்றும் அர்த்தங்கள்
    st.subheader("📚 அர்த்தங்கள்")
    
    # தேர்வு பெட்டி மற்றும் டவுன்லோட் பொத்தான்
    col_select, col_download = st.columns([3, 1])
    
    with col_select:
        chosen = st.selectbox(
            "ஒரு சொல்லைத் தேர்ந்தெடுக்கவும்", 
            [""] + (matches[:200] if 'matches' in locals() else []),
            key="word_select"
        )
    
    with col_download:
        if chosen:
            towrite = BytesIO()
            syns = wordnet.synsets(chosen)
            if syns:
                data_rows = []
                for i, syn in enumerate(syns, start=1):
                    pos = "வினை" if syn.pos() == 'v' else "பெயர்" if syn.pos() == 'n' else "பெயரடை" if syn.pos() in ('a', 's') else "வினையடை"
                    eng = syn.definition()
                    ta = translate_to_tamil(eng)
                    data_rows.append({"எண்": i, "வகை": pos, "அர்த்தம்": eng, "தமிழ்": ta})
                
                df_export = pd.DataFrame(data_rows)
                with pd.ExcelWriter(towrite, engine="xlsxwriter") as writer:
                    df_export.to_excel(writer, index=False, sheet_name="Meanings")
                towrite.seek(0)
                
                st.download_button(
                    "📊 Excel-ஆக சேமிக்க", 
                    towrite, 
                    file_name=f"{chosen}_அர்த்தங்கள்.xlsx",
                    help="இந்த சொல்லின் அர்த்தங்களை Excel கோப்பாக சேமிக்க"
                )
    
    # தேர்ந்தெடுக்கப்பட்ட சொல்லின் அர்த்தங்கள்
    if chosen:
        st.markdown(f"### ✨ {chosen}")
        
        syns = wordnet.synsets(chosen)
        if not syns:
            st.info("இந்த சொல்லுக்கு அர்த்தங்கள் கிடைக்கவில்லை.")
        else:
            for i, syn in enumerate(syns, start=1):
                pos = "வினை" if syn.pos() == 'v' else "பெயர்" if syn.pos() == 'n' else "பெயரடை" if syn.pos() in ('a', 's') else "வினையடை"
                eng = syn.definition()
                ta = translate_to_tamil(eng)
                
                with st.expander(f"அர்த்தம் {i} ({pos})"):
                    st.markdown(f"**ஆங்கிலம்:** {eng}")
                    if ta:
                        st.markdown(f"**தமிழ்:** {ta}")

# அடிக்குறிப்பு
st.markdown("""
<div style="margin-top:30px; padding:15px; background:#f0f0f0; border-radius:8px; text-align:center;">
    <p>💡 உதவி: குறுகிய இறுதி எழுத்துகளை முதலில் முயற்சிக்கவும் (எ.கா 'ing', 'tion')</p>
</div>
""", unsafe_allow_html=True)
