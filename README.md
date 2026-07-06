# classento-resume-screenerr
bulk resume upload (PDF/DOCX/TXT), scores each against your JD using whichever provider you pick (Groq/Gemini/DeepSeek — dropdown in sidebar), ranks them, and you Accept/Hold/Reject right in the same view. CSV export at the bottom.


Classento Resume Screener

Bulk-upload resumes → score against a job description using your own Groq, Gemini, or DeepSeek API key → manage candidates through Accept / Reject / Hold.

Run it locally first (optional, to test)

bashpip install -r requirements.txt
streamlit run app.py

It opens at http://localhost:8501. Paste your API key in the sidebar and try it before deploying.

Deploy to Streamlit Community Cloud (free, ~5 minutes)


Push this folder to a GitHub repo. You already have one at
github.com/LakshBagdi/classento-resume-screener — replace its contents with these files
(app.py, requirements.txt, this README.md), commit, and push:


bash   cd classento-resume-screener
   # copy app.py and requirements.txt into this folder, replacing what's there
   git add .
   git commit -m "Replace with AI resume screener app"
   git push


Go to share.streamlit.io and sign in with your GitHub account.
Click "New app".
Fill in:

Repository: LakshBagdi/classento-resume-screener
Branch: main (or whatever your default branch is)
Main file path: app.py



Click Deploy. It builds for a minute or two, then gives you a public URL like
https://classento-resume-screener.streamlit.app — this is what you send your boss.
API key: the key box lives in the app's sidebar — whoever uses the deployed app pastes
their own key there each session. Nothing is stored server-side. If you'd rather have one
shared key baked in so your team doesn't need their own:

In the Streamlit Cloud dashboard, go to your app → Settings → Secrets
Add:





toml     DEFAULT_API_KEY = "your-key-here"
     DEFAULT_PROVIDER = "groq"


Then in app.py, near the top of the sidebar section, add:


python     import os
     default_key = st.secrets.get("DEFAULT_API_KEY", "")
     if not api_key:
         api_key = default_key


This way the key lives in Streamlit's encrypted secrets store, not in your code or GitHub repo.


Where to get each API key


Groq (free tier, no credit card): console.groq.com
Gemini (free tier): aistudio.google.com/apikey
DeepSeek: platform.deepseek.com


Notes


Model names drift over time. If a provider retires a model, edit the MODELS dict at the
top of app.py — that's the only place model names are set.
Scanned/image-only PDFs won't extract text — the app will flag them rather than fail silently.
CSV export at the bottom of the results section — useful for sharing a shortlist outside the app.
This is a screening aid, not a final decision-maker. Have a human spot-check borderline
scores (5-7) before rejecting anyone outright.
