# app_streamlit_suffix_kids_enhanced.py
import streamlit as st
import pandas as pd
import textwrap
from io import BytesIO
from pathlib import Path
from deep_translator import GoogleTranslator
from nltk.corpus import wordnet
import nltk
import time

# 🔹 NLTK Data Download (cache செய்யப்பட்டது)
@st.cache_resource
def load_nltk_data():
    nltk.download('wordnet')
    nltk.download('omw-1.4')

load_nltk_data()

# ---------- CONFIG ----------
st.set_page_config(
    page_title="சொல் விளையாட்டு - குழந்தைகளுக்கான ஆங்கிலம்", 
    layout="wide",
    page_icon="🌈"
)

# குழந்தைகளுக்கான வண்ணத் திட்டம்
COLORS = {
    'primary': '#4285F4',  # மென்மையான நீலம்
    'secondary': '#34A853',  # மென்மையான பச்சை
    'accent': '#EA4335',  # மென்மையான சிவப்பு
    'background': '#F8F9FA',  # மிகவும் இலகுவான சாம்பல்
    'text': '#FFFFFF',  # கருமையான எழுத்துக்கள்
    'highlight': '#FBBC05',  # மென்மையான மஞ்சள்
    'footer': '#E8EAED',  # மென்மையான அடிக்குறிப்பு பகுதி
    'card': '#34A853',  # மென்மையான சிவப்பு அட்டைகள்
    'border': '#DADCE0'  # எல்லைக்கோடுகள்
}
# ---------- Helpers ----------
@st.cache_data(show_spinner=False)
def translate_to_tamil(text: str):
    try:
        return GoogleTranslator(source='auto', target='ta').translate(text)
    except Exception:
        return ""

@st.cache_data(show_spinner=False, max_entries=100)
def find_matches(words, suffix, before_letters):
    suf = suffix.lower()
    matched = [w for w in words if w.lower().endswith(suf) and 
              (before_letters == 0 or len(w) - len(suf) == before_letters)]
    return sorted(matched, key=len)

def get_related_words(synset):
    """தொடர்புடைய வார்த்தைகளைப் பெறுவது"""
    related = {
        'ஒத்த பொருள்': [],
        'எதிர் பொருள்': [],
        'உதாரணங்கள்': []
    }
    
    # ஒத்த பொருள் (Synonyms)
    for lemma in synset.lemmas():
        if lemma.name() != synset.name().split('.')[0]:
            related['ஒத்த பொருள்'].append(lemma.name())
    
    # எதிர் பொருள் (Antonyms)
    for lemma in synset.lemmas():
        for antonym in lemma.antonyms():
            related['எதிர் பொருள்'].append(antonym.name())
    
    # உதாரணங்கள் (Examples)
    if synset.examples():
        related['உதாரணங்கள்'] = synset.examples()
    
    return related

