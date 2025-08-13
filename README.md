# Suffix Learner (Streamlit)

This Streamlit app finds English words by suffix, shows WordNet meanings and Tamil translations (via deep-translator).

## Quick run (local)
1. python -m venv venv
2. source venv/bin/activate   # Windows: venv\Scripts\activate
3. pip install -r requirements.txt
4. python -c "import nltk; nltk.download('wordnet'); nltk.download('omw-1.4')"
5. set STREAMLIT_SECRETS or edit app to include WORDLIST_REMOTE_URL
6. streamlit run app_streamlit_suffix.py

## Deploy (Streamlit Community Cloud)
1. Push this repo to GitHub (public).
2. Go to https://streamlit.io/cloud -> New app -> connect repo and select `app_streamlit_suffix.py`.
3. In Streamlit Cloud settings, add a secret named `WORDLIST_REMOTE_URL` with the public download URL for your wordlist (or paste URL in sidebar at runtime).
4. Deploy.

## Hosting large wordlist
- Recommended: upload the wordlist as a GitHub Release asset or to Hugging Face Hub and use the public download link.
- If using Google Drive, make sure link is direct download and not the UI preview link.

Notes:
- Streamlit Cloud instances are ephemeral: local file edits (Add Word) are not persistent across redeploys. Persist changes upstream (e.g., update GitHub Release or HF file).
