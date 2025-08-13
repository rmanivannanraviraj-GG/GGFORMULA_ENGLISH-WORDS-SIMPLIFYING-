# app_streamlit_suffix.py
import streamlit as st
import pandas as pd
import textwrap
import os
import requests
import gzip
from io import BytesIO
from pathlib import Path

# NLP libs
import nltk
from nltk.corpus import wordnet
# optional translator
try:
    from deep_translator import GoogleTranslator
except Exception:
    GoogleTranslator = None

# ---------- NLTK data ----------
# ensure wordnet downloaded (quiet)
nltk.download('wordnet', quiet=True)
nltk.download('omw-1.4', quiet=True)

# ---------- Config ----------
st.set_page_config(page_title="Suffix Learner", layout="wide")
WORDLIST_REMOTE_URL = st.secrets.get("WORDLIST_REMOTE_URL", "") if "secrets" in dir(st) else ""
CACHE_DIR = Path("data")
CACHE_DIR.mkdir(exist_ok=True)
CACHE_PATH = CACHE_DIR / "wordlist.txt"
CACHE_GZ_PATH = CACHE_DIR / "wordlist.txt.gz"

POS_MAP = {'n': 'Noun', 'v': 'Verb', 'a': 'Adjective', 's': 'Adjective Satellite', 'r': 'Adverb'}
WRAP_EN = 80
WRAP_TA = 100

# ---------- Helpers ----------
def download_remote_wordlist(url: str, dest: Path):
    """Download remote file (supports .gz or plain txt). Shows progress in Streamlit."""
    resp = requests.get(url, stream=True, timeout=120)
    resp.raise_for_status()
    total = int(resp.headers.get("content-length", 0) or 0)
    chunk_size = 1024 * 1024
    with st.spinner("Downloading wordlist (first-time)..."):
        with open(dest, "wb") as f:
            downloaded = 0
            p = st.progress(0)
            for chunk in resp.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        p.progress(min(100, int(downloaded / total * 100)))
    return dest

def load_wordlist_from_path(path: Path):
    """Load wordlist (txt or gz) into memory (list)."""
    if not path.exists():
        return []
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8", errors="ignore") as f:
            words = [w.strip() for w in f if w.strip()]
    else:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            words = [w.strip() for w in f if w.strip()]
    words = sorted(set(words), key=lambda x: (len(x), x.lower()))
    return words

@st.cache_data(show_spinner=False)
def get_words(remote_url: str):
    """Return cached words; download if needed. If nothing available, fallback to small sample from wordnet."""
    # prefer cached plain file
    if CACHE_PATH.exists() and CACHE_PATH.stat().st_size > 0:
        return load_wordlist_from_path(CACHE_PATH)
    if CACHE_GZ_PATH.exists() and CACHE_GZ_PATH.stat().st_size > 0:
        return load_wordlist_from_path(CACHE_GZ_PATH)
    # download if URL provided
    if remote_url:
        dest = CACHE_GZ_PATH if remote_url.endswith(".gz") else CACHE_PATH
        try:
            download_remote_wordlist(remote_url, dest)
            return load_wordlist_from_path(dest)
        except Exception as e:
            st.warning(f"Could not download remote wordlist: {e}")
    # fallback: use wordnet lemma names (limited)
    try:
        lemmas = list(set(wordnet.all_lemma_names()))
        lemmas = sorted(lemmas, key=lambda x: (len(x), x.lower()))
        return lemmas
    except Exception:
        # final small sample
        sample = ["light","bright","flight","might","right","sight","tight","night","delight","fright",
                  "playing","singing","learning","running","dancing","hopping","stopping","jumping"]
        return sample

def translate_to_tamil(text: str):
    if not GoogleTranslator:
        return ""
    try:
        return GoogleTranslator(source='auto', target='ta').translate(text)
    except Exception:
        return ""

def find_matches(words, suffix, before_letters):
    """Return matched words that end with suffix and have exact number of letters before suffix
       If before_letters is None => ignore before-length constraint"""
    if not suffix:
        return []
    suf = suffix.lower()
    matched = []
    for w in words:
        if not w:
            continue
        if w.lower().endswith(suf):
            if before_letters is None:
                matched.append(w)
            else:
                before_part = w[:-len(suf)]
                # length of before_part in characters
                if len(before_part) == before_letters:
                    matched.append(w)
    matched.sort(key=lambda x: (len(x), x.lower()))
    return matched

def make_highlight_html(word, suf):
    if suf and word.lower().endswith(suf.lower()):
        prefix = word[:-len(suf)]
        sfx = word[-len(suf):]
        return f"<div style='font-size:18px; padding:6px;'><span style='color:#0b6b8a'>{prefix}</span><span style='color:#1b9aaa; font-weight:700'>{sfx}</span></div>"
    return f"<div style='font-size:18px; padding:6px;'>{word}</div>"

