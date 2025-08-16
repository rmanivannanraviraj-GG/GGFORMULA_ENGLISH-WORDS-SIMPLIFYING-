import streamlit as st
import pandas as pd
from io import BytesIO
from pathlib import Path
from deep_translator import GoogleTranslator
from nltk.corpus import wordnet
import nltk
from concurrent.futures import ThreadPoolExecutor
import sys
import os

# For PDF generation
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import red, blue, black
from reportlab.graphics.shapes import Drawing, Line
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Set default encoding to UTF-8
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# Download WordNet data (only once)
nltk.download('wordnet')
nltk.download('omw-1.4')

# --- Register custom fonts with dynamic path ---
try:
    # Use the directory of the current script to locate the fonts
    script_dir = os.path.dirname(os.path.abspath(__file__))
    penmanship_font_path = os.path.join(script_dir, 'KGPrimaryPenmanship.ttf')
    dots_font_path = os.path.join(script_dir, 'KGPrimaryDots.ttf')
    
    # Check if files exist before trying to register
    if os.path.exists(penmanship_font_path) and os.path.exists(dots_font_path):
        pdfmetrics.registerFont(TTFont('KGPrimaryPenmanship', penmanship_font_path))
        pdfmetrics.registerFont(TTFont('KGPrimaryDots', dots_font_path))
    else:
        st.warning("Font files 'KGPrimaryPenmanship.ttf' and 'KGPrimaryDots.ttf' not found. Using default fonts.")
        # If fonts are not found, fallback to a simpler font
        penmanship_font_path = 'Helvetica-Bold'
        dots_font_path = 'Courier'

except Exception as e:
    st.error(f"எழுத்துருக்களை பதிவு செய்வதில் பிழை: {e}")
    penmanship_font_path = 'Helvetica-Bold'
    dots_font_path = 'Courier'

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
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    margin-bottom: 20px;
}
.main-container {
    background-color: #f0f2f6;
    padding: 20px;
    border-radius: 12px;
    margin-top: 20px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}
.content-box {
    background-color: #ffffff;
    padding: 15px;
    border-radius: 8px;
    border: 1px solid #e0e0e0;
    max-height: 450px;
    overflow-y: auto;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}
.st-emotion-cache-1r65d8v {
    background: #f0f2f6;
}
.st-emotion-cache-12m3106 {
    padding-left: 1rem;
    padding-right: 1rem;
}
.st-emotion-cache-1f8p3j0 > div {
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

# Function to create the PDF content
def create_pdf_content(words):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=1 * inch, rightMargin=1 * inch, topMargin=1 * inch, bottomMargin=1 * inch)
    
    styles = getSampleStyleSheet()
    
    try:
        penmanship_style = ParagraphStyle('Penmanship', parent=styles['Normal'], fontName='KGPrimaryPenmanship', fontSize=36, leading=40, textColor=black)
        dots_style = ParagraphStyle('Dots', parent=styles['Normal'], fontName='KGPrimaryDots', fontSize=36, leading=40, textColor=black)
    except Exception as e:
        penmanship_style = ParagraphStyle('Penmanship', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=36, leading=40, textColor=black)
        dots_style = ParagraphStyle('Dots', parent=styles['Normal'], fontName='Courier', fontSize=36, leading=40, textColor=black)

    story = []
    
    story.append(Paragraph("<b>Handwriting Practice</b>", styles['Title']))
    story.append(Spacer(1, 0.5 * inch))
    
    for word in words:
        story.append(Paragraph(word, penmanship_style))
        story.append(Spacer(1, 0.2 * inch))
        
        for _ in range(5):
            story.append(Paragraph(word, dots_style))
            story.append(Spacer(1, 0.2 * inch))
        
        story.append(Spacer(1, 0.5 * inch))

    doc.build(story)
    return buffer.getvalue()


# --- Main Streamlit App Layout ---
st.markdown("<div class='app-header'><h1 style='margin:0'>BRAIN-CHILD DICTIONARY</h1><small>Learn spellings and master words with suffixes and meanings</small></div>", unsafe_allow_html=True)

with st.container():
    st.markdown("<div class='main-container'>", unsafe_allow_html=True)
    
    col_input1, col_input2 = st.columns(2)
    with col_input1:
        before_letters = st.number_input("Letters Before Suffix (0 for any number)", min_value=0, step=1, value=0, key='before_letters_main')
    with col_input2:
        lang_choice = st.selectbox("Show Meaning in:", ["English Only", "Tamil Only", "English + Tamil"], key='lang_choice_main')

    # Layout for the main content sections
    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.subheader("🔎 Find Words")
        with st.form("find_words_form"):
            suffix_input = st.text_input("Suffix (e.g., 'ight')", value="ight", key='suffix_input_form')
            search_button = st.form_submit_button(label='Search Words')

        if search_button:
            all_words = sorted(set(wordnet.all_lemma_names()), key=lambda x: (len(x), x.lower()))
            matches = find_matches(all_words, suffix_input, before_letters)
            st.session_state['matches'] = matches
            st.session_state['search_triggered'] = True
            
            st.markdown(f"**Total Words Found:** {len(matches)}")
            
            if matches:
                matches_df = pd.DataFrame(matches, columns=["Word"])
                st.dataframe(matches_df, height=450, use_container_width=True)
            else:
                st.info("No results found.")
    
    with col2:
        st.subheader("📝 Word Tracer Generator")
        with st.form("word_tracer_form"):
            words_input = st.text_area("Enter words for practice (one per line):", height=150, key='words_input_form')
            tracer_button = st.form_submit_button(label='Generate PDF')
            
        if tracer_button:
            words_for_tracer = [word.strip() for word in words_input.split('\n') if word.strip()]
            if words_for_tracer:
                pdf_data = create_pdf_content(words_for_tracer)
                if pdf_data:
                    st.download_button(
                        label="Download Practice Sheet as PDF",
                        data=pdf_data,
                        file_name="word_tracer_sheet.pdf",
                        mime="application/pdf"
                    )

    # Word Definitions section is now below
    st.markdown("---")
    st.subheader("📘 Word Definitions")

    if st.session_state.get('search_triggered'):
        if 'matches' in st.session_state:
            matches = st.session_state['matches']
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

                if st.session_state.lang_choice_main != "English Only":
                    tamil_list = translate_list_parallel(df_export["English"].tolist(), max_workers=10)
                    df_export["Tamil"] = tamil_list
                else:
                    df_export["Tamil"] = "-"

                if st.session_state.lang_choice_main == "English Only":
                    df_view = df_export[["Word", "Word Type", "English"]]
                elif st.session_state.lang_choice_main == "Tamil Only":
                    df_view = df_export[["Word", "Word Type", "Tamil"]]
                else:
                    df_view = df_export

                st.dataframe(df_view, height=450, use_container_width=True)

                towrite = BytesIO()
                with pd.ExcelWriter(towrite, engine="xlsxwriter") as writer:
                    df_export.to_excel(writer, index=False, sheet_name="Meanings")
                towrite.seek(0)
                st.download_button("📥 Download as EXCEL SHEET", towrite, file_name="all_meanings.xlsx")
            else:
                st.info("No results found.")
        else:
            st.info("Please enter a suffix and click 'Search Words' to see definitions.")
    else:
        st.info("Please enter a suffix and click 'Search Words' to see definitions.")
    
    st.markdown("</div>", unsafe_allow_html=True)
