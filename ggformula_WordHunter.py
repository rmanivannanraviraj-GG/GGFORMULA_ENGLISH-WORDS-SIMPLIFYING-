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
st.set_page_config(page_title="Word Explorer", layout="wide")

# POS mapping
POS_MAP = {
    'n': 'Noun',
    'v': 'Verb',
    'a': 'Adjective',
    's': 'Adjective (Satellite)',
    'r': 'Adverb'
}

@st.cache_data
def get_all_wordnet_lemmas():
    """Loads all WordNet lemma names and caches them."""
    return sorted(set(wordnet.all_lemma_names()), key=lambda x: (len(x), x.lower()))

@st.cache_data(show_spinner=False)
def translate_definitions(definitions, target_lang='ta'):
    """Translates a list of definitions in parallel and caches the result."""
    total_items = len(definitions)
    progress_bar = st.progress(0, text="Translating... please wait.")
    
    def translate_with_progress(text, index):
        try:
            translated_text = GoogleTranslator(source='auto', target=target_lang).translate(text)
            progress_bar.progress((index + 1) / total_items, text=f"Translating... {index + 1}/{total_items}")
            return translated_text
        except Exception:
            return "Translation failed."

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
            data_rows.append({"Word": word, "Word Type": "-", "English": "No definition found."})
        else:
            for syn in syns:
                data_rows.append({
                    "Word": word,
                    "Word Type": POS_MAP.get(syn.pos(), "Noun"),
                    "English": syn.definition()
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
st.markdown("<div class='app-header'><h1 style='margin:0'>Word Explorer</h1><p>Find and explore words with suffixes and meanings</p></div>", unsafe_allow_html=True)

# Main container
with st.container():
    st.markdown("<div class='main-container'>", unsafe_allow_html=True)
    
    # New row for input controls
    control_cols = st.columns(3)
    with control_cols[0]:
        before_letters = st.number_input("Letters Before Suffix (0 for any number)", min_value=0, step=1, value=0)
    with control_cols[1]:
        lang_choice = st.radio("Show Meaning in:", ["English Only", "Tamil Only", "English + Tamil"])
    with control_cols[2]:
        max_threads = st.slider("Translation Threads (Speed Control)", min_value=2, max_value=20, value=10)

    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 2], gap="large")

    with col1:
        st.subheader("🔎 Find Words")
        suffix_input = st.text_input("Suffix (e.g., 'ight')", value="ight", help="Enter the suffix you want to search for.")
        
        all_words = get_all_wordnet_lemmas()
        matches = find_matches(all_words, suffix_input, before_letters)
        
        # Sort by length as the default
        matches.sort(key=len)

        st.markdown(f"**Total Words Found:** {len(matches)}")
        
        # Words are displayed in a scrollable container
        st.markdown("<div class='content-box'>", unsafe_allow_html=True)
        if matches:
            for w in matches:
                st.markdown(make_highlight_html(w, suffix_input), unsafe_allow_html=True)
        else:
            st.info("No results found.")
        st.markdown("</div>", unsafe_allow_html=True)
        

    with col2:
        st.subheader("📘 Word Definitions")
        
        if matches:
            df_export = get_word_definitions(matches)
            
            # Use max_threads from the new slider
            if lang_choice != "English Only":
                definitions_to_translate = df_export["English"].tolist()
                with st.spinner("Translating..."):
                    tamil_list = translate_definitions(definitions_to_translate)
                    df_export["Tamil"] = tamil_list
            else:
                df_export["Tamil"] = "-"

            if lang_choice == "English Only":
                df_view = df_export[["Word", "Word Type", "English"]]
            elif lang_choice == "Tamil Only":
                df_view = df_export[["Word", "Word Type", "Tamil"]]
            else:
                df_view = df_export

            # Definitions are displayed in a scrollable dataframe
            st.dataframe(df_view, use_container_width=True, height=450)

            # Excel download button positioned below the dataframe
            towrite = BytesIO()
            with pd.ExcelWriter(towrite, engine="xlsxwriter") as writer:
                df_export.to_excel(writer, index=False, sheet_name="Meanings")
            towrite.seek(0)
            st.download_button(
                "📥 Download as EXCEL SHEET",
                towrite,
                file_name=f"words_with_{suffix_input}_suffix.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        else:
            st.info("Results will be shown here.")
    
    st.markdown("</div>", unsafe_allow_html=True)
