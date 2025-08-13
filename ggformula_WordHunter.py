import streamlit as st
import pandas as pd
import textwrap
import requests
import gzip
from pathlib import Path
from io import BytesIO

# NLP libs
import nltk
from nltk.corpus import wordnet
try:
    from deep_translator import GoogleTranslator
except Exception:
    GoogleTranslator = None

# Ensure WordNet data available (downloads on first run)
nltk.download('wordnet', quiet=True)
nltk.download('omw-1.4', quiet=True)

# ---------------- Config ----------------
st.set_page_config(page_title="Word Hunter — Simple", page_icon="🔎", layout="wide")

CACHE_DIR = Path("data")
CACHE_DIR.mkdir(exist_ok=True)
CACHE_PATH = CACHE_DIR / "wordlist.txt"
CACHE_GZ_PATH = CACHE_DIR / "wordlist.txt.gz"

POS_MAP = {'n': 'Noun', 'v': 'Verb', 'a': 'Adjective', 's': 'Adjective Satellite', 'r': 'Adverb'}
WRAP_EN = 80
WRAP_TA = 100
# Page config
st.set_page_config(page_title="Word Hunter - Kids Edition", layout="wide")

# Title (fun style for kids)
st.markdown("<h1 style='text-align:center; color:#ff66b2;'>🎈 Word Hunter 🎈</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; font-size:20px; color:#444;'>Learn English words with meanings & Tamil translations</p>", unsafe_allow_html=True)

# Suffix input box (big, colorful)
suffix = st.text_input("🔍 Type any suffix:", "", help="Enter a word ending to search (Example: ing, tion, ly)")

# Get params from URL
params = st.query_params
if "suffix" in params and not suffix:
    suffix = params["suffix"]

# Sample word list (replace with your file/remote data)
word_list = ["playing", "reading", "station", "action", "lovely", "friendly", "fishing", "education", "translation", "singing"]

# Filter words
matches = [w for w in word_list if w.endswith(suffix)] if suffix else []

# Update URL params
if suffix:
    st.query_params.update({"suffix": suffix})

# Display results
if matches:
    st.markdown(f"<h3 style='color:#ff9933;'>Found {len(matches)} words!</h3>", unsafe_allow_html=True)

    table_data = []
    for word in matches:
        synsets = wordnet.synsets(word)
        eng_meaning = synsets[0].definition() if synsets else "Meaning not found"
        tamil_meaning = GoogleTranslator(source='en', target='ta').translate(eng_meaning)
        table_data.append([word, eng_meaning, tamil_meaning])

    df = pd.DataFrame(table_data, columns=["Word", "English Meaning", "Tamil Meaning"])
    
    # Wider columns for kids readability
    st.dataframe(df, use_container_width=True)

else:
    if suffix:
        st.warning("No matching words found. Try another suffix!")

# Footer
st.markdown("<hr><p style='text-align:center; color:#888;'>Made with ❤️ for kids learning</p>", unsafe_allow_html=True)

