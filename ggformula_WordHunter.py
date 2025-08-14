import streamlit as st
from nltk.corpus import wordnet
import nltk
from deep_translator import GoogleTranslator
from io import BytesIO
import pandas as pd

# NLTK தரவு ஏற்றம்
nltk.download('wordnet')
nltk.download('omw-1.4')

# பக்க அமைப்பு
st.set_page_config(
    page_title="சொல் மேம்பட்டு", 
    layout="wide",
    page_icon="🔍"
)

# CSS வடிவமைப்பு
st.markdown("""
<style>
.word-container {
    height: 500px;
    overflow-y: scroll;
    padding: 10px;
    background: white;
    border-radius: 8px;
    border: 1px solid #e0e0e0;
    margin-top: 10px;
}
.word-item {
    padding: 8px;
    margin: 4px 0;
    border-left: 3px solid #4285F4;
    background: #f8f9fa;
}
</style>
""", unsafe_allow_html=True)

# தலைப்பு பகுதி
st.markdown("""
<div style="text-align:center; background:#4285F4; padding:15px; border-radius:10px; color:white; margin-bottom:20px;">
    <h1 style="margin:0;">🔍 சொல் மேம்பட்டு</h1>
    <p style="margin:0;">இறுதி எழுத்துகளால் சொற்களைத் தேடவும்</p>
</div>
""", unsafe_allow_html=True)

# முக்கிய பகுதி
col1, col2 = st.columns([1, 2])

with col1:
    # தேடல் பகுதி
    st.subheader("சொல் தேடல்")
    suffix = st.text_input("இறுதி எழுத்துகளை உள்ளிடவும்", "ing")
    
    # வார்த்தை பட்டியல்
    with st.spinner("சொற்கள் ஏற்றப்படுகின்றன..."):
        words = sorted(set(wordnet.all_lemma_names()), key=lambda x: (len(x), x.lower()))
        matches = [w for w in words if w.lower().endswith(suffix.lower())]
    
    st.write(f"கிடைத்த சொற்கள்: {len(matches)}")
    
    # ஸ்க்ரோல் செய்யும் வார்த்தை பட்டியல்
    st.markdown('<div class="word-container">', unsafe_allow_html=True)
    for word in matches[:1000]:  # முதல் 1000 வார்த்தைகள் மட்டும்
        st.markdown(f'<div class="word-item">{word}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    # பொருள் பகுதி
    selected_word = st.selectbox("ஒரு சொல்லைத் தேர்ந்தெடுக்கவும்", [""] + matches[:500])
    
    if selected_word:
        st.subheader(f"📚 {selected_word} - பொருள்")
        
        # பொருள்கள்
        synsets = wordnet.synsets(selected_word)
        if not synsets:
            st.info("இந்த சொல்லுக்கு பொருள் கிடைக்கவில்லை")
        else:
            meanings = []
            for i, syn in enumerate(synsets[:3], 1):  # முதல் 3 பொருள்கள் மட்டும்
                eng = syn.definition()
                try:
                    tam = GoogleTranslator(source='en', target='ta').translate(eng)
                except:
                    tam = "மொழிபெயர்ப்பு தோல்வியுற்றது"
                
                meanings.append({
                    "எண்": i,
                    "ஆங்கில பொருள்": eng,
                    "தமிழ் பொருள்": tam
                })
                
                with st.expander(f"பொருள் {i}"):
                    st.write(f"**ஆங்கிலம்:** {eng}")
                    st.write(f"**தமிழ்:** {tam}")
            
            # Excel பதிவிறக்கம்
            if meanings:
                df = pd.DataFrame(meanings)
                towrite = BytesIO()
                df.to_excel(towrite, index=False, engine='openpyxl')
                towrite.seek(0)
                
                st.download_button(
                    "பொருள்களை பதிவிறக்குக",
                    towrite,
                    file_name=f"{selected_word}_meanings.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

# அடிக்குறிப்பு
st.markdown("""
<div style="text-align:center; margin-top:30px; color:#666; font-size:14px;">
    <p>இறுதி எழுத்துகளை உள்ளிட்டு சொற்களைத் தேடவும்</p>
</div>
""", unsafe_allow_html=True)
