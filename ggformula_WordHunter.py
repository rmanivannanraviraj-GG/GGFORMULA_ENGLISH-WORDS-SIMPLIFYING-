import streamlit as st
import pandas as pd
from io import BytesIO
from pathlib import Path
from deep_translator import GoogleTranslator
from nltk.corpus import wordnet
import nltk
from concurrent.futures import ThreadPoolExecutor
import sys

# For PDF generation
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import black
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Set default encoding to UTF-8
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# Download WordNet data (only once)
nltk.download('wordnet')
nltk.download('omw-1.4')

# --- Register custom fonts ---
try:
    pdfmetrics.registerFont(TTFont('KGPrimaryPenmanship', 'KGPrimaryPenmanship.ttf'))
    pdfmetrics.registerFont(TTFont('KGPrimaryDots', 'KGPrimaryDots.ttf'))
except:
    st.error("Font files not found. Please ensure 'KGPrimaryPenmanship.ttf' and 'KGPrimaryDots.ttf' are in the same directory.")
    
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

# Function to create the PDF content
def create_pdf_content(words):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=1 * inch, rightMargin=1 * inch, topMargin=1 * inch, bottomMargin=1 * inch)
    
    styles = getSampleStyleSheet()
    
    # Custom style for the Penmanship font
    penmanship_style = ParagraphStyle('Penmanship', parent=styles['Normal'], fontName='KGPrimaryPenmanship', fontSize=36, leading=40, textColor=black)
    
    # Custom style for the Dots font
    dots_style = ParagraphStyle('Dots', parent=styles['Normal'], fontName='KGPrimaryDots', fontSize=36, leading=40, textColor=black)
    
    story = []
    
    # Header for the PDF
    story.append(Paragraph("<b>Handwriting Practice</b>", styles['Title']))
    story.append(Spacer(1, 0.5 * inch))
    
    for word in words:
        # Add the first line with the Penmanship font
        story.append(Paragraph(word, penmanship_style))
        story.append(Spacer(1, 0.2 * inch))
        
        # Add the remaining lines with the Dots font
        for _ in range(5): # Repeat 5 times to fill the page
            story.append(Paragraph(word, dots_style))
            story.append(Spacer(1, 0.2 * inch))
        
        story.append(Spacer(1, 0.5 * inch))

    doc.build(story)
    return buffer.getvalue()


# --- Main Streamlit App Layout ---
# Header
st.markdown("<div class='app-header'><h1 style='margin:0'>BRAIN-CHILD DICTIONARY</h1><small>Learn spellings and master words with suffixes and meanings</small></div>", unsafe_allow_html=True)

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

    st.markdown("---")
    st.subheader("📝 Word Tracer Generator")
    
    words_input = st.text_area("Enter words for practice (one per line):", height=150)
    
    if words_input:
        words_for_tracer = [word.strip() for word in words_input.split('\n') if word.strip()]
        if words_for_tracer:
            pdf_data = create_pdf_content(words_for_tracer)
            st.download_button(
                label="Download Practice Sheet as PDF",
                data=pdf_data,
                file_name="word_tracer_sheet.pdf",
                mime="application/pdf"
            )

