import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from pathlib import Path
from deep_translator import GoogleTranslator
from nltk.corpus import wordnet
import nltk
from concurrent.futures import ThreadPoolExecutor, as_completed
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors

# --- NLTK setup ---
try: nltk.data.find('corpora/wordnet')
except LookupError: nltk.download('wordnet')
try: nltk.data.find('corpora/omw-1.4')
except LookupError: nltk.download('omw-1.4')

# optional extra corpus: nltk.corpus.words
HAVE_NLTK_WORDS = True
try:
    from nltk.corpus import words as nltk_words
    try: nltk.data.find('corpora/words')
    except LookupError: nltk.download('words')
except Exception:
    HAVE_NLTK_WORDS = False

# --- Page setup ---
st.set_page_config(page_title="Word Suffix Finder", layout="wide")
CACHE_DIR = Path("data"); CACHE_DIR.mkdir(exist_ok=True)
POS_MAP = {'n':'Noun','v':'Verb','a':'Adjective','s':'Adjective (Satellite)','r':'Adverb'}

# --- CSS styling (keep your UI) ---
st.markdown("""
<style>
body { font-family: 'Roboto', sans-serif; }
.app-header { background: linear-gradient(90deg, #3498db, #2ecc71); padding: 20px; border-radius: 12px; color:white; text-align:center; box-shadow:0 2px 4px rgba(0,0,0,0.2); margin-bottom:20px;}
.main-container { background-color:#f0f2f6; padding:20px; border-radius:12px; margin-top:20px; box-shadow:0 2px 4px rgba(0,0,0,0.1);}
.stButton>button { background-color:#e74c3c; color:white; font-weight:bold; border-radius:8px; padding:6px 12px;}
</style>
""", unsafe_allow_html=True)

# --- Translation ---
@st.cache_data(show_spinner=False)
def translate_to_tamil(text:str):
    if not text: return "-"
    try:
        out = GoogleTranslator(source='auto', target='ta').translate(text)
        return out if out else "-"
    except Exception:
        return "-"

def google_public_translate(text: str) -> str:
    if not text: return "-"
    try:
        params = {"client":"gtx","sl":"auto","tl":"ta","dt":"t","q":text}
        r = requests.get("https://translate.googleapis.com/translate_a/single", params=params, timeout=8)
        r.raise_for_status()
        data = r.json()
        return "".join(chunk[0] for chunk in data[0]) or "-"
    except Exception:
        return "-"

def translate_list_parallel(texts, max_workers=12):
    results = [None]*len(texts)
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(translate_to_tamil, t): i for i, t in enumerate(texts)}
        for f in as_completed(futs):
            i = futs[f]
            try: results[i] = f.result()
            except Exception: results[i] = "-"
    need = [i for i, t in enumerate(results) if (not t) or t == "-"]
    if need:
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futs = {ex.submit(google_public_translate, texts[i]): i for i in need}
            for f in as_completed(futs):
                i = futs[f]
                try: fb = f.result()
                    results[i] = fb if fb else "-"
                except Exception:
                    results[i] = "-"
    return results

# --- Word lists: WordNet + nltk.corpus.words + Dolch + custom + large ---
@st.cache_data(show_spinner=False)
def get_all_words():
    wordnet_words = set(wordnet.all_lemma_names())
    extra_words = set(w.lower() for w in nltk_words.words()) if HAVE_NLTK_WORDS else set()
    dolch_words = set(["a","and","away","big","blue","can","come","down","find","for","funny","go","help","here","I","in","is","it","jump","little","look","make","me","my","not","one","play","red","run","said","see","the","three","to","up","we","where","yellow","you"])
    custom_file = Path("data/custom_words.txt")
    custom_words = set()
    if custom_file.exists(): custom_words = set(custom_file.read_text(encoding="utf-8", errors="ignore").splitlines())
    large_file = Path("data/large_words.txt")
    large_words = set()
    if large_file.exists(): large_words = set(large_file.read_text(encoding="utf-8", errors="ignore").splitlines())
    merged = wordnet_words.union(extra_words).union(dolch_words).union(custom_words).union(large_words)
    cleaned = {str(x).strip() for x in merged if str(x).strip() and str(x).strip().isascii()}
    return sorted(cleaned, key=lambda x:(len(x), x.lower()))

