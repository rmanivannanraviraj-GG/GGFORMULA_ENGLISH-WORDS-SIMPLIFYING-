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
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import black
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.colors import black, darkgrey

# Set default encoding to UTF-8
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
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=0.5 * inch, rightMargin=0.5 * inch, topMargin=0.5 * inch, bottomMargin=0.5 * inch)
    
    styles = getSampleStyleSheet()
    
    # Using default fonts to avoid file not found errors
    penmanship_style = ParagraphStyle('Penmanship', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=24, leading=28, textColor=black, alignment=TA_CENTER)
    
    # We will create a style for the dotted words, but ReportLab doesn't support
    # opacity directly on text, so we'll use a different font or color.
    # For this example, we'll use a slightly different style to represent 'opacity'.
    dotted_style = ParagraphStyle('Dotted', parent=styles['Normal'], fontName='Courier', fontSize=24, leading=28, textColor=darkgrey, alignment=TA_CENTER)
    normal_style = ParagraphStyle('Normal', parent=styles['Normal'], fontName='Helvetica', fontSize=12, alignment=TA_CENTER)
    
    story = []
    
    # Add Name and Date placeholder
    story.append(Paragraph("<b>Name:</b> ____________________ &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; <b>Date:</b> ____________________", styles['Normal']))
    story.append(Spacer(1, 0.5 * inch))
    
    story.append(Paragraph("<b>Handwriting Practice</b>", styles['Title']))
    story.append(Spacer(1, 0.5 * inch))
    
    words_per_page = 15
    words_to_process = words[:words_per_page * 10]
    
    for i in range(0, len(words_to_process), words_per_page):
        if i > 0:
            story.append(PageBreak())
        
        page_words = words_to_process[i:i + words_per_page]
        
        table_data = []
        
        # Create a single row for the bold words
        bold_row = [Paragraph(f"<b>{word}</b>", penmanship_style) for word in page_words]
        table_data.append(bold_row)
        
        # Create 4 more rows with the dotted/normal style
        for _ in range(4):
            clone_row = [Paragraph(word, normal_style) for word in page_words]
            table_data.append(clone_row)

        table_style = [
            ('INNERGRID', (0,0), (-1,-1), 0.25, black),
            ('BOX', (0,0), (-1,-1), 0.25, black),
            ('TOPPADDING', (0,0), (-1,-1), 10),
            ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ]

        story.append(Table(table_data, colWidths=[1.5*inch]*5, style=table_style))
        story.append(Spacer(1, 0.5 * inch))

    # Footer
    story.append(Spacer(1, 0.5 * inch))
    story.append(Paragraph("Created with G.GEORGE - BRAIN-CHILD DICTIONARY", styles['Normal']))

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
        
        # Check if matches are available to pre-fill the text area
        if st.session_state.get('search_triggered') and 'matches' in st.session_state:
            matches_to_use = "\n".join(st.session_state['matches'])
            words_input = st.text_area("Enter words for practice (one per line):", value=matches_to_use, height=150, key='words_input_form')
        else:
            words_input = st.text_area("Enter words for practice (one per line):", height=150, key='words_input_form')
        
        tracer_button = st.button(label='Generate PDF')
            
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
