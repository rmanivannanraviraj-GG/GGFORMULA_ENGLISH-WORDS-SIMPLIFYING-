import streamlit as st
import pandas as pd
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import red, blue, black

# --- Streamlit App ---
st.set_page_config(page_title="Word Tracer Generator", layout="wide")

st.title("Word Tracer Generator")
st.write("Enter words below to create a handwriting practice sheet.")

# Get words from user
words_input = st.text_area("Enter words (one per line):", height=200)

if words_input:
    words = [word.strip() for word in words_input.split('\n') if word.strip()]
    
    # Create the PDF content
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=1 * inch, rightMargin=1 * inch, topMargin=1 * inch, bottomMargin=1 * inch)
    
    styles = getSampleStyleSheet()
    
    # Custom styles for the handwriting lines
    line_style_red = ParagraphStyle('LineRed', parent=styles['Normal'], fontSize=16, leading=16, textColor=red)
    line_style_blue = ParagraphStyle('LineBlue', parent=styles['Normal'], fontSize=16, leading=16, textColor=blue)

    # Custom style for the word to trace
    word_style = ParagraphStyle('WordStyle', parent=styles['Normal'], fontSize=20, leading=20, textColor=black, spaceAfter=20)
    
    story = []
    
    for word in words:
        # Add the word to trace
        story.append(Paragraph(f"<b>{word}</b>", word_style))
        
        # Add the four lines for practice
        for i in range(4):
            story.append(Paragraph("_" * 50, line_style_red if i == 0 or i == 3 else line_style_blue))
            story.append(Spacer(1, 0.1 * inch)) # Add a small spacer
        
        story.append(Spacer(1, 0.5 * inch)) # Add a larger space between words

    doc.build(story)
    
    # Get the PDF data from the buffer
    pdf_data = buffer.getvalue()
    
    # Download button
    st.download_button(
        label="Download Practice Sheet as PDF",
        data=pdf_data,
        file_name="word_tracer_sheet.pdf",
        mime="application/pdf"
    )