def find_matches(words, suffix, before_letters):
    suf = (suffix or "").lower().strip()
    if not suf: return []
    matched = []
    for w in words:
        wl = w.lower()
        if wl.endswith(suf):
            if before_letters == 0 or len(wl) - len(suf) == before_letters:
                matched.append(w)
    matched.sort(key=len)
    return matched

# --- Wiktionary parser ---
@st.cache_data(show_spinner=False)
def wiktionary_lookup(word: str):
    try:
        params = {"action":"parse","page":word,"prop":"wikitext","format":"json"}
        r = requests.get("https://en.wiktionary.org/w/api.php", params=params, timeout=10)
        if r.status_code != 200: return {}
        data = r.json()
        wt = data.get("parse", {}).get("wikitext", {}).get("*", "")
        if not wt: return {}
        defs = []
        for line in wt.splitlines():
            line = line.strip()
            if line.startswith("# ") and not line.startswith("##"):
                txt = line.lstrip("# ").strip()
                txt = txt.replace("'''","").replace("''","")
                txt = txt.replace("[[","").replace("]]","")
                if txt: defs.append(txt)
        defs = [d for d in defs if d]
        return {"definitions": list(dict.fromkeys(defs)), "synonyms": [], "source":"Wiktionary"}
    except Exception:
        return {}

# --- WordNet info ---
@st.cache_data(show_spinner=False)
def wordnet_info(word: str):
    synsets = wordnet.synsets(word)
    out_defs, out_syns, out_pos = [], set(), set()
    for s in synsets:
        out_defs.append(s.definition())
        out_pos.add(s.pos())
        for lemma in s.lemmas():
            out_syns.add(lemma.name().replace("_"," "))
    pos_list = sorted({POS_MAP.get(p,p) for p in out_pos}) if out_pos else []
    return {"definitions": list(dict.fromkeys(out_defs)), "synonyms": sorted(out_syns), "pos": pos_list, "source":"WordNet"}

# --- Aggregate meanings ---
@st.cache_data(show_spinner=False)
def aggregate_meanings(word: str):
    agg_defs, agg_syns, sources = [], set(), []
    wn_info = wordnet_info(word)
    if wn_info["definitions"]:
        agg_defs.extend(wn_info["definitions"])
        agg_syns |= set(wn_info["synonyms"])
        sources.append("WordNet")
    tasks=[]
    with ThreadPoolExecutor(max_workers=2) as ex:
        tasks.append(ex.submit(wiktionary_lookup, word))
        for fut in as_completed(tasks):
            info = fut.result() or {}
            if info.get("definitions"):
                agg_defs.extend(info["definitions"])
            for s in info.get("synonyms", []):
                agg_syns.add(s)
            if info.get("source"):
                sources.append(info["source"])
    agg_defs = list(dict.fromkeys([d.strip() for d in agg_defs if d and d.strip()]))
    return {"definitions": agg_defs, "synonyms": sorted(agg_syns), "pos": wn_info["pos"], "sources": sources}

# --- PDF tracer generator retained ---
def create_tracer_pdf_buffer(words):
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    page_w, page_h = A4
    left_margin = right_margin = 50; top_margin = bottom_margin = 50
    usable_w = page_w - left_margin - right_margin
    col_gap = 40; col_w = (usable_w - col_gap)/2; x_cols = [left_margin, left_margin+col_w+col_gap]
    font_main = "Helvetica-Bold"; font_clone = font_main
    font_size_main = 28; font_size_clone = 28
    clones_per_word = 5; line_height = 40; clone_gap = 10
    block_height = font_size_main + (font_size_clone+clone_gap)*clones_per_word + 60
    y_start_orig = page_h - top_margin; count_on_page = 0; y_start = y_start_orig

    for idx, word in enumerate(words):
        if count_on_page==0 and idx>0: c.showPage(); y_start=y_start_orig
        col = count_on_page%2
        if col==0 and count_on_page>0: y_start-=block_height
        x = x_cols[col]
        c.setFont(font_main,font_size_main); c.setFillColor(colors.black)
        c.drawCentredString(x+col_w/2, y_start, word)
        c.setFont(font_clone,font_size_clone); c.setFillColor(colors.lightgrey)
        y_clone=y_start-line_height
        for _ in range(clones_per_word):
            c.drawCentredString(x+col_w/2, y_clone, word)
            underline_y = y_clone-6; c.setDash(3,3); c.setStrokeColor(colors.lightgrey)
            c.line(x+4,underline_y,x+col_w-4,underline_y); c.setDash()
            y_clone-=(font_size_clone+clone_gap)
        count_on_page+=1; 
        if count_on_page>=6: count_on_page=0
    c.save(); buf.seek(0); return buf

