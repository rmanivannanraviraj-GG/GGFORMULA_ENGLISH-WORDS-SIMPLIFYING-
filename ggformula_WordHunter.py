# app_streamlit_suffix_toggle_translate_parallel.py
import streamlit as st
import pandas as pd
from io import BytesIO
from pathlib import Path
from deep_translator import GoogleTranslator
from nltk.corpus import wordnet
import nltk
from concurrent.futures import ThreadPoolExecutor

# Download WordNet data (only once)
nltk.download('wordnet')
nltk.download('omw-1.4')

# CSS Styling
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
    max-height: 450px;
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

# Streamlit page config
st.set_page_config(page_title="Word Suffix Finder", layout="wide")
CACHE_DIR = Path("data")
CACHE_DIR.mkdir(exist_ok=True)

# POS mapping
POS_MAP = {
    'n': 'Noun',
    'v': 'Verb',
    'a': 'Adjective',
    's': 'Adjective (Satellite)',
    'r': 'Adverb'
}

# Cached translation
@st.cache_data(show_spinner=False)
def translate_to_tamil(text: str):
    try:
        return GoogleTranslator(source='auto', target='ta').translate(text)
    except:
        return ""

# Parallel translation wrapper
def translate_list_parallel(texts, max_workers=10):
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(translate_to_tamil, texts))
    return results

# Find matching words
def find_matches(words, suffix, before_letters):
    suf = suffix.lower()
    matched = []
    for w in words:
        if w.lower().endswith(suf):
            if before_letters == 0 or len(w) - len(suf) == before_letters:
                matched.append(w)
    matched.sort(key=len)
    return matched

# Highlight suffix in word with audio icon
def make_highlight_html(word, suf):
    if suf and word.lower().endswith(suf.lower()):
        p = word[:-len(suf)]
        s = word[-len(suf):]
        return f"<div style='font-size:20px; padding:6px;'><span>{p}</span><span style='color:#e53935; font-weight:700'>{s}</span></div>"
    else:
        return f"<div style='font-size:20px; padding:6px;'>{word}</div>"

# Header
st.markdown("<div class='app-header'><h1 style='margin:0'>Word Explorer</h1><small>Find and explore words with suffixes and meanings</small></div>", unsafe_allow_html=True)

# Main container
with st.container():
    st.markdown("<div class='main-container'>", unsafe_allow_html=True)

    # New row for input controls
    control_cols = st.columns(2)
    with control_cols[0]:
        before_letters = st.number_input("Letters Before Suffix (0 for any number)", min_value=0, step=1, value=0)
    with control_cols[1]:
        lang_choice = st.selectbox("Show Meaning in:", ["English Only", "Tamil Only", "English + Tamil"])

    st.markdown("<br>", unsafe_allow_html=True)

    # Layout
    col1, col2 = st.columns([1,2], gap="large")

    with col1:
        st.subheader("🔎 Find Words")
        suffix_input = st.text_input("Suffix (e.g., 'ight')", value="ight")
        all_words = sorted(set(wordnet.all_lemma_names()), key=lambda x: (len(x), x.lower()))
        matches = find_matches(all_words, suffix_input, before_letters)
        
        st.markdown(f"**Total Words Found:** {len(matches)}")
        
        # Display words in a scrollable table
        if matches:
            matches_df = pd.DataFrame(matches, columns=["Word"])
            st.dataframe(matches_df, height=450, use_container_width=True)
        else:
            st.info("No results found.")
        

    with col2:
        st.subheader("📘 Word Definitions")

        if matches:
            data_rows = []
            for word in matches:
                syns = wordnet.synsets(word)
                if not syns:
                    data_rows.append({"Word": word, "Word Type": "-", "English": "-", "Tamil": "-"})
                else:
                    for syn in syns:
                        eng = syn.definition()
                        data_rows.append({
                            "Word": word,
                            "Word Type": POS_MAP.get(syn.pos(), "Noun"),
                            "English": eng,
                            "Tamil": "-"
                        })

            df_export = pd.DataFrame(data_rows)

            if lang_choice != "English Only":
                tamil_list = translate_list_parallel(df_export["English"].tolist(), max_workers=10)
                df_export["Tamil"] = tamil_list
            else:
                df_export["Tamil"] = "-"

            if lang_choice == "English Only":
                df_view = df_export[["Word", "Word Type", "English"]]
            elif lang_choice == "Tamil Only":
                df_view = df_export[["Word", "Word Type", "Tamil"]]
            else:
                df_view = df_export

            st.dataframe(df_view, height=450)

            towrite = BytesIO()
            with pd.ExcelWriter(towrite, engine="xlsxwriter") as writer:
                df_export.to_excel(writer, index=False, sheet_name="Meanings")
            towrite.seek(0)
            st.download_button("📥 Download as EXCEL SHEET", towrite, file_name="all_meanings.xlsx")
        else:
            st.info("No results found.")

    st.markdown("</div>", unsafe_allow_html=True)
