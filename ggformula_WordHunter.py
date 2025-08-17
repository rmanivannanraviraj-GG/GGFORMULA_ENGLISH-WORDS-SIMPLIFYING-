# app.py
# ------------------ Imports ------------------
import os
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import streamlit as st
import pandas as pd
import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

# NLTK / WordNet
import nltk
from nltk.corpus import wordnet

# deep_translator (optional)
try:
    from deep_translator import GoogleTranslator
    HAS_TRANSLATOR = True
except Exception:
    HAS_TRANSLATOR = False

# ReportLab (PDF)
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ------------------ One-time NLTK data ------------------
# If these are already downloaded locally, this is a no-op.
try:
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('wordnet')
try:
    nltk.data.find('corpora/omw-1.4')
except LookupError:
    nltk.download('omw-1.4')

# ------------------ App Config & CSS ------------------
st.set_page_config(page_title="Brain-Child • Tracer + Dictionary Explorer", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.app-header {
  background: linear-gradient(90deg, #6a11cb, #2575fc);
  padding: 20px; border-radius: 16px; color: white; text-align: center;
  box-shadow: 0 4px 14px rgba(0,0,0,0.12); margin-bottom: 20px;
}
.card { background:#fff; border:1px solid #eee; border-radius:14px; padding:16px; box-shadow: 0 2px 8px rgba(0,0,0,0.04); }
.small { color:#666; font-size: 0.9rem; }
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='app-header'><h1 style='margin:0'>🧠 BRAIN-CHILD</h1><div>Tracing Sheet Generator + Dictionary Explorer</div></div>", unsafe_allow_html=True)

# ------------------ Utilities ------------------
CACHE_DIR = Path("data")
CACHE_DIR.mkdir(exist_ok=True)

POS_MAP = {
    'n': 'Noun',
    'v': 'Verb',
    'a': 'Adjective',
    's': 'Adjective (Satellite)',
    'r': 'Adverb'
}

@st.cache_data(show_spinner=False)
def get_all_words():
    # WordNet lemmas → unique strings
    return sorted(set(wordnet.all_lemma_names()), key=lambda x: (len(x), x.lower()))

def find_matches(words, suffix, before_letters):
    suf = suffix.lower()
    return sorted(
        [w for w in words if w.lower().endswith(suf) and (before_letters == 0 or len(w) - len(suf) == before_letters)],
        key=len
    )

def find_synonyms(word):
    syns = set()
    for syn in wordnet.synsets(word):
        for lemma in syn.lemmas():
            syns.add(lemma.name().replace('_', ' '))
    return list(syns)

def translate_to_tamil(text: str):
    if not HAS_TRANSLATOR:
        return "(translation unavailable)"
    try:
        return GoogleTranslator(source='auto', target='ta').translate(text)
    except Exception:
        return "(translation failed)"

def translate_list_parallel(texts, max_workers=min(5, os.cpu_count() or 2)):
    if not HAS_TRANSLATOR:
        return ["(translation unavailable)"] * len(texts)
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        return list(ex.map(translate_to_tamil, texts))

# Optional dotted handwriting font (if you have a TTF like KGPrimaryDots.ttf)
DO_TTF = os.path.exists("KGPrimaryDots.ttf")
if DO_TTF:
    try:
        pdfmetrics.registerFont(TTFont("Dotted", "KGPrimaryDots.ttf"))
    except Exception:
        DO_TTF = False

import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

# ------------------------
# Register extra fonts (optional for kids handwriting)
# ------------------------
FONTS = {
    "Helvetica": "Helvetica",
    "Comic Sans": "ComicSansMS.ttf",   # you need to keep this .ttf file in project folder
    "Arial": "Arial.ttf"
}

for fname in FONTS.values():
    if fname.endswith(".ttf") and os.path.exists(fname):
        pdfmetrics.registerFont(TTFont(fname.replace(".ttf",""), fname))

# ------------------------
# Register extra fonts (optional for kids handwriting)
# ------------------------
FONTS = {
    "Helvetica": "Helvetica",
    "Comic Sans": "ComicSansMS.ttf",   # you need to keep this .ttf file in project folder
    "Arial": "Arial.ttf"
}

for fname in FONTS.values():
    if fname.endswith(".ttf") and os.path.exists(fname):
        pdfmetrics.registerFont(TTFont(fname.replace(".ttf",""), fname))

# ------------------------
import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

# ------------------------
# Register extra fonts (optional for kids handwriting)
# ------------------------
FONTS = {
    "Helvetica": "Helvetica",
    "Comic Sans": "ComicSansMS.ttf",   # you need to keep this .ttf file in project folder
    "Arial": "Arial.ttf"
}

for fname in FONTS.values():
    if fname.endswith(".ttf") and os.path.exists(fname):
        pdfmetrics.registerFont(TTFont(fname.replace(".ttf",""), fname))

# ------------------------
# PDF Generator Function
# ------------------------
def create_practice_pdf(words, filename, clone_count=5, font_choice="Helvetica", margins=(50,50,50,50)):
    left, right, top, bottom = margins
    doc = SimpleDocTemplate(filename, pagesize=A4,
                            leftMargin=left, rightMargin=right,
                            topMargin=top, bottomMargin=bottom)

    story = []

    # Bold model word
    model_style = ParagraphStyle(
        'ModelWord',
        fontName=font_choice,
        fontSize=28,
        alignment=TA_CENTER,
        leading=34,
        textColor=colors.black
    )

    # Trace word (Light Grey)
    trace_style = ParagraphStyle(
        'TraceWord',
        fontName=font_choice,
        fontSize=28,
        alignment=TA_CENTER,
        leading=34,
        textColor=colors.grey
    )

    # Layout: 2-column grid (6 words per page)
    usable_width = A4[0] - (left + right)
    col_width = usable_width / 2

    for i, word in enumerate(words):
        # Model word
        story.append(Paragraph(word, model_style))
        story.append(Spacer(1, 0.2 * cm))

        # Clones
        for _ in range(clone_count):
            story.append(Paragraph(word, trace_style))
            story.append(Spacer(1, 0.2 * cm))

        # After every 2 words, add a spacer for column gap
        if (i+1) % 2 == 0:
            story.append(Spacer(1, 1.5 * cm))

        # After 6 words, new page
        if (i+1) % 6 == 0 and (i+1) < len(words):
            story.append(PageBreak())

    doc.build(story)
    return filename

# ------------------------
# Streamlit UI
# ------------------------
st.title("✏️ Kids English Word Tracer Generator")

# Sidebar Controls
st.sidebar.header("⚙️ Settings")
clone_count = st.sidebar.slider("Number of trace clones per word", 3, 10, 5)
font_choice = st.sidebar.selectbox("Font Style", list(FONTS.keys()))
margin_left = st.sidebar.slider("Left Margin", 20, 80, 50)
margin_right = st.sidebar.slider("Right Margin", 20, 80, 50)
margin_top = st.sidebar.slider("Top Margin", 20, 100, 50)
margin_bottom = st.sidebar.slider("Bottom Margin", 20, 100, 50)

# Input words
words_input = st.text_area("Enter words (comma separated)", "Apple, Ball, Cat, Dog, Egg, Fish")

words = [w.strip() for w in words_input.split(",") if w.strip()]

if st.button("Generate Practice PDF"):
    output_file = "practice_sheet.pdf"
    create_practice_pdf(words, output_file,
                        clone_count=clone_count,
                        font_choice=font_choice if font_choice=="Helvetica" else font_choice.replace(".ttf",""),
                        margins=(margin_left, margin_right, margin_top, margin_bottom))
    with open(output_file, "rb") as f:
        st.download_button("📥 Download PDF", f, file_name=output_file)


# ------------------------
# Streamlit UI
# ------------------------
st.title("✏️ Kids English Word Tracer Generator")

# Sidebar Controls
st.sidebar.header("⚙️ Settings")
clone_count = st.sidebar.slider("Number of trace clones per word", 3, 10, 5)
font_choice = st.sidebar.selectbox("Font Style", list(FONTS.keys()))
margin_left = st.sidebar.slider("Left Margin", 20, 80, 50)
margin_right = st.sidebar.slider("Right Margin", 20, 80, 50)
margin_top = st.sidebar.slider("Top Margin", 20, 100, 50)
margin_bottom = st.sidebar.slider("Bottom Margin", 20, 100, 50)

# Input words
words_input = st.text_area("Enter words (comma separated)", "Apple, Ball, Cat, Dog, Egg, Fish")

words = [w.strip() for w in words_input.split(",") if w.strip()]

if st.button("Generate Practice PDF"):
    output_file = "practice_sheet.pdf"
    create_practice_pdf(words, output_file,
                        clone_count=clone_count,
                        font_choice=font_choice if font_choice=="Helvetica" else font_choice.replace(".ttf",""),
                        margins=(margin_left, margin_right, margin_top, margin_bottom))
    with open(output_file, "rb") as f:
        st.download_button("📥 Download PDF", f, file_name=output_file)

# ------------------------
# Streamlit UI
# ------------------------
st.title("✏️ Kids English Word Tracer Generator")

# Sidebar Controls
st.sidebar.header("⚙️ Settings")
clone_count = st.sidebar.slider("Number of trace clones per word", 3, 10, 5)
font_choice = st.sidebar.selectbox("Font Style", list(FONTS.keys()))
margin_left = st.sidebar.slider("Left Margin", 20, 80, 50)
margin_right = st.sidebar.slider("Right Margin", 20, 80, 50)
margin_top = st.sidebar.slider("Top Margin", 20, 100, 50)
margin_bottom = st.sidebar.slider("Bottom Margin", 20, 100, 50)

# Input words
words_input = st.text_area("Enter words (comma separated)", "Apple, Ball, Cat, Dog, Egg, Fish")

words = [w.strip() for w in words_input.split(",") if w.strip()]

if st.button("Generate Practice PDF"):
    output_file = "practice_sheet.pdf"
    create_practice_pdf(words, output_file,
                        clone_count=clone_count,
                        font_choice=font_choice if font_choice=="Helvetica" else font_choice.replace(".ttf",""),
                        margins=(margin_left, margin_right, margin_top, margin_bottom))
    with open(output_file, "rb") as f:
        st.download_button("📥 Download PDF", f, file_name=output_file)


# ------------------ LEFT: Suffix Finder ------------------
with st.container():
    left_col, right_col = st.columns([1,1])

    with left_col:
        st.markdown("### 🔎 Suffix Finder", unsafe_allow_html=True)
        st.markdown("<div class='card'>", unsafe_allow_html=True)

        suffix = st.text_input("Suffix (e.g., 'ight')", value="ight")
        before_letters = st.number_input("Letters before suffix (0 = any)", min_value=0, step=1, value=0)
        run_search = st.button("Find Words")

        matches = []
        if run_search:
            all_words = get_all_words()
            matches = find_matches(all_words, suffix, before_letters)
            st.success(f"Found {len(matches)} words that end with “{suffix}”.")
            if matches:
                st.dataframe(pd.DataFrame(matches, columns=["Word"]), height=min(500, max(250, len(matches)*28)), use_container_width=True)
            else:
                st.info("No matches. Try another suffix or set 'letters before' = 0.")

        st.markdown("</div>", unsafe_allow_html=True)

    # ------------------ RIGHT: Tracer Generator ------------------
    with right_col:
        st.markdown("### ✏️ PDF Tracer Generator (6 words / page)", unsafe_allow_html=True)
        st.markdown("<div class='card'>", unsafe_allow_html=True)

        default_words_text = "Apple\nBall\nCat\nDog\nEgg\nFish\nGoat\nHat\nIce\nJug\nKite\nLion"
        if run_search and matches:
            default_words_text = "\n".join(matches[:24])  # seed with top matches

        words_text = st.text_area("Practice words (one per line):", value=default_words_text, height=220)
        words_list = [w.strip() for w in words_text.splitlines() if w.strip()]

        c1, c2, c3 = st.columns(3)
        with c1:
            clones_per_word = st.slider("Clone rows", 3, 7, 5)
        with c2:
            font_size = st.slider("Font size", 22, 36, 28)
        with c3:
            underline_full_width = st.toggle("Full-width underline", value=True)

        gen_pdf = st.button("Generate Tracing PDF", type="primary")

        if gen_pdf:
            if not words_list:
                st.warning("Please enter at least one word.")
            else:
                pdf_buf = create_tracer_pdf_buffer(
                    words_list,
                    clones_per_word=clones_per_word,
                    words_per_page=6,
                    font_size_main=font_size,
                    font_size_clone=font_size,
                    underline_full_width=underline_full_width
                )
                st.download_button(
                    "📥 Download Tracing Sheet (PDF)",
                    data=pdf_buf,
                    file_name="tracing_practice_6_per_page.pdf",
                    mime="application/pdf"
                )
                st.success("PDF ready!")

        st.markdown("</div>", unsafe_allow_html=True)

# ------------------ Dictionary Explorer ------------------
st.markdown("### 📘 Dictionary Explorer", unsafe_allow_html=True)
st.markdown("<div class='card'>", unsafe_allow_html=True)

# Options for meanings table
lang_choice = st.selectbox("Show meaning in:", ["English Only", "Tamil Only", "English + Tamil"], index=0)
st.caption("Tip: If Tamil translation fails or is slow, switch to 'English Only'.")

go_defs = st.button("Build Meanings Table from current Suffix results" if 'matches' in locals() and matches else "Build Meanings Table (use words from Tracer box)")

words_for_defs = []
if go_defs:
    # Prefer suffix results if available; else take tracer words
    if 'matches' in locals() and matches:
        words_for_defs = list(dict.fromkeys(matches))  # unique preserving order
    else:
        words_for_defs = words_list

    if not words_for_defs:
        st.info("No words to show. Search a suffix or add words in the Tracer box.")
    else:
        rows = []
        for w in words_for_defs:
            synsets = wordnet.synsets(w)
            if not synsets:
                rows.append({"Word": w, "Word Type": "-", "English": "-", "Tamil": "-", "Synonyms": "-"})
            else:
                # Take unique definitions across POS to avoid explosion; cap a few
                for syn in synsets[:4]:
                    english_def = syn.definition()
                    synonyms = ", ".join(find_synonyms(w)[:10]) if find_synonyms(w) else "-"
                    rows.append({
                        "Word": w,
                        "Word Type": POS_MAP.get(syn.pos(), "Noun"),
                        "English": english_def,
                        "Tamil": "-",  # will fill later if needed
                        "Synonyms": synonyms
                    })
        df_export = pd.DataFrame(rows)

        # Add Tamil if requested
        if lang_choice != "English Only":
            tamil_list = translate_list_parallel(df_export["English"].tolist())
            df_export["Tamil"] = tamil_list

        if lang_choice == "English Only":
            df_view = df_export[["Word", "Word Type", "English", "Synonyms"]]
        elif lang_choice == "Tamil Only":
            df_view = df_export[["Word", "Word Type", "Tamil", "Synonyms"]]
        else:
            df_view = df_export[["Word", "Word Type", "English", "Tamil", "Synonyms"]]

        st.dataframe(df_view, height=min(600, max(300, len(df_view)*28)), use_container_width=True)

        # Excel export
        xbuf = BytesIO()
        with pd.ExcelWriter(xbuf, engine="xlsxwriter") as writer:
            df_export.to_excel(writer, index=False, sheet_name="Meanings")
        xbuf.seek(0)
        st.download_button("📥 Download Meanings (Excel)", xbuf, file_name="meanings.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

st.markdown("</div>", unsafe_allow_html=True)

st.caption("© Brain-Child — Tracing Generator + Dictionary Explorer • 6 words/page ‘golden middle’ layout")