# ---------- UI ----------
st.markdown("""
<style>
body { background: #f3fbff; }
.app-header { background: linear-gradient(90deg,#e6f7ff,#e6fff2); padding:12px; border-radius:10px; margin-bottom:8px;}
.kid-card { background:#fff; border-radius:8px; padding:12px; box-shadow: 0 2px 6px rgba(0,0,0,0.04); }
.small { color:#305f67; font-size:14px; }
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='app-header'><h2 style='margin:0;color:#0b6b8a;'>🔎 Suffix Learner — Word Hunter</h2><div class='small'>Find words by suffix and see meanings (English & Tamil)</div></div>", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("Settings")
    st.markdown("Paste remote wordlist URL (optional) or set as Streamlit secret `WORDLIST_REMOTE_URL`.")
    remote_input = st.text_input("Remote wordlist URL (optional)", value=WORDLIST_REMOTE_URL or "")
    st.markdown("---")
    st.markdown("Letters before suffix (exact). Set 0 to ignore this filter.")
    before_letters_in = st.number_input("Letters before suffix", min_value=0, step=1, value=0)
    st.markdown("---")
    st.markdown("Add a word (local only, ephemeral):")
    add_w = st.text_input("Add word (single token)")
    if st.button("Add to local list"):
        if not add_w.strip():
            st.warning("Enter a word.")
        else:
            CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(CACHE_PATH, "a", encoding="utf-8") as f:
                f.write("\n" + add_w.strip())
            st.success(f"Added '{add_w.strip()}' to local cache. (Ephemeral)")

# load words (use remote_input if given else secret)
remote_url = (remote_input.strip() or WORDLIST_REMOTE_URL).strip()
words = get_words(remote_url)

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("Search")
    suff = st.text_input("Suffix (e.g. ight)", value="ight")
    # interpret before_letters_in: 0 -> None (ignore), else integer
    before_param = None if (before_letters_in == 0) else int(before_letters_in)

    if st.button("Search"):
        pass  # triggers rerun; match logic below runs on rerun

    # compute matches
    matches_exact = find_matches(words, suff, before_param)
    matches_related = [w for w in words if w.lower().endswith(suff.lower())] if suff else []

    st.markdown(f"**Exact matches:** {len(matches_exact)}  —  **Related:** {len(matches_related)}")
    st.markdown("<div style='max-height:520px; overflow:auto; padding:6px; background:#fff; border-radius:6px;'>", unsafe_allow_html=True)

    display_list = matches_exact if matches_exact else matches_related
    if not display_list:
        st.write("<div class='small'>No matches to display.</div>", unsafe_allow_html=True)
    else:
        for w in display_list[:2000]:  # safety limit
            st.markdown(make_highlight_html(w, suff), unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    st.write("")
    st.markdown("Quick pick:")
    chosen = st.selectbox("Choose a word", [""] + (display_list[:200] if display_list else []))
    # update query params (store chosen in URL as list)
    if chosen:
        # use st.query_params to update; value must be list of strings
        st.query_params.update({"selected": [chosen]})

with col2:
    st.subheader("Meanings & Translations")
    # read chosen from query params if present, else fallback to chosen variable
    qp = st.query_params
    chosen_from_qp = qp.get("selected", [None])[0] if "selected" in qp else None
    initial_value = chosen_from_qp or chosen or ""
    word_to_show = st.text_input("Type or choose a word", value=initial_value)

    if word_to_show:
        st.markdown(f"### 🔤 {word_to_show}")
        syns = wordnet.synsets(word_to_show)
        if not syns:
            st.info("No WordNet meanings found for this word.")
        else:
            # build table rows
            rows = []
            for i, syn in enumerate(syns, start=1):
                pos = POS_MAP.get(syn.pos(), syn.pos())
                eng = syn.definition()
                ta = translate_to_tamil(eng) if GoogleTranslator else ""
                eng_w = "<br>".join(textwrap.wrap(eng, WRAP_EN))
                ta_w = "<br>".join(textwrap.wrap(ta, WRAP_TA)) if ta else ""
                rows.append((str(i), pos, eng_w, ta_w))

            # HTML table
            html = "<table style='width:100%; border-collapse:collapse;'>"
            html += "<tr style='background:#e6f7ff'><th style='padding:8px'>No</th><th>POS</th><th>English</th><th>Tamil</th></tr>"
            for no, pos, eng_w, ta_w in rows:
                html += f"<tr><td style='padding:8px;border-bottom:1px solid #eee'>{no}</td>"
                html += f"<td style='padding:8px;border-bottom:1px solid #eee'>{pos}</td>"
                html += f"<td style='padding:8px;border-bottom:1px solid #eee'>{eng_w}</td>"
                html += f"<td style='padding:8px;border-bottom:1px solid #eee'>{ta_w}</td></tr>"
            html += "</table>"
            st.markdown(html, unsafe_allow_html=True)

        # Export current meanings
        if st.button("Export current meanings to Excel"):
            if not syns:
                st.warning("No meanings to export.")
            else:
                data = []
                for i, syn in enumerate(syns, start=1):
                    pos = POS_MAP.get(syn.pos(), syn.pos())
                    eng = syn.definition()
                    ta = translate_to_tamil(eng) if GoogleTranslator else ""
                    data.append({"No": i, "POS": pos, "English Definition": eng, "Tamil Translation": ta})
                df = pd.DataFrame(data)
                towrite = BytesIO()
                with pd.ExcelWriter(towrite, engine="xlsxwriter") as writer:
                    df.to_excel(writer, index=False, sheet_name="Meanings")
                towrite.seek(0)
                st.download_button("Download Excel", towrite, file_name=f"{word_to_show}_meanings.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# Footer
st.markdown("<div style='margin-top:12px; color:#555'>Tip: Use short suffixes (like 'ight') and 'Letters before suffix' to narrow results. Add words using the sidebar. For persistent additions, update the upstream wordlist file (GitHub Release / HF Hub).</div>", unsafe_allow_html=True)
