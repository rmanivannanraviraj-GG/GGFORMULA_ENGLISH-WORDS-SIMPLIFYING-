# app_streamlit_suffix_toggle_translate_parallel.py
import streamlit as st
import pandas as pd
from io import BytesIO
from pathlib import Path
from deep_translator import GoogleTranslator
from nltk.corpus import wordnet
import nltk
from concurrent.futures import ThreadPoolExecutor
import sys

# Set default encoding to UTF-8
# This fixes the 'invalid character' error
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# Download WordNet data (only once)
nltk.download('wordnet')
nltk.download('omw-1.4')

# CSS Styling with improved padding, font, and box-shadow
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap');
body {
    font-family: 'Roboto', sans-serif;
}
.app-header {
    background: linear-gradient(90deg, #3498db, #2ecc71);
    padding: 20px;
    border-radius: 12px;
    color: white;
    text-align: center;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2); /* Reduced shadow */
    margin-bottom: 20px;
}
.main-container {
    background-color: #f0f2f6;
    padding: 20px; /* Adjusted padding */
    border-radius: 12px;
    margin-top: 20px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1); /* Reduced shadow */
}
.content-box {
    background-color: #ffffff;
    padding: 15px; /* Adjusted padding */
    border-radius: 8px;
    border: 1px solid #e0e0e0;
    max-height: 450px;
    overflow-y: auto;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05); /* Reduced shadow */
}
.st-emotion-cache-1r65d8v {
    background: #f0f2f6;
}
.st-emotion-cache-12m3106 {
    padding-left: 1rem;
    padding-right: 1rem;
}
.st-emotion-cache-1f8p3j0 > div {
    /* To ensure columns are aligned at the top */
    margin-top: 0;
}
.st-emotion-cache-1f8p3j0 > div > div > h3 {
    margin-top: 0;
}
.st-emotion-cache-1f8p3j0 > div > div > p {
    margin-top: 0;
}

/* CSS for the A4 practice sheet with 4-line design */
.a4-paper {
    width: 210mm;
    height: 297mm;
    background: white;
    padding: 20mm;
    font-family: 'Times New Roman', Times, serif;
    font-size: 24px;
    line-height: 2;
    page-break-after: always;
}
.four-lines-container {
    margin-bottom: 25px;
    position: relative;
    height: 60px;
}
.line {
    position: absolute;
    width: 100%;
    border-bottom: 1px solid #ccc;
}
.line-top-red {
    top: 0;
    border-bottom: 1px solid red;
}
.line-middle-blue-1 {
    top: 15px;
    border-bottom: 1px dashed blue;
}
.line-middle-blue-2 {
    top: 30px;
    border-bottom: 1px dashed blue;
}
.line-bottom-red {
    top: 45px;
    border-bottom: 1px solid red;
}
.practice-word {
    font-size: 28px;
    font-family: 'Times New Roman', Times, serif;
    color: #333;
    position: absolute;
    top: 15px;
    left: 5px;
    z-index: 10;
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

# Find synonyms for a given word
def find_synonyms(word):
    synonyms = set()
    for syn in wordnet.synsets(word):
        for lemma in syn.lemmas():
            synonyms.add(lemma.name().replace('_', ' '))
    return list(synonyms)

# Highlight suffix in word with audio icon
def make_highlight_html(word, suf):
    if suf and word.lower().endswith(suf.lower()):
        p = word[:-len(suf)]
        s = word[-len(suf):]
        return f"<div style='font-size:20px; padding:6px;'><span>{p}</span><span style='color:#e53935; font-weight:700'>{s}</span></div>"
    else:
        return f"<div style='font-size:20px; padding:6px;'>{word}</div>"

# Function to create the practice sheet HTML
def create_practice_sheet_html(words):
    html_content = "<!DOCTYPE html><html><head><title>Word Practice Sheet</title><style>@import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap'); body{font-family:'Roboto',sans-serif;} .a4-paper{width:210mm;height:297mm;background:white;padding:20mm;} .four-lines-container{margin-bottom:20px;position:relative;height:60px;} .line{position:absolute;width:100%;border-bottom:1px solid #ccc;} .line-top-red{top:0;border-bottom:1px solid red;} .line-blue{top:15px;border-bottom:1px dashed blue;} .line-blue-2{top:30px;border-bottom:1px dashed blue;} .line-bottom-red{top:45px;border-bottom:1px solid red;} .practice-word{font-size:28px;font-family:'Times New Roman',Times,serif;color:#333;position:absolute;top:20px;left:5px;z-index:10;}</style></head><body><div class='a4-paper'>"
    html_content += "<h2 style='text-align: center;'>Word Practice Sheet</h2>"
    html_content += "<hr style='border: 1px solid black;'>"
    
    words_to_practice = words[:10]
    
    for word in words_to_practice:
        html_content += f"<div class='four-lines-container'>"
        html_content += f"<div class='line line-top-red'></div>"
        html_content += f"<div class='line line-blue'></div>"
        html_content += f"<div class='line line-blue'></div>"
        html_content += f"<div class='line line-bottom-red'></div>"
        html_content += f"<span class='practice-word'>{word}</span>"
        html_content += "</div>"
    
    html_content += "</div></body></html>"
    return html_content


# --- Main Streamlit App Layout ---
# Header
st.markdown("<div class='app-header'><h1 style='margin:0'>Word Explorer</h1><small>Learn spellings and master words with suffixes and meanings</small></div>", unsafe_allow_html=True)

# Main container
with st.container():
    st.markdown("<div class='main-container'>", unsafe_allow_html=True)
    
    # All input controls are now at the top
    col_input1, col_input2 = st.columns(2)
    with col_input1:
        before_letters = st.number_input("Letters Before Suffix (0 for any number)", min_value=0, step=1, value=0)
    with col_input2:
        lang_choice = st.selectbox("Show Meaning in:", ["English Only", "Tamil Only", "English + Tamil"])

    suffix_input = st.text_input("Suffix (e.g., 'ight')", value="ight")
    
    st.markdown("<br>", unsafe_allow_html=True)

    # Layout for the main content sections
    col1, col2 = st.columns(2, gap="large")
    
    # Calculate matches once
    
    @st.cache_data
    def get_all_words():
        """Loads and combines all words from multiple corpora."""
        words_from_wordnet = set(wordnet.all_lemma_names())
        return sorted(list(words_from_wordnet), key=lambda x: (len(x), x.lower()))

    all_words = get_all_words()
    matches = find_matches(all_words, suffix_input, before_letters)
    
    # Column 1: Find Words
    with col1:
        st.subheader("🔎 Find Words")
        # Display Total Words Found below subheader
        st.markdown(f"**Total Words Found:** {len(matches)}")
        
        if matches:
            matches_df = pd.DataFrame(matches, columns=["Word"])
            st.dataframe(matches_df, height=450, use_container_width=True)
            
            # Button to download the practice sheet
            html_content = create_practice_sheet_html(matches)
            st.download_button(
                label="Download A4 Practice Sheet",
                data=html_content,
                file_name="word_practice_sheet.html",
                mime="text/html"
            )
        else:
            st.info("No results found.")
    
    # Column 2: Word Definitions
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
