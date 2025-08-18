import streamlit as st
from nltk.corpus import wordnet as wn
from nltk.corpus import words
from deep_translator import GoogleTranslator
from wiktionaryparser import WiktionaryParser
import requests

# Wiktionary parser
parser = WiktionaryParser()

# Title
st.title("📘 Word Explorer")

# User Inputs
suffix = st.text_input("Enter Suffix (e.g., ous, ence, phobia)")
before_suffix = st.number_input("Letters before suffix (optional)", min_value=0, max_value=10, value=0)

show_meaning = st.selectbox("Show Meaning", ["No", "Yes"])
meaning_lang = st.selectbox("Word Definitions Language", ["English", "Tamil"])

# Styled apply button
apply = st.button("Apply", type="primary")  # Streamlit built-in primary gives colored look

# Helper: Get word definitions
def get_definitions(word, lang):
    definitions = []

    # Try WordNet first
    synsets = wn.synsets(word)
    if synsets:
        defs = [s.definition() for s in synsets]
        definitions.extend(defs)

    # If WordNet empty → Wiktionary
    if not definitions:
        try:
            parsed = parser.fetch(word, "english")
            for entry in parsed:
                for definition in entry.get("definitions", []):
                    defs = definition.get("text", [])
                    definitions.extend(defs)
        except Exception:
            pass

    # If still empty → DictionaryAPI.dev
    if not definitions:
        try:
            r = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}")
            if r.status_code == 200:
                data = r.json()
                for meaning in data[0]["meanings"]:
                    for d in meaning["definitions"]:
                        definitions.append(d["definition"])
        except Exception:
            pass

    # If Tamil selected → translate
    if lang == "Tamil" and definitions:
        try:
            definitions = [GoogleTranslator(source="en", target="ta").translate(d) for d in definitions]
        except Exception:
            pass

    return definitions[:3]  # Limit 3 definitions

# Main logic
if apply:
    if not suffix:
        st.warning("Please enter a suffix.")
    else:
        all_words = set(words.words())
        matched = [w for w in all_words if w.endswith(suffix) and len(w) > before_suffix + len(suffix)]

        st.write(f"### Results for suffix: `{suffix}`")
        st.write(f"**Total words found:** {len(matched)}")

        for w in matched[:100]:  # limit 100
            st.markdown(f"**{w}**")

            if show_meaning == "Yes":
                defs = get_definitions(w, meaning_lang)
                if defs:
                    for d in defs:
                        st.write(f"- {d}")
                else:
                    st.write("_No definition found_")