# ---------- UI Styling ----------
st.markdown(f"""
<style>
/* குழந்தைகளுக்கான வண்ணமயமான UI */
body {{
    background-color: {COLORS['background']};
    font-family: 'Comic Sans MS', cursive, sans-serif;
    line-height: 1.6;
}}

.stApp {{
    max-width: 1200px;
    margin: 0 auto;
    padding-top: 1rem;
}}

h1, h2, h3, h4 {{
    color: {COLORS['primary']};
    margin-bottom: 0.5rem !important;
}}

/* குழந்தைகளுக்கான பொத்தான்கள் */
.stButton>button {{
    background-color: {COLORS['secondary']};
    color: white;
    border: none;
    border-radius: 12px;
    padding: 12px 24px;
    font-size: 16px;
    margin-top: 0.5rem;
    transition: all 0.3s;
    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
}}

.stButton>button:hover {{
    background-color: #{COLORS['secondary']}dd;
    color: white;
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(0,0,0,0.15);
}}

/* தேர்வு பெட்டி வடிவமைப்பு */
.stSelectbox>div>div>select {{
    font-size: 16px;
    padding: 12px;
    margin-bottom: 0.5rem;
    border-radius: 12px;
    border: 2px solid {COLORS['border']};
}}

/* அட்டவணை வடிவமைப்பு */
table {{
    width: 100%;
    border-collapse: collapse;
    margin: 15px 0;
    font-size: 15px;
    border-radius: 12px;
    overflow: hidden;
}}

th {{
    background-color: {COLORS['primary']};
    color: white;
    padding: 14px;
    text-align: left;
    font-size: 16px;
}}

td {{
    padding: 12px;
    border-bottom: 1px solid {COLORS['border']};
}}

tr:nth-child(even) {{
    background-color: #f5f5f5;
}}

/* சொல் முன்னிலைப்படுத்தல் */
.highlight {{
    color: {COLORS['accent']};
    font-weight: bold;
    font-size: 18px;
}}

/* சொற்கள் பட்டியல் */
.word-list {{
    font-size: 17px;
    line-height: 2.2;
    column-count: 2;
    column-gap: 25px;
}}

.word-item {{
    margin-bottom: 10px;
    break-inside: avoid;
    padding: 8px;
    border-radius: 8px;
    transition: all 0.2s;
}}

.word-item:hover {{
    background-color: {COLORS['highlight']}22;
}}

/* அட்டைகள் */
.card {{
    background-color: {COLORS['card']};
    border-radius: 16px;
    padding: 20px;
    margin-bottom: 20px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    border: 1px solid {COLORS['border']};
}}

/* அடிக்குறிப்பு */
.footer {{
    background-color: {COLORS['footer']};
    padding: 18px;
    border-radius: 16px;
    margin-top: 30px;
    font-size: 15px;
    color: {COLORS['text']};
    text-align: center;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}}

/* புதிய சொல் சேர்க்கும் பகுதி */
.add-word-card {{
    background-color: {COLORS['card']};
    border-radius: 16px;
    padding: 20px;
    margin-top: 20px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    border: 2px dashed {COLORS['primary']}40;
}}

/* தொடர்புடைய சொற்கள் அட்டை */
.related-words-card {{
    background-color: {COLORS['card']};
    border-radius: 12px;
    padding: 15px;
    margin-top: 15px;
    border: 1px solid {COLORS['border']};
}}

.related-word-item {{
    padding: 8px;
    margin: 5px 0;
    background-color: {COLORS['highlight']}15;
    border-radius: 8px;
    display: inline-block;
}}

/* முன்னேற்ற பட்டை */
.stProgress > div > div > div > div {{
    background-color: {COLORS['accent']} !important;
}}
</style>
""", unsafe_allow_html=True)

# தலைப்பு பகுதி
st.markdown(f"""
<div style="text-align:center; padding-bottom:20px;">
    <h1 style="color:{COLORS['primary']}; margin-bottom:10px;">🌈 சொல் விளையாட்டு</h1>
    <p style="color:{COLORS['text']}; font-size:18px;">சொற்களின் இரகசியங்களைக் கண்டுபிடிப்போம்!</p>
</div>
""", unsafe_allow_html=True)

# முக்கிய பக்க வடிவமைப்பு
col1, col2 = st.columns([1, 2])