# --- UI ---
st.markdown("<div class='app-header'><h1 style='margin:0'>BRAIN-CHILD DICTIONARY</h1><small>Learn spellings and master words with suffixes and meanings</small></div>", unsafe_allow_html=True)

with st.container():
    st.markdown("<div class='main-container'>", unsafe_allow_html=True)
    col1,col2 = st.columns(2,gap="large")

    # --- Find Words ---
    with col1:
        st.subheader("🔎 Find Words")
        with st.form("find_words_form"):
            suffix_input = st.text_input("Suffix (e.g., 'ight')", value="ight")
            before_letters = st.number_input("Letters Before Suffix (0 for any number)", min_value=0, step=1, value=0)
            submit_button = st.form_submit_button("Apply")
            if submit_button:
                all_words = get_all_words()
                matches = find_matches(all_words,suffix_input,before_letters)
                st.session_state['matches']=matches; st.session_state['search_triggered']=True
                st.markdown(f"**Total Words Found:** {len(matches)}")
                if matches: st.dataframe(pd.DataFrame(matches,columns=["Word"]),height=450,use_container_width=True)
                else: st.info("No results found.")

    # --- Word Tracer PDF ---
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
    lang_choice = st.selectbox("Show Meaning in:", ["English Only","Tamil Only","English + Tamil"])

    if st.session_state.get('search_triggered') and 'matches' in st.session_state:
        matches = st.session_state['matches']
        if matches:
            data_rows=[]
            def build_rows(word):
                info = aggregate_meanings(word)
                pos = ", ".join(info.get("pos") or []) if info.get("pos") else "-"
                defs = info.get("definitions") or []
                syns = ", ".join(info.get("synonyms") or []) if info.get("synonyms") else "-"
                if not defs:
                    return [{"Word":word,"Word Type":pos,"English":"-","Tamil":"-","Synonyms":syns}]
                rows=[]
                for d in defs:
                    rows.append({"Word":word,"Word Type":pos,"English":d,"Tamil":"","Synonyms":syns})
                return rows

            with ThreadPoolExecutor(max_workers=12) as ex:
                futs = [ex.submit(build_rows, w) for w in matches]
                for f in as_completed(futs):
                    data_rows.extend(f.result())

            df_export=pd.DataFrame(data_rows)

            # Translation handling
            if lang_choice in ["Tamil Only","English + Tamil"]:
                eng_defs = df_export["English"].fillna("").astype(str).tolist()
                df_export["Tamil"] = translate_list_parallel(eng_defs)

            # View dataframe
            if lang_choice=="English Only":
                df_view=df_export[["Word","Word Type","English","Synonyms"]]
            elif lang_choice=="Tamil Only":
                df_view=df_export[["Word","Word Type","Tamil","Synonyms"]]
            else:
                df_view=df_export[["Word","Word Type","English","Tamil","Synonyms"]]

            for col in df_view.columns:
                df_view[col]=df_view[col].replace("", "-").fillna("-")

            st.dataframe(df_view,height=450,use_container_width=True)

            # --- Excel Export (Sources removed) ---
            df_export_excel = df_export.drop(columns=["Sources"], errors='ignore')
            towrite=BytesIO()
            with pd.ExcelWriter(towrite, engine="openpyxl") as writer:
                df_export_excel.to_excel(writer,index=False,sheet_name="Meanings")
            towrite.seek(0)
            st.download_button("📥 Download as EXCEL SHEET", towrite, file_name="all_meanings.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            st.info("No results found.")
    else:
        st.info("Please enter a suffix and click 'Apply' to see definitions.")
    st.markdown("</div>", unsafe_allow_html=True)
