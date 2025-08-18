import streamlit as st
import pandas as pd
from io import BytesIO
from pathlib import Path
from deep_translator import GoogleTranslator
from nltk.corpus import wordnet
import nltk
from concurrent.futures import ThreadPoolExecutor
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Ensure WordNet
try:
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('wordnet')
try:
    nltk.data.find('corpora/omw-1.4')
except LookupError:
    nltk.download('omw-1.4')

# Page config
st.set_page_config(page_title="Word Suffix Finder", layout="wide")
CACHE_DIR = Path("data")
CACHE_DIR.mkdir(exist_ok=True)

POS_MAP = {'n': 'Noun','v': 'Verb','a': 'Adjective','s': 'Adjective (Satellite)','r': 'Adverb'}

DO_TTF = False

# CSS Styling
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap');
body { font-family: 'Roboto', sans-serif; }
.app-header { background: linear-gradient(90deg, #3498db, #2ecc71); padding: 20px; border-radius: 12px; color: white; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.2); margin-bottom:20px; }
.main-container { background-color:#f0f2f6; padding:20px; border-radius:12px; margin-top:20px; box-shadow:0 2px 4px rgba(0,0,0,0.1);}
.content-box { background-color:#ffffff; padding:15px; border-radius:8px; border:1px solid #e0e0e0; max-height:450px; overflow-y:auto; box-shadow:0 1px 2px rgba(0,0,0,0.05);}
.stButton>button { background-color:#e74c3c; color:white; font-weight:bold; border-radius:8px; padding:6px 12px;}
</style>
""", unsafe_allow_html=True)

# Translation caching
@st.cache_data(show_spinner=False)
def translate_to_tamil(text: str):
    try:
        return GoogleTranslator(source='auto', target='ta').translate(text)
    except:
        return ""

def translate_list_parallel(texts, max_workers=10):
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        return list(executor.map(translate_to_tamil, texts))

# Word list
@st.cache_data
def get_all_words():
    wordnet_words = set(wordnet.all_lemma_names())
    custom_file = Path("data/custom_words.txt")
    custom_words = set()
    if custom_file.exists():
        custom_words = set(custom_file.read_text().splitlines())
    # Dolch Sight words (example subset)
    dolch_words = set(["a","and","away","big","blue","can","come","down","find","for","funny","go","help","here","I","in","is","it","jump","little","look","make","me","my","not","one","play","red","run","said","see","the","three","to","up","we","where","yellow","you"])
    return sorted(wordnet_words.union(custom_words).union(dolch_words), key=lambda x:(len(x), x.lower()))

def find_matches(words, suffix, before_letters):
    suf = suffix.lower()
    matched = []
    for w in words:
        if w.lower().endswith(suf):
            if before_letters == 0 or len(w)-len(suf) == before_letters:
                matched.append(w)
    matched.sort(key=len)
    return matched

def create_tracer_pdf_buffer(words):
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    page_w, page_h = A4
    left_margin = right_margin = 50
    top_margin = bottom_margin = 50
    usable_w = page_w - left_margin - right_margin
    col_gap = 40
    col_w = (usable_w - col_gap)/2
    x_cols = [left_margin, left_margin + col_w + col_gap]

    font_main = "Helvetica-Bold"
    if DO_TTF:
        try:
            pdfmetrics.registerFont(TTFont('Dotted', 'Dotted.ttf'))
            font_main = 'Dotted'
        except:
            font_main = "Helvetica-Bold"
    font_clone = font_main
    font_size_main = 28
    font_size_clone = 28
    clones_per_word = 5
    line_height = 40
    clone_gap = 10
    block_height = font_size_main + (font_size_clone+clone_gap)*clones_per_word + 60

    y_start_orig = page_h - top_margin
    count_on_page = 0
    y_start = y_start_orig

    for idx, word in enumerate(words):
        if count_on_page==0 and idx>0:
            c.showPage()
            y_start = y_start_orig
        col = count_on_page %2
        if col==0 and count_on_page>0:
            y_start -= block_height
        x = x_cols[col]

        c.setFont(font_main, font_size_main)
        c.setFillColor(colors.black)
        c.drawCentredString(x+col_w/2, y_start, word)

        c.setFont(font_clone, font_size_clone)
        c.setFillColor(colors.lightgrey)
        y_clone = y_start - line_height
        for _ in range(clones_per_word):
            c.drawCentredString(x+col_w/2, y_clone, word)
            underline_y = y_clone-6
            c.setDash(3,3)
            c.setStrokeColor(colors.lightgrey)
            c.line(x+4, underline_y, x+col_w-4, underline_y)
            c.setDash()
            y_clone -= (font_size_clone+clone_gap)

        count_on_page +=1
        if count_on_page>=6: count_on_page=0

    c.save()
    buf.seek(0)
    return buf

# Main UI
st.markdown("<div class='app-header'><h1 style='margin:0'>BRAIN-CHILD DICTIONARY</h1><small>Learn spellings and master words with suffixes and meanings</small></div>", unsafe_allow_html=True)

with st.container():
    st.markdown("<div class='main-container'>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2, gap="large")

    # Find Words Form
    with col1:
        st.subheader("🔎 Find Words")
        with st.form("find_words_form"):
            suffix_input = st.text_input("Suffix (e.g., 'ight')", value="ight", key='suffix_input_form')
            before_letters = st.number_input("Letters Before Suffix (0 for any number)", min_value=0, step=1, value=0, key='before_letters_form')
            submit_button = st.form_submit_button("Apply")
            if submit_button:
                all_words = get_all_words()
                matches = find_matches(all_words, suffix_input, before_letters)
                st.session_state['matches'] = matches
                st.session_state['search_triggered'] = True
                st.markdown(f"**Total Words Found:** {len(matches)}")
                if matches:
                    st.dataframe(pd.DataFrame(matches, columns=["Word"]), height=450, use_container_width=True)
                else:
                    st.info("No results found.")

    # PDF Tracer
    with col2:
        st.subheader("📝 Word Tracer Generator")
        if st.session_state.get('search_triggered') and 'matches' in st.session_state:
            words_input = st.text_area("Enter words for practice (one per line):", value="\n".join(st.session_state['matches']), height=150)
        else:
            words_input = st.text_area("Enter words for practice (one per line):", height=150)
        if st.button("Generate PDF"):
            words_for_tracer = [w.strip() for w in words_input.split('\n') if w.strip()]
            if words_for_tracer:
                pdf_data = create_tracer_pdf_buffer(words_for_tracer)
                st.download_button("Download Practice Sheet as PDF", data=pdf_data, file_name="word_tracer_sheet.pdf", mime="application/pdf")

    st.markdown("---")
    st.subheader("📘 Word Definitions")
    lang_choice = st.selectbox("Show Meaning in:", ["English Only","Tamil Only","English + Tamil"], key='lang_choice_main_def')
    if st.session_state.get('search_triggered') and 'matches' in st.session_state:
        matches = st.session_state['matches']
        if matches:
            data_rows = []
            for word in matches:
                syns = wordnet.synsets(word)
                if not syns:
                    data_rows.append({"Word": word, "Word Type":"-","English":"-","Tamil":"-"})
                else:
                    for syn in syns:
                        data_rows.append({"Word": word, "Word Type":POS_MAP.get(syn.pos(),"Noun"), "English": syn.definition(), "Tamil":"-"})
            df_export = pd.DataFrame(data_rows)
            if lang_choice in ["Tamil Only","English + Tamil"]:
                if "Tamil" not in df_export.columns or df_export["Tamil"].isnull().all():
                    df_export["Tamil"] = translate_list_parallel(df_export["English"].tolist())
            if lang_choice=="English Only": df_view = df_export[["Word","Word Type","English"]]
            elif lang_choice=="Tamil Only": df_view = df_export[["Word","Word Type","Tamil"]]
            else: df_view = df_export
            st.dataframe(df_view, height=450, use_container_width=True)
            towrite = BytesIO()
            with pd.ExcelWriter(towrite, engine="xlsxwriter") as writer:
                df_export.to_excel(writer, index=False, sheet_name="Meanings")
            towrite.seek(0)
            st.download_button("📥 Download as EXCEL SHEET", towrite, file_name="all_meanings.xlsx")
        else:
            st.info("No results found.")
    else:
        st.info("Please enter a suffix and click 'Apply' to see definitions.")
    
    st.markdown("</div>", unsafe_allow_html=True)