with col1:
    # தேடல் பகுதி
    with st.container():
        st.markdown(f"""
        <div class="card">
            <h3>🔍 சொற்களைத் தேடு</h3>
        """, unsafe_allow_html=True)
        
        suffix_input = st.text_input(
            "இறுதி எழுத்துகளை உள்ளிடவும் (எ.கா. 'ing')", 
            value="ing",
            key="suffix_input"
        )
        
        before_letters = st.number_input(
            "இறுதி எழுத்துகளுக்கு முன் எத்தனை எழுத்துகள்?", 
            min_value=0, 
            step=1, 
            value=0,
            help="0 எனில் எத்தனை இருந்தாலும் பரவாயில்லை"
        )
        
        # வேகமான தேடலுக்கு
        with st.spinner("சொற்கள் ஏற்றப்படுகின்றன..."):
            all_words = sorted(set(wordnet.all_lemma_names()), key=lambda x: (len(x), x.lower()))
        
        # பொருத்தமான சொற்களைக் கண்டறிதல்
        if suffix_input:
            with st.spinner("சொற்கள் தேடப்படுகின்றன..."):
                matches = find_matches(all_words, suffix_input, before_letters)
                st.success(f"**கிடைத்த சொற்கள்:** {len(matches)}")
                
                # சொற்களின் பட்டியல் - 2 நெடுவரிசைகளில்
                if matches:
                    st.markdown('<div class="word-list">', unsafe_allow_html=True)
                    for w in matches[:300]:  # முதல் 300 சொற்களை மட்டும் காட்டுகிறது
                        if suffix_input.lower() in w.lower():
                            parts = w.rsplit(suffix_input, 1)
                            st.markdown(
                                f'<div class="word-item">'
                                f"{parts[0]}<span class='highlight'>{suffix_input}</span>" 
                                f'</div>' if len(parts) > 1 else f'<div class="word-item">{w}</div>',
                                unsafe_allow_html=True
                            )
                    st.markdown('</div>', unsafe_allow_html=True)
        
        # புதிய சொல் சேர்க்கும் பகுதி
        st.markdown(f"""
        <div class="add-word-card">
            <h4>➕ புதிய சொல் சேர்க்க</h4>
            <p>உங்களுக்குத் தெரிந்த புதிய சொல்லைச் சேர்க்கவும்</p>
        """, unsafe_allow_html=True)
        
        add_w = st.text_input("சொல்லை இங்கே எழுதவும்", key="add_word")
        if st.button("சொல்லைச் சேர்க்க"):
            if not add_w.strip():
                st.warning("ஒரு சொல்லை எழுதவும்.")
            else:
                CACHE_PATH = Path("data/wordlist.txt")
                CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
                with open(CACHE_PATH, "a", encoding="utf-8") as f:
                    f.write("\n" + add_w.strip())
                st.success(f"'{add_w.strip()}' சொல் வெற்றிகரமாக சேர்க்கப்பட்டது!")
                time.sleep(1)
                st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)  # add-word-card close
        st.markdown("</div>", unsafe_allow_html=True)  # card close

