# classento-resume-screenerr
bulk resume upload (PDF/DOCX/TXT), scores each against your JD using whichever provider you pick (Groq/Gemini/DeepSeek — dropdown in sidebar), ranks them, and you Accept/Hold/Reject right in the same view. CSV export at the bottom.


# Classento Resume Screener

An AI-powered resume screening tool built with Streamlit. The application compares multiple resumes against a job description, ranks candidates based on relevance, and allows recruiters to manage applicants in one place.

## Features

- Bulk upload resumes (PDF, DOCX, TXT)
- Compare resumes against a job description
- Supports Groq, Gemini, and DeepSeek APIs
- Candidate status management (Accept, Hold, Reject)
- Resume ranking with match scores
- Export results as CSV

## Running Locally

Install the required dependencies:

```bash
pip install -r requirements.txt
```

Start the application:

```bash
streamlit run app.py
```

The app will be available at:

```
http://localhost:8501
```

## Deployment

The project is designed to run on Streamlit Community Cloud.

1. Push the project to a GitHub repository.
2. Create a new app on Streamlit Community Cloud.
3. Select your repository and branch.
4. Set the main file to:

```
app.py
```

5. Deploy the application.

## API Keys

The application requires an API key from one of the supported providers.

Supported providers:

- Groq
- Google Gemini
- DeepSeek

Paste the API key into the sidebar before processing resumes.

## Optional: Streamlit Secrets

To avoid entering an API key every session, you can store it using Streamlit Secrets.

Example:

```toml
DEFAULT_API_KEY = "your-api-key"
DEFAULT_PROVIDER = "groq"
```

Then load it in `app.py`:

```python
default_key = st.secrets.get("DEFAULT_API_KEY", "")
if not api_key:
    api_key = default_key
```

## Notes

- Text-based PDF, DOCX, and TXT resumes are supported.
- Image-only or scanned PDFs may not contain extractable text.
- Provider model names can be updated in the `MODELS` dictionary if required.
