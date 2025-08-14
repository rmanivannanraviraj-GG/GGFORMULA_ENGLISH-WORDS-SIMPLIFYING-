import streamlit as st
import pandas as pd
from deep_translator import GoogleTranslator
from nltk.corpus import wordnet
import nltk
from io import BytesIO

# NLTK தரவு ஏற்றம்
nltk.download('wordnet')
nltk.download('omw-1.4')

# தனிப்பயன் வடிவமைப்பு
st.set_page_config(
    page_title="சொல் மேம்பட்டு", 
    layout="wide",
    page_icon="📚"
)

# வண்ணங்கள்
COLORS = {
    'primary': '#4285F4',
    'secondary': '#34A853',
    'background': '#F8F9FA',
    'text': '#202124',
    'card': '#FFFFFF'
}

# CSS வடிவமைப்பு
st.markdown(f"""
<style>
body {{
    background-color: {COLORS['background']};
    font-family: 'Arial', sans-serif;
}}
.word-container {{
    height: 400px;
    overflow-y: auto;
    padding: 15px;
    background: {COLORS['card']};
    border-radius: 10px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}}
.word-item {{
    padding: 10px;
    margin: 5px 0;
    border-left: 4px solid {COLORS['primary']};
    background: #f5f9ff;
}}
</style>
""", unsafe_allow_html=True)

# தலைப்பு
st.markdown(f"""
<div style="background:{COLORS['primary']}; padding:20px; border-radius:10px; color:white;">
    <h1 style="text-align:center; margin:0;">📚 சொல் மேம்பட்டு</h1>
    <p style="text-align:center; margin:0;">சொற்களின் இறுதி எழுத்துகளைக் கொண்டு வார்த்தைகளைக் கண்டறிய</p>
</div>
""", unsafe_allow_html=True)

# முக்கிய வரிசை
col1, col2 = st.columns([1, 2])

with col1:
    # தேடல் பகுதி
    with st.container():
        st.subheader("🔍 வார்த்தை தேடல்")
        suffix = st.text_input("இறுதி எழுத்துகளை உள்ளிடவும்", "ing")
        
        # ஸ்க்ரோல் செய்யும் வார்த்தை பட்டியல்
        st.markdown("<div class='word-container'>", unsafe_allow_html=True)
        
        words = sorted(set(wordnet.all_lemma_names()), key=lambda x: (len(x), x.lower()))
        matches = [w for w in words if w.lower().endswith(suffix.lower())][:500]
        
        for word in matches:
            st.markdown(f"<div class='word-item'>{word}</div>", unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)

with col2:
    # பொருள் மற்றும் வாக்கியம் பகுதி
    selected_word = st.selectbox("ஒரு சொல்லைத் தேர்ந்தெடுக்கவும்", [""] + matches)
    
    if selected_word:
        st.subheader(f"📖 {selected_word} - பொருள் விளக்கம்")
        
        # பொருள்கள்
        synsets = wordnet.synsets(selected_word)
        for i, syn in enumerate(synsets, 1):
            with st.expander(f"பொருள் {i}"):
                eng = syn.definition()
                tam = GoogleTranslator(source='en', target='ta').translate(eng)
                
                st.markdown(f"**ஆங்கிலம்:** {eng}")
                st.markdown(f"**தமிழ்:** {tam}")
        
        # வாக்கியம் உருவாக்கு
        st.subheader("✍️ வாக்கியம் உருவாக்கு")
        sentence = st.text_area(f"'{selected_word}' சொல்லைப் பயன்படுத்தி வாக்கியம் எழுதுக")
        
        if st.button("வாக்கியத்தை சேமிக்க"):
            st.success("வாக்கியம் சேமிக்கப்பட்டது!")

# பக்கத்தின் அடிப்பகுதி
st.markdown("""
<div style="text-align:center; margin-top:20px; color:#666;">
    <p>💡 உதவி: குறுகிய இறுதி எழுத்துகளை முதலில் முயற்சிக்கவும்</p>
</div>
""", unsafe_allow_html=True)
