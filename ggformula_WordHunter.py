import streamlit as st
import pandas as pd
from pathlib import Path
from deep_translator import GoogleTranslator
import re

# ====== SETTINGS ======
DEFAULT_WORDLIST = Path("wordlist.txt")
BEFORE_LETTERS_LIMIT = 10  # max limit for before letters input
CACHE_PATH = Path("session_words.txt")

# ====== FUNCTIONS ======
def load_words(path: Path):
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return sorted(set(w.strip() for w in f if w.strip()))

def save_words(path: Path, words):
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(sorted(set(words))))

def find_matches(words, suffix, before_letters=0):
    if not suffix:
        return []
    pattern = rf"^[a-zA-Z]{{{before_letters}}}{suffix}$" if before_letters > 0 else rf"{suffix}$"
    regex = re.compile(pattern, re.IGNORECASE)
    return [w for w in words if regex.search(w)]

def make_highlight_html(word, suffix):
    idx = word.lower().rfind(suffix.lower())
    if idx == -1:
        return f"<div style='padding:2px 6px;'>{word}</div>"
    prefix = word[:idx]
    match = word[idx:idx+len(suffix)]
    suffix_part = word[idx+len(suffix):]
    return f"<div style='padding:2px 6px;'><span>{prefix}</span><span style='background:yellow; font-weight:bold'>{match}</span><span>{suffix_part}</span></div>"

def translate_to_tamil(text):
    try:
        return GoogleTranslator(source='en', target='ta').translate(text)
    except Exception:
        return ""

# ====== LOAD DEFAULT WORDS ======
all_words = load_words(DEFAULT_WORDLIST)

# ====== UI ======
st.set_page_config(page_title="Word Finder", layout="wide")
st.title("Word Finder Tool 🔍")

# Search controls
col1, col2, col3 = st.columns([2, 1, 1])
suffix_input = col1.text_input("Suffix (e.g., 'ight')", value="ight")
before_letters = col2.number_input("Before letters count", min_value=0, max_value=BEFORE_LETTERS_LIMIT, value=0)

# Find matches
matches = find_matches(all_words, suffix_input, before_letters)

# Count
st.markdown(f"**Found words:** {len(matches)}")

# Show matches
st.markdown(
    "<div style='max-height:520px; overflow:auto; padding:6px; background:#fff8e1; border-radius:6px;'>",
    unsafe_allow_html=True
)
for w in matches[:5000]:
    st.markdown(make_highlight_html(w, suffix_input), unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# Meanings & Tamil translation
if matches:
    data = []
    for w in matches:
        tamil = translate_to_tamil(w)
        data.append({"Word": w, "Tamil": tamil})
    df = pd.DataFrame(data)
    st.dataframe(df)

    # Download as Excel
    excel_path = "matched_words.xlsx"
    df.to_excel(excel_path, index=False)
    with open(excel_path, "rb") as f:
        st.download_button("📥 Download Excel", f, file_name=excel_path)
