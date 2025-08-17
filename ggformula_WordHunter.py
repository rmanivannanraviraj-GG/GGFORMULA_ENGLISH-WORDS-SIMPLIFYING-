import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase import pdfmetrics
import pandas as pd
import io
import nltk
from nltk.corpus import wordnet as wn

# =============  UI BASE =============
st.set_page_config(page_title="Brain-Child Dictionary", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    html, body, [class*="css"]  {
        font-family: 'Inter', sans-serif;
    }
    .gradient-header {
        background: linear-gradient(90deg, #ff7eb3, #ff758c);
        color: white;
        padding: 1.5rem;
        border-radius: 12px;
        text-align: center;
        font-size: 1.8rem;
        font-weight: 800;
        margin-bottom: 2rem;
    }
    .card {
        background: #fff;
        padding: 1rem;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        margin-bottom: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("<div class='gradient-header'>🌟 BRAIN-CHILD DICTIONARY 🌟</div>", unsafe_allow_html=True)


# =============  DICTIONARY EXPLORER  =============
st.subheader("📖 Dictionary Explorer")

word_input = st.text_input("Enter a word to explore", "apple")
if word_input:
    synsets = wn.synsets(word_input)
    meanings = []
    synonyms = set()

    for syn in synsets:
        meanings.append(syn.definition())
        for lemma in syn.lemmas():
            synonyms.add(lemma.name())

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("**English Meanings**")
        for m in meanings[:5]:
            st.write(f"- {m}")
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("**Synonyms**")
        for s in list(synonyms)[:10]:
            st.write(f"- {s}")
        st.markdown("</div>", unsafe_allow_html=True)

    # Tamil translation placeholder
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("**தமிழ் பொருள்** (Google Translate API இணைக்கலாம்)")
    st.write("→ (example) 'apple' = ஆப்பிள்")
    st.markdown("</div>", unsafe_allow_html=True)


# =============  PDF TRACER GENERATOR  =============
st.subheader("✍️ Tracer Sheet Generator")

words_for_pdf = st.text_area("Enter words (comma separated)", "apple, ball, cat, dog, egg, fish")
words = [w.strip() for w in words_for_pdf.split(",") if w.strip()]

if st.button("Generate Tracer PDF"):
    buffer = io.BytesIO()
    pdf = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    normal = ParagraphStyle('normal', parent=styles['Normal'], fontSize=24, leading=28)

    pdfmetrics.registerFont(UnicodeCIDFont('HeiseiMin-W3'))
    content = []

    per_page = 6
    for i, word in enumerate(words):
        content.append(Paragraph(f"<b>{word}</b>", normal))
        for _ in range(3):  # fixed clone rows
            content.append(Paragraph(f"<font color='gray'>{word}</font>", normal))
            content.append(Spacer(1, 12))
        content.append(Spacer(1, 18))
        if (i+1) % per_page == 0:
            content.append(Spacer(1, 50))

    pdf.build(content)
    buffer.seek(0)
    st.download_button("📥 Download Tracer PDF", buffer, "tracer.pdf", "application/pdf")


# =============  EXCEL EXPORT  =============
st.subheader("📂 Export Dictionary to Excel")

if st.button("Export Excel"):
    df = pd.DataFrame({
        "Word": words,
        "Meaning (EN)": ["dummy meaning"] * len(words),
        "Meaning (TA)": ["தமிழ் அர்த்தம்"] * len(words)
    })
    excel_buf = io.BytesIO()
    with pd.ExcelWriter(excel_buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    st.download_button("📥 Download Excel", excel_buf.getvalue(), "dictionary.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
