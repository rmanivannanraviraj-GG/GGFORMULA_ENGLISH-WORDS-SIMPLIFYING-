# streamlit_app.py

import streamlit as st
import pandas as pd
import numpy as np
import re
import json
import time
from io import BytesIO
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# NLP / Lexical
import nltk
from nltk.corpus import wordnet
from deep_translator import GoogleTranslator

# Optional extra corpus
try:
    from nltk.corpus import words as nltk_words
    HAVE_NLTK_WORDS = True
except Exception:
    HAVE_NLTK_WORDS = False

# HTTP
import requests

# PDF
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors

# -----------------------------
# NLTK setup (download if missing)
# -----------------------------
try: nltk.data.find('corpora/wordnet')
except LookupError: nltk.download('wordnet')
try: nltk.data.find('corpora/omw-1.4')
except LookupError: nltk.download('omw-1.4')
if HAVE_NLTK_WORDS:
    try: nltk.data.find('corpora/words')
    except LookupError:
        try: nltk.download('words')
        except Exception: pass

# -----------------------------
# Streamlit Page
# -----------------------------
st.set_page_config(page_title="Word Suffix Finder — Pro", layout="wide")
st.markdown("""
<style>
body { font-family: system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans', 'Liberation Sans', sans-serif; }
.app-header { background: linear-gradient(90deg, #5b86e5, #36d1dc); padding: 18px; border-radius: 14px; color:white; text-align:center; box-shadow:0 2px 8px rgba(0,0,0,.12); margin-bottom:18px;}
.main-card { background:#f7f9fc; border-radius:14px; padding:16px; box-shadow:0 1px 4px rgba(0,0,0,.06); }
.stButton>button { background:#e74c3c; color:#fff; font-weight:600; border-radius:10px; padding:8px 14px; }
.small { opacity:.8; }
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='app-header'><h1 style='margin:0'>BRAIN-CHILD DICTIONARY — Full Version</h1><div class='small'>Suffix-based search • WordNet + Online APIs • Tamil translations • PDF/Excel export</div></div>", unsafe_allow_html=True)

# -----------------------------
# Utilities
# -----------------------------
def safe_get(dct, key, default=""):
    try:
        return dct[key]
    except Exception:
        return default

@st.cache_data(show_spinner=False)
def google_translate_ta(text: str) -> str:
    """Primary translation via deep_translator GoogleTranslator."""
    if not text: return "-"
    try:
        return GoogleTranslator(source='auto', target='ta').translate(text) or "-"
    except Exception:
        return "-"

@st.cache_data(show_spinner=False)
def google_translate_ta_fallback(text: str) -> str:
    """
    Fallback using the public web endpoint (unofficial).
    NOTE: This endpoint is not guaranteed stable.
    """
    if not text: return "-"
    try:
        params = {
            "client": "gtx",
            "sl": "auto",
            "tl": "ta",
            "dt": "t",
            "q": text
        }
        r = requests.get("https://translate.googleapis.com/translate_a/single", params=params, timeout=8)
        r.raise_for_status()
        data = r.json()
        # data format: [[["translated","orig",...], ...], ...]
        out = "".join(chunk[0] for chunk in data[0])
        return out or "-"
    except Exception:
        return "-"

def translate_list_parallel(texts, use_fallback=False, max_workers=12):
    """Translate a list of English strings to Tamil in parallel."""
    func = google_translate_ta_fallback if use_fallback else google_translate_ta
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(func, t): i for i, t in enumerate(texts)}
        results = [None] * len(texts)
        for fut in as_completed(futs):
            i = futs[fut]
            try:
                results[i] = fut.result()
            except Exception:
                results[i] = "-"
    return results

# -----------------------------
# Data sources (Word lists)
# -----------------------------
@st.cache_data(show_spinner=False)
def get_wordnet_words() -> set:
    return set(wordnet.all_lemma_names())

@st.cache_data(show_spinner=False)
def get_nltk_words() -> set:
    if HAVE_NLTK_WORDS:
        try:
            return set(w.lower() for w in nltk_words.words())
        except Exception:
            return set()
    return set()

@st.cache_data(show_spinner=False)
def load_custom_files() -> set:
    """Load optional local files if present."""
    out = set()
    base = Path("data")
    base.mkdir(exist_ok=True)
    for fname in ["custom_words.txt", "large_words.txt"]:
        f = base / fname
        if f.exists():
            try:
                out |= set(x.strip() for x in f.read_text(encoding="utf-8", errors="ignore").splitlines() if x.strip())
            except Exception:
                pass
    return out

@st.cache_data(show_spinner=False)
def build_master_wordlist(include_wordnet=True, include_nltk_corpus=False) -> list:
    words = set()
    if include_wordnet:
        words |= get_wordnet_words()
    if include_nltk_corpus:
        words |= get_nltk_words()
    words |= load_custom_files()
    # normalize + filter reasonable tokens
    cleaned = set()
    for w in words:
        wl = str(w).strip()
        if not wl: continue
        if re.search(r"[^\w'-]", wl):  # strip weird tokens
            continue
        cleaned.add(wl)
    return sorted(cleaned, key=lambda x: (len(x), x.lower()))

# -----------------------------
# Suffix filtering
# -----------------------------
def match_suffix(word: str, suffix: str, before_mode: str, before_n: int) -> bool:
    if not suffix: return False
    if not word.lower().endswith(suffix.lower()):
        return False
    if before_mode == "any":
        return True
    letters_before = len(word) - len(suffix)
    if before_mode == "exact":
        return letters_before == before_n
    if before_mode == "at_least":
        return letters_before >= before_n
    if before_mode == "at_most":
        return letters_before <= before_n
    return True

@st.cache_data(show_spinner=False)
def find_matches(words: list, suffix: str, before_mode: str, before_n: int, max_results: int | None) -> list:
    res = [w for w in words if match_suffix(w, suffix, before_mode, before_n)]
    res.sort(key=lambda x: (len(x), x.lower()))
    if max_results:
        return res[:max_results]
    return res

# -----------------------------
# WordNet lookup
# -----------------------------
@st.cache_data(show_spinner=False)
def wordnet_info(word: str):
    synsets = wordnet.synsets(word)
    out_defs = []
    out_syns = set()
    out_pos = set()
    for s in synsets:
        out_defs.append(s.definition())
        out_pos.add(s.pos())
        for lemma in s.lemmas():
            out_syns.add(lemma.name().replace("_", " "))
    # map POS codes
    pos_map = {'n':'Noun','v':'Verb','a':'Adjective','s':'Adjective (Satellite)','r':'Adverb'}
    pos_list = sorted({pos_map.get(p, p) for p in out_pos})
    return {
        "definitions": list(dict.fromkeys(out_defs)),  # unique order
        "synonyms": sorted(out_syns),
        "pos": pos_list
    }

# -----------------------------
# Online APIs
# -----------------------------
def get_secrets_or_input(label_key: str, label_host: str):
    """Fetch API credentials from st.secrets or the UI."""
    key = st.secrets.get(label_key, "")
    host = st.secrets.get(label_host, "")
    c1, c2 = st.columns(2)
    with c1:
        key = st.text_input(f"{label_key} (hidden input ok)", value=key, type="password")
    with c2:
        host = st.text_input(f"{label_host} (for RapidAPI)", value=host)
    return key.strip(), host.strip()

@st.cache_data(show_spinner=False)
def wordsapi_lookup(word: str, api_key: str, api_host: str):
    if not api_key or not api_host: return {}
    url = f"https://wordsapiv1.p.rapidapi.com/words/{word}"
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": api_host
    }
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200: return {}
        data = r.json()
        out_defs = []
        out_syns = set()
        for res in data.get("results", []):
            if "definition" in res: out_defs.append(res["definition"])
            for s in res.get("synonyms", []): out_syns.add(s)
        return {
            "definitions": list(dict.fromkeys(out_defs)),
            "synonyms": sorted(out_syns),
            "source": "WordsAPI"
        }
    except Exception:
        return {}

@st.cache_data(show_spinner=False)
def owlbot_lookup(word: str, token: str):
    if not token: return {}
    url = "https://owlbot.info/api/v4/dictionary/" + word
    headers = {"Authorization": f"Token {token}"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200: return {}
        data = r.json()
        defs = []
        for item in data.get("definitions", []):
            d = item.get("definition")
            if d: defs.append(d)
        return {
            "definitions": list(dict.fromkeys(defs)),
            "synonyms": [],
            "source": "Owlbot"
        }
    except Exception:
        return {}

@st.cache_data(show_spinner=False)
def dictionaryapi_lookup(word: str):
    """https://api.dictionaryapi.dev/api/v2/entries/en/<word>"""
    url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200: return {}
        data = r.json()
        defs = []
        syns = set()
        for entry in data if isinstance(data, list) else []:
            for meaning in entry.get("meanings", []):
                for d in meaning.get("definitions", []):
                    if "definition" in d: defs.append(d["definition"])
                    for s in d.get("synonyms", []): syns.add(s)
        return {
            "definitions": list(dict.fromkeys(defs)),
            "synonyms": sorted(syns),
            "source": "DictionaryAPI.dev"
        }
    except Exception:
        return {}

def aggregate_meanings(word: str, use_wordsapi: bool, wordsapi_key: str, wordsapi_host: str,
                       use_owlbot: bool, owlbot_token: str, use_dictapi: bool):
    """Combine WordNet + chosen online sources."""
    agg_defs = []
    agg_syns = set()
    sources = []

    # WordNet
    wn = wordnet_info(word)
    if wn["definitions"]:
        agg_defs.extend(wn["definitions"])
        agg_syns |= set(wn["synonyms"])
        sources.append("WordNet")

    # Online (in parallel)
    tasks = []
    with ThreadPoolExecutor(max_workers=3) as ex:
        if use_wordsapi and wordsapi_key and wordsapi_host:
            tasks.append(ex.submit(wordsapi_lookup, word, wordsapi_key, wordsapi_host))
        if use_owlbot and owlbot_token:
            tasks.append(ex.submit(owlbot_lookup, word, owlbot_token))
        if use_dictapi:
            tasks.append(ex.submit(dictionaryapi_lookup, word))

        for fut in as_completed(tasks):
            info = fut.result() or {}
            if info.get("definitions"):
                agg_defs.extend(info["definitions"])
            for s in info.get("synonyms", []):
                agg_syns.add(s)
            if info.get("source"):
                sources.append(info["source"])

    # unique while preserving order
    agg_defs = list(dict.fromkeys([d.strip() for d in agg_defs if d and d.strip()]))

    return {
        "definitions": agg_defs,
        "synonyms": sorted(agg_syns),
        "pos": wn["pos"],
        "sources": sources
    }

# -----------------------------
# PDF generator (English only)
# -----------------------------
def create_tracer_pdf_buffer(words, clones_per_word=5, font_size=28):
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    page_w, page_h = A4
    left_margin = right_margin = 50
    top_margin = bottom_margin = 50
    usable_w = page_w - left_margin - right_margin
    col_gap = 40
    col_w = (usable_w - col_gap) / 2
    x_cols = [left_margin, left_margin + col_w + col_gap]

    font_main = "Helvetica-Bold"
    font_clone = font_main
    line_height = font_size + 12
    clone_gap = 10
    block_height = font_size + (font_size + clone_gap) * clones_per_word + 60

    y_start_orig = page_h - top_margin
    count_on_page = 0
    y_start = y_start_orig

    for idx, word in enumerate(words):
        if count_on_page == 0 and idx > 0:
            c.showPage()
            y_start = y_start_orig
        col = count_on_page % 2
        if col == 0 and count_on_page > 0:
            y_start -= block_height
        x = x_cols[col]
        c.setFont(font_main, font_size); c.setFillColor(colors.black)
        c.drawCentredString(x + col_w / 2, y_start, word)
        c.setFont(font_clone, font_size); c.setFillColor(colors.lightgrey)
        y_clone = y_start - line_height
        for _ in range(clones_per_word):
            c.drawCentredString(x + col_w / 2, y_clone, word)
            underline_y = y_clone - 6; c.setDash(3, 3); c.setStrokeColor(colors.lightgrey)
            c.line(x + 4, underline_y, x + col_w - 4, underline_y); c.setDash()
            y_clone -= (font_size + clone_gap)
        count_on_page += 1
        if count_on_page >= 6:
            count_on_page = 0

    c.save()
    buf.seek(0)
    return buf

# -----------------------------
# UI — Controls
# -----------------------------
with st.container():
    st.markdown("<div class='main-card'>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1.2, 1, 1])
    with c1:
        st.subheader("🔎 Suffix Search")
        suffix = st.text_input("Suffix (e.g., ight, ous, phobia)", value="ight").strip()
        before_mode = st.selectbox("Letters before suffix — mode", ["any", "exact", "at_least", "at_most"], index=0)
        before_n = st.number_input("Letters before suffix — number", min_value=0, step=1, value=0)
        max_results = st.number_input("Max results (0 = no limit)", min_value=0, step=50, value=0)
        include_wordnet = st.checkbox("Use WordNet wordlist", value=True)
        include_nltk_corpus = st.checkbox("Also include nltk.corpus.words (optional)", value=False, help="Large list; improves coverage but heavier.")
        go = st.button("Apply Filter")

    with c2:
        st.subheader("📚 Meaning Sources")
        use_wordsapi = st.checkbox("Add WordsAPI (RapidAPI)", value=False)
        use_owlbot = st.checkbox("Add Owlbot", value=False)
        use_dictapi = st.checkbox("Add DictionaryAPI.dev (free)", value=True)

    with c3:
        st.subheader("🌐 API Credentials")
        wordsapi_key = st.secrets.get("WORDSAPI_KEY", "")
        wordsapi_host = st.secrets.get("WORDSAPI_HOST", "")
        owlbot_token = st.secrets.get("OWLBOT_TOKEN", "")

        if use_wordsapi:
            wordsapi_key, wordsapi_host = get_secrets_or_input("WORDSAPI_KEY", "WORDSAPI_HOST")
        if use_owlbot:
            owlbot_token = st.text_input("OWLBOT_TOKEN", value=owlbot_token, type="password")

    st.markdown("</div>", unsafe_allow_html=True)

# -----------------------------
# Run search
# -----------------------------
if go:
    master_words = build_master_wordlist(include_wordnet, include_nltk_corpus)
    matches = find_matches(
        master_words,
        suffix=suffix,
        before_mode=before_mode,
        before_n=int(before_n),
        max_results=int(max_results) if max_results else None
    )

    st.success(f"Total words found: {len(matches)}")

    if matches:
        # Show simple list first
        st.dataframe(pd.DataFrame({"Word": matches}), use_container_width=True, height=360)

        st.markdown("### 📘 Meanings & Synonyms (WordNet + Online APIs)")
        # Batch lookup with threads
        results = []
        with st.spinner("Fetching meanings..."):
            def task(word):
                info = aggregate_meanings(
                    word,
                    use_wordsapi, wordsapi_key, wordsapi_host,
                    use_owlbot, owlbot_token,
                    use_dictapi
                )
                return word, info

            with ThreadPoolExecutor(max_workers=12) as ex:
                futs = [ex.submit(task, w) for w in matches]
                for fut in as_completed(futs):
                    results.append(fut.result())

        # Build rows
        rows = []
        for word, info in results:
            defs = info["definitions"]
            syns = info["synonyms"]
            pos = ", ".join(info["pos"]) if info["pos"] else "-"
            src = ", ".join(info["sources"]) if info["sources"] else "—"
            if not defs:
                rows.append({
                    "Word": word,
                    "POS": pos,
                    "English Definition": "-",
                    "Tamil Definition": "-",
                    "Synonyms (unique)": ", ".join(syns) if syns else "-",
                    "Sources": src
                })
            else:
                # One row per definition for clarity
                for d in defs:
                    rows.append({
                        "Word": word,
                        "POS": pos,
                        "English Definition": d,
                        "Tamil Definition": "",  # fill later
                        "Synonyms (unique)": ", ".join(syns) if syns else "-",
                        "Sources": src
                    })

        df = pd.DataFrame(rows)

        # Translation controls
        st.markdown("#### 🌏 Translations (English → Tamil)")
        colT1, colT2 = st.columns([1,1])
        with colT1:
            do_translate = st.checkbox("Translate English definitions to Tamil", value=True)
        with colT2:
            use_public_fallback = st.checkbox("If deep-translator fails, use Google public fallback", value=True)

        if do_translate and not df.empty:
            english_defs = df["English Definition"].fillna("").astype(str).tolist()
            ta = translate_list_parallel(english_defs, use_fallback=False)
            # any "-"? try fallback selectively if opted-in
            if use_public_fallback:
                need_idx = [i for i, t in enumerate(ta) if t == "-" or not t.strip()]
                if need_idx:
                    fallback_texts = [english_defs[i] for i in need_idx]
                    fb = translate_list_parallel(fallback_texts, use_fallback=True)
                    for j, i in enumerate(need_idx):
                        ta[i] = fb[j] or "-"
            df["Tamil Definition"] = [t if t and t.strip() else "-" for t in ta]

        # Clean up empties
        df["English Definition"] = df["English Definition"].replace("", "-")
        df["Tamil Definition"] = df["Tamil Definition"].replace("", "-")
        df["Synonyms (unique)"] = df["Synonyms (unique)"].replace("", "-")

        # Show table
        st.dataframe(df, use_container_width=True, height=420)

        # Downloads
        dl1, dl2 = st.columns(2)
        with dl1:
            towrite = BytesIO()
            with pd.ExcelWriter(towrite, engine="xlsxwriter") as writer:
                df.to_excel(writer, index=False, sheet_name="Meanings")
            towrite.seek(0)
            st.download_button("📥 Download Meanings (Excel)", data=towrite, file_name="meanings.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        with dl2:
            json_bytes = json.dumps(df.to_dict(orient="records"), ensure_ascii=False, indent=2).encode("utf-8")
            st.download_button("📥 Download Meanings (JSON)", data=json_bytes, file_name="meanings.json", mime="application/json")

        st.markdown("---")
        st.markdown("### 📝 Word Tracer (PDF, English only)")
        t1, t2 = st.columns([1,1])
        with t1:
            clones_per_word = st.slider("Copies per word", 1, 10, 5, step=1)
        with t2:
            font_size = st.slider("Font size", 18, 48, 28, step=2)
        words_input = st.text_area("Words for practice (one per line)", value="\n".join(matches[:60]), height=160)
        if st.button("Generate PDF"):
            words_for_tracer = [w.strip() for w in words_input.splitlines() if w.strip()]
            if words_for_tracer:
                pdf_data = create_tracer_pdf_buffer(words_for_tracer, clones_per_word=clones_per_word, font_size=font_size)
                st.download_button("Download Practice Sheet (PDF)", data=pdf_data, file_name="word_tracer_sheet.pdf", mime="application/pdf")
            else:
                st.info("Please enter at least one word.")
    else:
        st.info("No results. Try a different suffix or relax the before-suffix constraint.")
else:
    st.info("Enter suffix and click **Apply Filter**.")
