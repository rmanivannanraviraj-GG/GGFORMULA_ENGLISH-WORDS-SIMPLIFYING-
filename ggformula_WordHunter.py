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

# PDF Unicode font registration (for Tamil if needed)
pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))

# Cache directory
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

# -------------------------------------------------------------------
# CSS Styling
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
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------------
# Caching Functions
@st.cache_data(show_spinner=False)
def get_all_words():
    return sorted(set(wordnet.all_lemma_names()), key=lambda x: (len(x), x.lower()))

@st.cache_data(show_spinner=False)
def translate_to_tamil(text: str):
    try:
        return GoogleTranslator(source='auto', target='ta').translate(text)
    except Exception as e:
        return f"(translation failed)"

def translate_list_parallel(texts, max_workers=min(5, os.cpu_count() or 2)):
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(translate_to_tamil, texts))
    return results

# -------------------------------------------------------------------
# Core Functions
def find_matches(words, suffix, before_letters):
    suf = suffix.lower()
    return sorted(
        [w for w in words if w.lower().endswith(suf) and (before_letters == 0 or len(w) - len(suf) == before_letters)],
        key=len
    )

def find_synonyms(word):
    synonyms = set()
    for syn in wordnet.synsets(word):
        for lemma in syn.lemmas():
            synonyms.add(lemma.name().replace('_', ' '))
    return list(synonyms)

# Try to use dotted handwriting font if available
practice_font = "Helvetica-Bold"
if os.path.exists("KGPrimaryDots.ttf"):  # keep the TTF file in same folder
    pdfmetrics.registerFont(TTFont('Dotted', "KGPrimaryDots.ttf"))
    practice_font = "Dotted"

# -------------------------------------------------------------------
# ---------- Custom Flowable for Tracing with Underline ----------
class UnderlinedWord(Flowable):
    def __init__(self, word, style, width=400):
        Flowable.__init__(self)
        self.word = word
        self.style = style
        self.width = width
        self.height = 40  # approx line height

    def draw(self):
        from reportlab.platypus.paragraph import Paragraph
        p = Paragraph(self.word, self.style)
        w, h = p.wrap(self.width, 0)
        p.drawOn(self.canv, 0, 0)
        # Draw dashed underline
        self.canv.setStrokeColor(colors.lightgrey)
        self.canv.setDash(3, 2)  # dashed pattern
        self.canv.line(0, -2, self.width, -2)

# ✅ PDF generation function
def create_practice_pdf(words, filename="english_practice_sheet.pdf"):
    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4

    # Margins
    left_margin = 50
    right_margin = 50
    top_margin = 50
    bottom_margin = 50

    # Column settings
    column_gap = 40
    column_width = (width - left_margin - right_margin - column_gap) / 2

    # Font settings
    main_font = "Helvetica-Bold"
    main_size = 28
    trace_size = 28

    # Vertical spacing
    line_height = 40
    clone_gap = 10
    block_height = main_size + (trace_size + clone_gap) * 5 + 60  # One word block height

    # Start position
    x_positions = [left_margin, left_margin + column_width + column_gap]
    y_position = height - top_margin

    word_index = 0
    for word in words:
        col = word_index % 2
        if col == 0 and word_index > 0:
            # Left column already used, reduce Y
            y_position -= block_height

        if y_position < bottom_margin + block_height:
            c.showPage()
            y_position = height - top_margin

        x = x_positions[col]

        # Draw main word (Black Bold)
        c.setFont(main_font, main_size)
        c.setFillColor(colors.black)
        c.drawCentredString(x + column_width / 2, y_position, word)

        # Draw clone words (Light Grey Bold with underline/dash lines)
        c.setFont(main_font, trace_size)
        c.setFillColor(colors.lightgrey)

        y_clone = y_position - line_height
        for _ in range(5):
            c.drawCentredString(x + column_width / 2, y_clone, word)

            # Draw dashed underline
            word_width = c.stringWidth(word, main_font, trace_size)
            underline_y = y_clone - 5
            c.setDash(3, 3)
            c.line(
                x + (column_width - word_width) / 2,
                underline_y,
                x + (column_width + word_width) / 2,
                underline_y,
            )
            c.setDash()  # reset dash

            y_clone -= (trace_size + clone_gap)

        word_index += 1

    c.save()
    return filename


