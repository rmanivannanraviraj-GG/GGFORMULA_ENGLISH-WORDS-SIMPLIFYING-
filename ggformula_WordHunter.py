# ggformula_WordHunter_streamlit_simple.py
import streamlit as st
import pandas as pd
import textwrap
import requests
import gzip
from pathlib import Path
from io import BytesIO

# NLP libs
import nltk
from nltk.corpus import wordnet
try:
    from deep_translator import GoogleTranslator
except Exception:
    GoogleTranslator = None

# Ensure WordNet data available (downloads on first run)
nltk.download('wordnet', quiet=True)
nltk.download('omw-1.4', quiet=True)

# ---------------- Config ----------------
st.set_page_config(page_title="Word Hunter — Simple", page_icon="🔎", layout="wide")

CACHE_DIR = Path("data")
CACHE_DIR.mkdir(exist_ok=True)
CACHE_PATH = CACHE_DIR / "wordlist.txt"
CACHE_GZ_PATH = CACHE_DIR / "wordlist.txt.gz"

POS_MAP = {'n': 'Noun', 'v': 'Verb', 'a': 'Adjective', 's': 'Adjective Satellite', 'r': 'Adverb'}
WRAP_EN = 80
WRAP_TA = 100

# ---------------- Styles (no orange) ----------------
st.markdown(
    """
    <style>
    body { background: #f3fbff; }
    .header { background: linear-gradient(90deg,#e6f7ff,#e6fff2); padding:18px; border-radius:12px; }
    h1 { color:#0b6b8a; font-family: 'Poppins', sans-serif; }
    .card { background:#ffffff; border-radius:10px; padding:12px; margin-bottom:10px; box-shadow: 0 2px 6px rgba(11,107,138,0.06); }
    .word { font-size:20px; font-weight:700; color:#0b6b8a; }
    .suf { color:#1b9aaa; font-weight:800; }
    .small { color:#305f67; font-size:14px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------- Helpers ----------------
def download_if_missing(url: str, dest: Path):
    dest.parent.mkdir(parents=True, exist_ok=True)
    # choose gz or txt by url
    try:
        r = requests.get(url, stream=True, timeout=120)
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024*1024):
                if chunk:
                    f.write(chunk)
        return dest
    except Exception:
        return None

def load_wordlist_from_path(path: Path):
    if not path.exists():
        return []
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8", errors="ignore") as f:
            words = [w.strip() for w in f if w.strip()]
    else:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            words = [w.strip() for w in f if w.strip()]
    # unique and sort short->long
    words = sorted(set(words), key=lambda x: (len(x), x.lower()))
    return words

@st.cache_data(show_spinner=False)
def get_words(remote_url: str = ""):
    # prefer cached plain file
    if CACHE_PATH.exists() and CACHE_PATH.stat().st_size > 0:
        return load_wordlist_from_path(CACHE_PATH)
    if CACHE_GZ_PATH.exists() and CACHE_GZ_PATH.stat().st_size > 0:
        return load_wordlist_from_path(CACHE_GZ_PATH)
    # try remote download if provided
    if remote_url:
        dest = CACHE_GZ_PATH if remote_url.endswith(".gz") else CACHE_PATH
        ok = download_if_missing(remote_url, dest)
        if ok:
            return load_wordlist_from_path(dest)
    # fallback small sample
    sample = ["light","bright","flight","might","right","sight","tight","night","delight","fright",
              "playing","singing","learning","running","dancing","hopping","stopping","jumping"]
    return sample

def find_matches(words, suffix, limit=200):
    s = suffix.lower()
    if not s:
        return []
    matched = [w for w in words if w.lower().endswith(s)]
    matched = sorted(matched, key=len)
    return matched[:limit]

def get_meanings(word):
    syns = wordnet.synsets(word)
    rows = []
    if not syns:
        return rows
    for i, syn in enumerate(syns, start=1):
        pos = POS_MAP.get(syn.pos(), syn.pos())
        eng = syn.definition()
        ta = ""
        if GoogleTranslator:
            try:
                ta = GoogleTranslator(source='en', target='ta').translate(eng)
            except Exception:
                ta = ""
        rows.append((str(i), pos, eng, ta))
    return rows

def highlight_suffix_html(word, suf):
    if suf and word.lower().endswith(suf.lower()):
        prefix = word[:-len(suf)]
        sfx = word[-len(suf):]
        return f"<span class='word'>{prefix}<span class='suf'>{sfx}</span></span>"
    return f"<span class='word'>{word}</span>"

# ---------------- UI ----------------
st.markdown("<div class='header'><h1>🔎 Word Hunter — Simple</h1><div class='small'>Find words by suffix and see their meanings (English & Tamil)</div></div>", unsafe_allow_html=True)
st.write("")

# Remote wordlist URL from Streamlit Secrets or leave blank to use sample
REMOTE_URL = st.secrets.get("WORDLIST_REMOTE_URL", "") if "secrets" in dir(st) else ""

# Load words (cached)
words = get_words(REMOTE_URL)

# Single simple input (no extra options)
suffix = st.text_input("Enter suffix (e.g. ight, ing, tion):", value="")

if suffix:
    matches = find_matches(words, suffix, limit=5000)  # server handles big lists; we limit display below
    st.markdown(f"**Found {len(matches)} words**", unsafe_allow_html=True)
    st.write("")

    # Show top 10 words AND their meanings immediately (no selection)
    top_show = matches[:10]
    results_for_export = []
    if not top_show:
        st.info("No words found for that suffix.")
    else:
        for w in top_show:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown(highlight_suffix_html(w, suffix), unsafe_allow_html=True)

            # get 1-3 meanings
            syn_rows = get_meanings(w)
            if syn_rows:
                for no, pos, eng, ta in syn_rows[:3]:
                    eng_wr = "<br>".join(textwrap.wrap(eng, WRAP_EN))
                    ta_wr = "<br>".join(textwrap.wrap(ta, WRAP_TA)) if ta else ""
                    st.markdown(f"<div class='small'><strong>{pos}</strong> — {eng_wr}</div>", unsafe_allow_html=True)
                    if ta_wr:
                        st.markdown(f"<div class='small'>தமிழ்: {ta_wr}</div>", unsafe_allow_html=True)
            else:
                st.markdown("<div class='small'>Meaning not found</div>", unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)

            # prepare row for export
            # flatten meanings into single cells (join)
            if syn_rows:
                eng_join = " || ".join([r[2] for r in syn_rows])
                ta_join = " || ".join([r[3] for r in syn_rows if r[3]])
                pos_join = " || ".join([r[1] for r in syn_rows])
            else:
                eng_join = ""
                ta_join = ""
                pos_join = ""
            results_for_export.append({"Word": w, "POS": pos_join, "English": eng_join, "Tamil": ta_join})

        # Export: full matched list (up to limit) OR top_show only — give both options
        st.write("")
        col1, col2 = st.columns([1,1])
        with col1:
            df_top = pd.DataFrame(results_for_export)
            towrite = BytesIO()
            df_top.to_excel(towrite, index=False, engine="xlsxwriter")
            towrite.seek(0)
            st.download_button("📥 Download shown words (Excel)", towrite.read(), file_name="wordhunter_shown.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        with col2:
            # export full matches (just words) as txt
            txt_buf = "\n".join(matches).encode("utf-8")
            st.download_button("📥 Download all matched words (.txt)", txt_buf, file_name="matched_words.txt", mime="text/plain")
else:
    st.info("Enter a suffix above to begin. (Very simple view for kids — no extra options.)")
