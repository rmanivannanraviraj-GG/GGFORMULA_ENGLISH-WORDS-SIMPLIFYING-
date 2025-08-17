import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Flowable
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import cm
from reportlab.lib import colors
from io import BytesIO

# For PDF generation
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import cm
from reportlab.lib import colors

# -------------------------------------------------------------------
# Streamlit Page Config
st.set_page_config(page_title="Word Suffix Finder", layout="wide")

# System Encoding
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

# ---------- PDF Generator ----------
# ---------- PDF Generator (Final Integrated) ----------
def create_pdf_content(words):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40, leftMargin=40,
        topMargin=40, bottomMargin=40
    )
    story = []

    # Styles
    model_style = ParagraphStyle(
        'ModelWord',
        fontName="Helvetica-Bold",
        fontSize=28,
        alignment=TA_CENTER,
        leading=34,
        textColor=colors.black
    )
    trace_style = ParagraphStyle(
        'TraceWord',
        fontName="Helvetica-Bold",   # same bold font (no size diff)
        fontSize=28,
        alignment=TA_CENTER,
        leading=34,
        textColor=colors.lightgrey
    )

    # Split words into chunks of 6 (per page)
    for page_start in range(0, len(words), 6):
        chunk = words[page_start:page_start+6]
        left_col = chunk[:3]
        right_col = chunk[3:6]

        while len(left_col) < 3:
            left_col.append("")
        while len(right_col) < 3:
            right_col.append("")

        table_data = []
        for left_word, right_word in zip(left_col, right_col):
            left_block, right_block = [], []

            if left_word:
                left_block.append(Paragraph(left_word, model_style))
                left_block.append(Spacer(1, 6))
                for _ in range(5):
                    trace_para = Paragraph(f"<u>{left_word}</u>", trace_style)
                    left_block.append(trace_para)
                    left_block.append(Spacer(1, 4))
            else:
                left_block.append(Spacer(1, 200))

            if right_word:
                right_block.append(Paragraph(right_word, model_style))
                right_block.append(Spacer(1, 6))
                for _ in range(5):
                    trace_para = Paragraph(f"<u>{right_word}</u>", trace_style)
                    right_block.append(trace_para)
                    right_block.append(Spacer(1, 4))
            else:
                right_block.append(Spacer(1, 200))

            table_data.append([left_block, right_block])

        table = Table(
            table_data,
            colWidths=[(A4[0]-100)/2]*2,
            hAlign="CENTER"
        )
        table.setStyle(TableStyle([
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("BOX", (0,0), (-1,-1), 0.5, colors.white),
        ]))
        story.append(table)

        if page_start + 6 < len(words):
            story.append(PageBreak())

    doc.build(story)
    buffer.seek(0)
    return buffer

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



