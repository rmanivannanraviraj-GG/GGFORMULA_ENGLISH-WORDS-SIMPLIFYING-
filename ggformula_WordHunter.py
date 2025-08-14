import streamlit as st
import pandas as pd
import textwrap
from io import BytesIO
from pathlib import Path
from deep_translator import GoogleTranslator
from nltk.corpus import wordnet
import nltk
import os

# Initialize NLTK data
nltk.download('wordnet')
nltk.download('omw-1.4')

# Configuration
WORDLIST_PATH = "data/wordlist.txt"  # Default path - change as needed
WRAP_EN = 80
WRAP_TA = 100
POS_MAP = {'n': 'Noun', 'v': 'Verb', 'a': 'Adjective', 's': 'Adjective Satellite', 'r': 'Adverb'}

# Custom CSS for styling
st.markdown("""
<style>
.word-container {
    height: 600px;
    overflow-y: scroll;
    padding: 10px;
    background: white;
    border-radius: 8px;
    border: 1px solid #e0e0e0;
    margin-top: 10px;
}
.highlight {
    color: #EA4335;
    font-weight: bold;
}
.meaning-card {
    padding: 15px;
    margin-bottom: 15px;
    background: white;
    border-radius: 8px;
    border: 1px solid #e0e0e0;
}
</style>
""", unsafe_allow_html=True)

# Helper functions
def load_wordlist(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    if not Path(path).exists():
        return sorted(set(wordnet.all_lemma_names()), key=lambda x: (len(x), x.lower()))
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        words = [w.strip() for w in f.read().split() if w.strip()]
    return sorted(set(words), key=lambda x: (len(x), x.lower()))

def append_word_to_file(path, word):
    with open(path, "a", encoding="utf-8") as f:
        f.write("\n" + word.strip())

def get_wordnet_meanings(word):
    syns = wordnet.synsets(word)
    meanings = []
    for i, syn in enumerate(syns, start=1):
        pos_full = POS_MAP.get(syn.pos(), syn.pos())
        eng = syn.definition()
        try:
            ta = GoogleTranslator(source='auto', target='ta').translate(eng)
        except:
            ta = ""
        meanings.append({
            "No": i,
            "POS": pos_full,
            "English": "\n".join(textwrap.wrap(eng, WRAP_EN)),
            "Tamil": "\n".join(textwrap.wrap(ta, WRAP_TA)) if ta else ""
        })
    return meanings

# Main App
def main():
    st.set_page_config(
        page_title="Suffix Search App", 
        layout="wide",
        page_icon="🔍"
    )

    # Header
    st.markdown("""
    <div style="text-align:center; background:#4285F4; padding:15px; border-radius:10px; color:white; margin-bottom:20px;">
        <h1 style="margin:0;">🔍 Suffix Search App</h1>
        <p style="margin:0;">Search words by suffix and explore meanings</p>
    </div>
    """, unsafe_allow_html=True)

    # Load wordlist
    words = load_wordlist(WORDLIST_PATH)

    # Main columns
    col1, col2 = st.columns([1, 2])

    with col1:
        # Search controls
        st.subheader("Word Search")
        suffix = st.text_input("Enter suffix:", "ing")
        before_letters = st.number_input("Letters before suffix (0 for any):", min_value=0, value=0)
        
        search_col1, search_col2 = st.columns(2)
        with search_col1:
            if st.button("Search with count"):
                matches = [w for w in words if w.lower().endswith(suffix.lower()) and 
                          (before_letters == 0 or (len(w)-len(suffix)) == before_letters)]
                st.session_state.matches = matches
        with search_col2:
            if st.button("Show all matches"):
                matches = [w for w in words if w.lower().endswith(suffix.lower())]
                st.session_state.matches = matches

        # Word list display
        st.write(f"Total words: {len(words)}")
        if 'matches' in st.session_state:
            st.write(f"Matches found: {len(st.session_state.matches)}")
            
            # Scrollable word list with highlighting
            st.markdown('<div class="word-container">', unsafe_allow_html=True)
            for word in st.session_state.matches:
                if suffix.lower() in word.lower():
                    parts = word.rsplit(suffix, 1)
                    if len(parts) > 1:
                        st.markdown(f"{parts[0]}<span class='highlight'>{suffix}</span>", unsafe_allow_html=True)
                    else:
                        st.write(word)
                else:
                    st.write(word)
            st.markdown('</div>', unsafe_allow_html=True)

        # Add word section
        st.subheader("Add New Word")
        new_word = st.text_input("Enter a new word to add:")
        if st.button("Add Word"):
            if new_word.strip():
                append_word_to_file(WORDLIST_PATH, new_word)
                st.success(f"'{new_word}' added successfully!")
                st.experimental_rerun()

    with col2:
        # Meanings display
        st.subheader("Word Meanings")
        if 'matches' in st.session_state and st.session_state.matches:
            selected_word = st.selectbox("Select a word:", [""] + st.session_state.matches)
            
            if selected_word:
                meanings = get_wordnet_meanings(selected_word)
                
                if not meanings:
                    st.info("No meanings found for this word.")
                else:
                    # Display meanings in cards
                    for meaning in meanings:
                        with st.expander(f"Meaning {meaning['No']} ({meaning['POS']})", expanded=True):
                            st.markdown(f"**English:**\n{meaning['English']}")
                            if meaning['Tamil']:
                                st.markdown(f"**Tamil:**\n{meaning['Tamil']}")
                    
                    # Export to Excel
                    df = pd.DataFrame(meanings)
                    towrite = BytesIO()
                    df.to_excel(towrite, index=False, engine='xlsxwriter')
                    towrite.seek(0)
                    
                    st.download_button(
                        "Export Meanings to Excel",
                        towrite,
                        file_name=f"{selected_word}_meanings.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
        else:
            st.info("Search for words first to see meanings.")

if __name__ == "__main__":
    main()
