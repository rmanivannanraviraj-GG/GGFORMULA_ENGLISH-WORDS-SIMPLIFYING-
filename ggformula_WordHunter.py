# app_streamlit_suffix_toggle_translate_parallel_refactored.py
import streamlit as st
import pandas as pd
from io import BytesIO
from pathlib import Path
from deep_translator import GoogleTranslator
from nltk.corpus import wordnet
import nltk
from concurrent.futures import ThreadPoolExecutor
import os

# Set NLTK data path for Streamlit Cloud deployment
# This helps with permission errors
try:
    if "STREAMLIT_CLOUD" in os.environ:
        nltk_data_dir = "/tmp/nltk_data"
        os.makedirs(nltk_data_dir, exist_ok=True)
        nltk.data.path.append(nltk_data_dir)
except Exception as e:
    st.error(f"Failed to set NLTK data path: {e}")

# Download WordNet data (only once)
try:
    nltk.data.find('corpora/wordnet')
    nltk.data.find('corpora/omw-1.4')
except (nltk.downloader.DownloadError, LookupError):
    st.info("NLTK தரவுகள் பதிவிறக்கப்படுகின்றன... இது சில நிமிடங்கள் ஆகலாம்.")
    nltk.download('wordnet', quiet=True)
    nltk.download('omw-1.4', quiet=True)

# --- Streamlit Page Configuration and Caching ---
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
    """
    Translates a list of definitions in parallel and caches the result.
    Uses a progress bar for better UX.
    """
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

# --- Core Logic Functions ---
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
    return sorted(matched, key=len)

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

# --- UI Helper Functions ---
def make_highlight_html(word: str, suf: str):
    """Generates HTML to highlight the suffix in a word."""
    if suf and word.lower().endswith(suf.lower()):
        prefix = word[:-len(suf)]
        suffix_part = word[-len(suf):]
        return f"<div style='font-size:20px; padding:6px;'><span>{prefix}</span><span style='color:#e53935; font-weight:700'>{suffix_part}</span></div>"
    return f"<div style='font-size:20px; padding:6px;'>{word}</div>"

# --- Main Streamlit App Layout ---
st.markdown("""
<style>
.app-header {
    background: linear-gradient(90deg, #a1c4fd, #c2e9fb);
    padding: 12px;
    border-radius: 8px;
    margin-bottom: 20px;
}
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='app-header'><h1 style='margin:0'>கல்வி விதைகள் முளைக்கும் இடம்</h1><small>Suffix அடிப்படையில் சொற்களைத் தேடவும், அர்த்தங்களுடன் பார்க்கவும்</small></div>", unsafe_allow_html=True)

# Sidebar for controls
with st.sidebar:
    st.header("🔧 தேடுதலை எளிமையாக்கு")
    before_letters = st.number_input(
        "இறுதிக்கு முன் உள்ள எழுத்துகள் (0 என்றால் எந்தவொரு எண்ணும்)",
        min_value=0, step=1, value=0
    )
    lang_choice = st.radio("அர்த்தம் காண்பிக்க:", ["English Only", "Tamil Only", "English + Tamil"])

# Main content layout
col1, col2 = st.columns([1, 2])

# Load data only once
all_words = get_all_wordnet_lemmas()

with col1:
    st.subheader("🔎 சொற்களைத் தேடு")
    suffix_input = st.text_input("Suffix (உதா: 'ight')", value="ight")
    
    if not suffix_input:
        st.warning("Suffix-ஐ உள்ளிடவும்.")
        matches = []
    else:
        matches = find_matches(all_words, suffix_input, before_letters)
    
    st.markdown(f"**கிடைத்த மொத்த சொற்கள்:** {len(matches)}")
    
    st.markdown("<div style='max-height:520px; overflow-y:auto; padding:6px; background:#fff8e1; border-radius:6px;'>", unsafe_allow_html=True)
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
        
        st.dataframe(df_view, use_container_width=True)
    else:
        st.info("இங்கே முடிவுகள் காண்பிக்கப்படும்.")
