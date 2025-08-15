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

# Streamlit page config
st.set_page_config(page_title="Word Suffix Finder", layout="wide")
CACHE_DIR = Path("data")
CACHE_DIR.mkdir(exist_ok=True)

# POS mapping
POS_MAP = {
    'n': 'பெயர்ச்சொல்',
    'v': 'வினைச்சொல்',
    'a': 'விளிப்பெயர்',
    's': 'விளிப்பெயர் (சாட்டிலைட்)',
    'r': 'வினையடை'
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

# Highlight suffix in word
def make_highlight_html(word, suf):
    if suf and word.lower().endswith(suf.lower()):
        p = word[:-len(suf)]
        s = word[-len(suf):]
        return f"<div style='font-size:20px; padding:6px;'><span>{p}</span><span style='color:#e53935; font-weight:700'>{s}</span></div>"
    else:
        return f"<div style='font-size:20px; padding:6px;'>{word}</div>"

# CSS Styling
st.markdown("""
<style>
.app-header {background: linear-gradient(90deg,#a1c4fd,#c2e9fb); padding: 12px; border-radius: 8px;}
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("<div class='app-header'><h1 style='margin:0'>கல்வி விதைகள் முளைக்கும் இடம்</h1><small>Suffix அடிப்படையில் சொற்களைத் தேடவும், அர்த்தங்களுடன் பார்க்கவும்</small></div>", unsafe_allow_html=True)

# Sidebar settings
with st.sidebar:
    st.header("🔧 தேடுதலை எளிமையாக்கு")
    before_letters = st.number_input("இறுதிக்கு முன் உள்ள எழுத்துகள் (0 என்றால் எந்தவொரு எண்ணும்)", min_value=0, step=1, value=0)
    lang_choice = st.radio("அர்த்தம் காண்பிக்க:", ["English Only", "Tamil Only", "English + Tamil"])
    max_threads = st.slider("Translation Threads (வேக கட்டுப்பாடு)", min_value=2, max_value=20, value=10)

# Load all WordNet lemma names
all_words = sorted(set(wordnet.all_lemma_names()), key=lambda x: (len(x), x.lower()))

# Layout
col1, col2 = st.columns([1,2])

with col1:
    st.subheader("🔎 சொற்களைத் தேடு")
    suffix_input = st.text_input("Suffix (உதா: 'ight')", value="ight")
    matches = find_matches(all_words, suffix_input, before_letters)

    st.markdown(f"**கிடைத்த மொத்த சொற்கள்:** {len(matches)}")

    # இந்தக் div-க்குள் தான் ஸ்க்ரோலிங் வசதி உள்ளது.
    # max-height:520px; - அதிகபட்ச உயரம்
    # overflow-y:auto; - உயரம் தாண்டும்போது தானாகவே ஸ்க்ரோலிங் பட்டி வரும்
    st.markdown("<div style='max-height:520px; overflow-y:auto; padding:6px; background:#fff8e1; border-radius:6px;'>", unsafe_allow_html=True)
    if matches:
        for w in matches:
            st.markdown(make_highlight_html(w, suffix_input), unsafe_allow_html=True)
    else:
        st.info("முடிவுகள் எதுவும் இல்லை.")
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.subheader("📘சொற்களின் பொருள்கள்")

    if matches:
        data_rows = []
        for word in matches:
            syns = wordnet.synsets(word)
            if not syns:
                data_rows.append({"சொல்": word, "சொல் வகை": "-", "ஆங்கிலம்": "-", "தமிழ்": "-"})
            else:
                for syn in syns:
                    eng = syn.definition()
                    data_rows.append({
                        "சொல்": word,
                        "சொல் வகை": POS_MAP.get(syn.pos(), "பெயர்ச்சொல்"),
                        "ஆங்கிலம்": eng
                    })

        df_export = pd.DataFrame(data_rows)

        # Translate only if Tamil is needed
        if lang_choice != "English Only":
            tamil_list = translate_list_parallel(df_export["ஆங்கிலம்"].tolist(), max_workers=max_threads)
            df_export["தமிழ்"] = tamil_list
        else:
            df_export["தமிழ்"] = "-"

        # Filter columns
        if lang_choice == "English Only":
            df_view = df_export[["சொல்", "சொல் வகை", "ஆங்கிலம்"]]
        elif lang_choice == "Tamil Only":
            df_view = df_export[["சொல்", "சொல் வகை", "தமிழ்"]]
        else:
            df_view = df_export

        # Excel download
        towrite = BytesIO()
        with pd.ExcelWriter(towrite, engine="xlsxwriter") as writer:
            df_export.to_excel(writer, index=False, sheet_name="Meanings")
        towrite.seek(0)
        st.download_button("📥 EXCEL SHEET-ஆக பதிவிறக்கு", towrite, file_name="all_meanings.xlsx")

        st.dataframe(df_view)
    else:
        st.info("முடிவுகள் எதுவும் இல்லை.")