# ✅ Streamlit UI
def main():
    st.title("✏️ English Word Tracing Practice Sheet Generator")

    st.write("Enter the English words you want to generate for practice:")

    user_input = st.text_area(
        "Words (comma separated)", "Apple, Ball, Cat, Dog, Egg, Fish, Goat, Hat, Ink, Jug"
    )
    words = [w.strip() for w in user_input.split(",") if w.strip()]

    if st.button("Generate PDF"):
        output_file = "english_practice_sheet.pdf"
        create_practice_pdf(words, output_file)

        with open(output_file, "rb") as f:
            st.download_button(
                label="📥 Download Practice Sheet PDF",
                data=f,
                file_name=output_file,
                mime="application/pdf",
            )

        st.success("✅ PDF generated successfully!")


if __name__ == "__main__":
    main()
# -------------------------------------------------------------------
# --- Main Streamlit App Layout ---
st.markdown("<div class='app-header'><h1 style='margin:0'>BRAIN-CHILD DICTIONARY</h1><small>Learn spellings and master words with suffixes and meanings</small></div>", unsafe_allow_html=True)

with st.container():
    st.markdown("<div class='main-container'>", unsafe_allow_html=True)
    
    col_input1, col_input2 = st.columns(2)
    with col_input1:
        before_letters = st.number_input("Letters Before Suffix (0 for any number)", min_value=0, step=1, value=0, key='before_letters_main')
    with col_input2:
        lang_choice = st.selectbox("Show Meaning in:", ["English Only", "Tamil Only", "English + Tamil"], key='lang_choice_main')

    col1, col2 = st.columns(2, gap="large")

    # Search Column
    with col1:
        st.subheader("🔎 Find Words")
        with st.form("find_words_form"):
            suffix_input = st.text_input("Suffix (e.g., 'ight')", value="ight", key='suffix_input_form')
            search_button = st.form_submit_button(label='Search Words')

        if search_button:
            all_words = get_all_words()
            matches = find_matches(all_words, suffix_input, before_letters)
            st.session_state['matches'] = matches
            st.session_state['search_triggered'] = True
            
            st.markdown(f"**Total Words Found:** {len(matches)}")
            
            if matches:
                matches_df = pd.DataFrame(matches, columns=["Word"])
                st.dataframe(matches_df, height=min(600, len(matches_df)*35), use_container_width=True)
            else:
                st.info("No results found.")

    # Tracer Column
    with col2:
        st.subheader("📝 Word Tracer Generator")
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

    # Word Definitions Section
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
                        data_rows.append({"Word": word, "Word Type": "-", "English": "-", "Tamil": "-", "Synonyms": "-"})
                    else:
                        for syn in syns:
                            eng = syn.definition()
                            synonyms = ", ".join(find_synonyms(word)[:10]) if find_synonyms(word) else "-"
                            data_rows.append({
                                "Word": word,
                                "Word Type": POS_MAP.get(syn.pos(), "Noun"),
                                "English": eng,
                                "Tamil": "-",
                                "Synonyms": synonyms
                            })
                
                df_export = pd.DataFrame(data_rows)

                # Add Tamil translations if required
                if lang_choice != "English Only":
                    tamil_translations = translate_list_parallel([row["English"] for row in data_rows])
                    df_export["Tamil"] = tamil_translations

                if lang_choice == "English Only":
                    df_view = df_export[["Word", "Word Type", "English", "Synonyms"]]
                elif lang_choice == "Tamil Only":
                    df_view = df_export[["Word", "Word Type", "Tamil", "Synonyms"]]
                else:
                    df_view = df_export[["Word", "Word Type", "English", "Tamil", "Synonyms"]]

                st.dataframe(df_view, height=min(600, len(df_view)*35), use_container_width=True)

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