with col2:
    # விரைவான தேர்வு மற்றும் அர்த்தங்கள்
    with st.container():
        st.markdown(f"""
        <div class="card">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <h3 style="margin: 0;">📚 அர்த்தங்கள்</h3>
        """, unsafe_allow_html=True)
        
        # தேர்வு பெட்டி மற்றும் டவுன்லோட் பொத்தான்
        if 'matches' in locals() and matches:
            chosen = st.selectbox(
                "ஒரு சொல்லைத் தேர்ந்தெடுக்கவும்", 
                [""] + matches[:200],
                key="word_select",
                label_visibility="collapsed"
            )
            
            if chosen:
                towrite = BytesIO()
                syns = wordnet.synsets(chosen)
                if syns:
                    data_rows = []
                    for i, syn in enumerate(syns, start=1):
                        pos = "வினை" if syn.pos() == 'v' else "பெயர்" if syn.pos() == 'n' else "பெயரடை" if syn.pos() in ('a', 's') else "வினையடை"
                        eng = syn.definition()
                        ta = translate_to_tamil(eng)
                        
                        # தொடர்புடைய வார்த்தைகளைப் பெறுதல்
                        related_words = get_related_words(syn)
                        related_str = ""
                        if related_words['ஒத்த பொருள்']:
                            related_str += f"ஒத்தவை: {', '.join(set(related_words['ஒத்த பொருள்']))}"
                        if related_words['எதிர் பொருள்']:
                            related_str += f" | எதிர்: {', '.join(set(related_words['எதிர் பொருள்']))}"
                        
                        data_rows.append({
                            "எண்": i, 
                            "வகை": pos, 
                            "ஆங்கிலம்": eng, 
                            "தமிழ்": ta,
                            "தொடர்புடையவை": related_str
                        })
                    
                    df_export = pd.DataFrame(data_rows)
                    with pd.ExcelWriter(towrite, engine="xlsxwriter") as writer:
                        df_export.to_excel(writer, index=False, sheet_name="Meanings")
                    towrite.seek(0)
                    
                    st.download_button(
                        "📊 அனைத்து அர்த்தங்களையும் பதிவிறக்குக", 
                        towrite, 
                        file_name=f"{chosen}_அர்த்தங்கள்.xlsx",
                        help="இந்த சொல்லின் அனைத்து அர்த்தங்களையும் Excel கோப்பாக சேமிக்க"
                    )
        
        st.markdown("</div>", unsafe_allow_html=True)  # flex div close
        
        # தேர்ந்தெடுக்கப்பட்ட சொல்லின் அர்த்தங்கள்
        if 'chosen' in locals() and chosen:
            st.markdown(f"### ✨ {chosen}")
            
            syns = wordnet.synsets(chosen)
            if not syns:
                st.info("இந்த சொல்லுக்கு அர்த்தங்கள் கிடைக்கவில்லை.")
            else:
                for i, syn in enumerate(syns, start=1):
                    pos = "வினை" if syn.pos() == 'v' else "பெயர்" if syn.pos() == 'n' else "பெயரடை" if syn.pos() in ('a', 's') else "வினையடை"
                    eng = syn.definition()
                    ta = translate_to_tamil(eng)
                    
                    with st.expander(f"அர்த்தம் {i} ({pos})", expanded=True if i == 1 else False):
                        st.markdown(f"**🌍 ஆங்கிலம்:** {eng}")
                        if ta:
                            st.markdown(f"**🇮🇳 தமிழ்:** {ta}")
                        
                        # தொடர்புடைய வார்த்தைகளைக் காட்டுதல்
                        related_words = get_related_words(syn)
                        
                        if related_words['ஒத்த பொருள்'] or related_words['எதிர் பொருள்'] or related_words['உதாரணங்கள்']:
                            st.markdown("---")
                            st.markdown("**🔗 தொடர்புடையவை:**")
                            
                            if related_words['ஒத்த பொருள்']:
                                st.markdown(f"""
                                <div class="related-words-card">
                                    <h4>ஒத்த பொருள் கொண்டவை</h4>
                                    <div>
                                """, unsafe_allow_html=True)
                                for word in set(related_words['ஒத்த பொருள்']):
                                    st.markdown(f'<div class="related-word-item">{word}</div>', unsafe_allow_html=True)
                                st.markdown("</div></div>", unsafe_allow_html=True)
                            
                            if related_words['எதிர் பொருள்']:
                                st.markdown(f"""
                                <div class="related-words-card">
                                    <h4>எதிர் பொருள் கொண்டவை</h4>
                                    <div>
                                """, unsafe_allow_html=True)
                                for word in set(related_words['எதிர் பொருள்']):
                                    st.markdown(f'<div class="related-word-item">{word}</div>', unsafe_allow_html=True)
                                st.markdown("</div></div>", unsafe_allow_html=True)
                            
                            if related_words['உதாரணங்கள்']:
                                st.markdown(f"""
                                <div class="related-words-card">
                                    <h4>உதாரண வாக்கியங்கள்</h4>
                                """, unsafe_allow_html=True)
                                for example in related_words['உதாரணங்கள்']:
                                    st.markdown(f"- {example}")
                                st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)  # card close

# அடிக்குறிப்பு
st.markdown(f"""
<div class="footer">
    <p style="margin:0;">💡 உதவி: குறுகிய இறுதி எழுத்துகளை முதலில் முயற்சிக்கவும் (எ.கா 'ing', 'tion')</p>
    <p style="margin:10px 0 0 0; font-size:14px; color:#5f6368;">இந்த பயன்பாடு குழந்தைகளின் ஆங்கில கற்றலை மகிழ்ச்சியாக மாற்ற உதவுகிறது!</p>
</div>
""", unsafe_allow_html=True)

# பக்கத்தின் கீழே ஒரு சிறிய அலங்காரம்
st.markdown("""
<div style="text-align:center; margin-top:20px;">
    <div style="display:inline-block; margin:0 5px;">✨</div>
    <div style="display:inline-block; margin:0 5px;">🎈</div>
    <div style="display:inline-block; margin:0 5px;">📚</div>
    <div style="display:inline-block; margin:0 5px;">🌈</div>
    <div style="display:inline-block; margin:0 5px;">🧩</div>
</div>
""", unsafe_allow_html=True)

