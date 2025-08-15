# app_streamlit_suffix_toggle_translate_parallel_new_design.py
import streamlit as st
import pandas as pd
from io import BytesIO
from deep_translator import GoogleTranslator
from nltk.corpus import wordnet
import nltk
from concurrent.futures import ThreadPoolExecutor

# Download WordNet data (only once)
nltk.download('wordnet')
nltk.download('omw-1.4')
# Streamlit page config
st.set_page_config(page_title="சொல் தேடல்", layout="wide")

# POS mapping in Tamil
POS_MAP = {
    'n': 'பெயர்ச்சொல்',
    'v': 'வினைச்சொல்',
    'a': 'விளிப்பெயர்',
    's': 'விளிப்பெயர் (சாட்டிலைட்)',
    'r': 'வினையடை'
}

@st.cache_data
def get_all_wordnet_lemmas():
    """Loads all WordNet lemma names and caches them."""
    return sorted(set(wordnet.all_lemma_names()), key=lambda x: (len(x), x.lower()))

@st.cache_data(show_spinner=False)
def translate_definitions(definitions, target_lang='ta'):
    """Translates a list of definitions in parallel and caches the result."""
    total_items = len(definitions)
    progress_bar = st.progress(0, text="மொழிபெயர்க்கப்படுகிறது... தயவுசெய்து காத்திருக்கவும்.")
    
    def translate_with_progress(text, index):
        try:
            translated_text = GoogleTranslator(source='auto', target=target_lang).translate(text)
            progress_bar.progress((index + 1) / total_items, text=f"மொழிபெயர்க்கப்படுகிறது... {index + 1}/{total_items}")
            return translated_text
        except Exception:
            return "மொழிபெயர்ப்பு தோல்வியடைந்தது."

    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(translate_with_progress, definitions, range(total_items)))
    
    progress_bar.empty()
    return results

# Find matching words
def find_matches(words: list, suffix: str, before_letters: int):
    """Finds words ending with a specific suffix, with an optional length constraint."""
    suf = suffix.lower()
    matched = []
    if not suf:
        return []
    
    for w in words:
        if w.lower().endswith(suf):
            word_length_before_suffix = len(w) - len(suf)
            if before_letters == 0 or word_length_before_suffix == before_letters:
                matched.append(w)
    return matched

def get_word_definitions(word_list: list):
    """Fetches all definitions for a list of words from WordNet."""
    data_rows = []
    for word in word_list:
        syns = wordnet.synsets(word)
        if not syns:
            data_rows.append({"சொல்": word, "சொல் வகை": "-", "ஆங்கிலம்": "No definition found."})
        else:
            for syn in syns:
                data_rows.append({
                    "சொல்": word,
                    "சொல் வகை": POS_MAP.get(syn.pos(), "பெயர்ச்சொல்"),
                    "ஆங்கிலம்": syn.definition()
                })
    return pd.DataFrame(data_rows)

def make_highlight_html(word: str, suf: str):
    """Generates HTML to highlight the suffix in a word."""
    if suf and word.lower().endswith(suf.lower()):
        prefix = word[:-len(suf)]
        suffix_part = word[-len(suf):]
        return f"<div style='font-size:20px; padding:6px;'><span>{prefix}</span><span style='color:#f44336; font-weight:700'>{suffix_part}</span></div>"
    return f"<div style='font-size:20px; padding:6px;'>{word}</div>"

# --- Main Streamlit App Layout ---
st.markdown("""
<style>
.app-header {
    background: linear-gradient(90deg, #3498db, #2ecc71);
    padding: 20px;
    border-radius: 12px;
    color: white;
    text-align: center;
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}
.main-container {
    background-color: #f0f2f6;
    padding: 30px;
    border-radius: 12px;
    margin-top: 20px;
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}
.content-box {
    background-color: #ffffff;
    padding: 20px;
    border-radius: 8px;
    border: 1px solid #e0e0e0;
    max-height: 500px;
    overflow-y: auto;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}
.st-emotion-cache-1r65d8v {
    background: #f0f2f6;
}
.st-emotion-cache-12m3106 {
    padding-left: 1rem;
    padding-right: 1rem;
}
</style>
""", unsafe_allow_html=True)

# Header with new style
st.markdown("<div class='app-header'><h1 style='margin:0'>சொல் தேடல்</h1><p>விகுதி மற்றும் அர்த்தங்களுடன் சொற்களைக் கண்டறியலாம்</p></div>", unsafe_allow_html=True)

# Main container
with st.container():
    st.markdown("<div class='main-container'>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 2], gap="large")

    with col1:
        st.subheader("🔎 சொற்களைத் தேடு")
        suffix_input = st.text_input("Suffix (உதா: 'ight')", value="ight", help="நீங்கள் தேட விரும்பும் விகுதியை உள்ளிடவும்.")
        
        all_words = get_all_wordnet_lemmas()
        matches = find_matches(all_words, suffix_input, 0)
        
        # Sort by length as the default
        matches.sort(key=len)

        st.markdown(f"**கிடைத்த மொத்த சொற்கள்:** {len(matches)}")
        
        # வார்த்தைகளை ஒரு கட்டத்திற்குள் ஸ்க்ரோல் செய்யும்படி மாற்றி அமைக்கப்பட்டுள்ளது
        st.markdown("<div class='content-box'>", unsafe_allow_html=True)
        if matches:
            for w in matches:
                st.markdown(make_highlight_html(w, suffix_input), unsafe_allow_html=True)
        else:
            st.info("முடிவுகள் எதுவும் இல்லை.")
        st.markdown("</div>", unsafe_allow_html=True)
        

    with col2:
        st.subheader("📘 சொற்களின் பொருள்கள்")
        
        if matches:
            df_export = get_word_definitions(matches)
            
            lang_choice = st.radio("அர்த்தம் காண்பிக்க:", ["English Only", "Tamil Only", "English + Tamil"])
            
            if lang_choice != "English Only":
                definitions_to_translate = df_export["ஆங்கிலம்"].tolist()
                with st.spinner("மொழிபெயர்க்கப்படுகிறது..."):
                    tamil_list = translate_definitions(definitions_to_translate)
                    df_export["தமிழ்"] = tamil_list
            else:
                df_export["தமிழ்"] = "-"

            if lang_choice == "English Only":
                df_view = df_export[["சொல்", "சொல் வகை", "ஆங்கிலம்"]]
            elif lang_choice == "Tamil Only":
                df_view = df_export[["சொல்", "சொல் வகை", "தமிழ்"]]
            else:
                df_view = df_export

            # சொற்பொருட்களை ஸ்க்ரோல் செய்யும்படி உள்ளேயே அமைத்துள்ளோம்
            st.dataframe(df_view, use_container_width=True, height=450)

            # Excel download button positioned below the dataframe
            towrite = BytesIO()
            with pd.ExcelWriter(towrite, engine="xlsxwriter") as writer:
                df_export.to_excel(writer, index=False, sheet_name="Meanings")
            towrite.seek(0)
            st.download_button(
                "📥 EXCEL SHEET-ஆக பதிவிறக்கு",
                towrite,
                file_name=f"words_with_{suffix_input}_suffix.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        else:
            st.info("இங்கே முடிவுகள் காண்பிக்கப்படும்.")
    
    st.markdown("</div>", unsafe_allow_html=True)
