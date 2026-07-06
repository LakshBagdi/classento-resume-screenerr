"""
Classento AI Resume Screener
Bulk-upload resumes, score them against a job description using your own
Groq / Gemini / DeepSeek API key, and manage candidates through an
Accept / Reject / Hold pipeline.

Deploy on Streamlit Community Cloud: push this folder to a GitHub repo,
then go to share.streamlit.io and point it at app.py. See README.md.
"""

import json
import time
from io import BytesIO

import requests
import streamlit as st

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

try:
    import docx
except ImportError:
    docx = None


# ---------------------------------------------------------------------------
# Config — if a provider changes its model name, update it here only.
# ---------------------------------------------------------------------------
MODELS = {
    "Groq (Llama 3.3 70B)": {"provider": "groq", "model": "llama-3.3-70b-versatile"},
    "Gemini 2.0 Flash": {"provider": "gemini", "model": "gemini-2.0-flash"},
    "DeepSeek Chat": {"provider": "deepseek", "model": "deepseek-chat"},
}

SYSTEM_PROMPT = """You are a lead technical recruiter and startup founder at Classento screening resumes against a Job Description.
Your goal is ruthless, high-signal, pragmatic candidate evaluation. Time is limited; optimize for actual execution capability over keywords.

Return ONLY valid JSON (no markdown fences, no preamble, no backticks) matching this exact schema:
{
  "score": <integer 1-10>,
  "verdict": "<strong_fit|possible_fit|weak_fit|not_a_fit>",
  "matched_skills": ["skill1", "skill2"],
  "missing_requirements": ["requirement1"],
  "strengths": "<Punchy bullet-style 1-2 sentence execution summary>",
  "concerns": "<Punchy bullet-style 1-2 sentence risk summary>",
  "years_experience_estimate": <number or null>
}

STRICT EVALUATION & WRITING RULES:
1. STARTUP PRAGMATISM OVER KEYWORDS: Do not penalize strong candidates for trivial gaps (e.g., missing basic tools like Canva if they know advanced analytics, or holding an Economics/ECE degree instead of CS/Marketing if their hands-on project portfolio is elite). Focus on real-world building and shipping.
2. ZERO AI FLUFF: Never use robotic filler words like "The candidate has demonstrated proficiency", "Additionally", "However", or "which aligns with requirements". Write sharp, direct, punchy sentences.
3. SCORING CALIBRATION: Be brutally honest and specific. Do not inflate scores. 
   - 9-10: Exceptional fit, day-one executor, hits all core needs.
   - 7-8: Strong fit with minor non-blocking gaps.
   - 4-6: Missing critical core requirements, high risk.
   - 1-3: Completely unqualified.
4. NO HALLUCINATIONS: Base skills and years of experience STRICTLY on what is explicitly written in the resume text."""

VERDICT_COLOR = {
    "strong_fit": "🟢",
    "possible_fit": "🟡",
    "weak_fit": "🟠",
    "not_a_fit": "🔴",
}

st.set_page_config(page_title="Classento Resume Screener", page_icon="📋", layout="wide")


# ---------------------------------------------------------------------------
# File parsing
# ---------------------------------------------------------------------------
def extract_text(uploaded_file) -> str:
    name = uploaded_file.name.lower()
    data = uploaded_file.read()

    if name.endswith(".pdf"):
        if pdfplumber is None:
            raise RuntimeError("pdfplumber not installed")
        text = []
        with pdfplumber.open(BytesIO(data)) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text.append(t)
        return "\n".join(text)

    if name.endswith(".docx"):
        if docx is None:
            raise RuntimeError("python-docx not installed")
        d = docx.Document(BytesIO(data))
        return "\n".join(p.text for p in d.paragraphs)

    if name.endswith(".txt"):
        return data.decode(errors="ignore")

    raise ValueError(f"Unsupported file type: {name}")


# ---------------------------------------------------------------------------
# Provider calls — each returns the raw text response, which we then parse.
# ---------------------------------------------------------------------------
def call_groq(model: str, api_key: str, jd: str, resume_text: str) -> str:
    resp = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"JOB DESCRIPTION:\n{jd}\n\n---\n\nCANDIDATE RESUME:\n{resume_text}"},
            ],
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def call_deepseek(model: str, api_key: str, jd: str, resume_text: str) -> str:
    resp = requests.post(
        "https://api.deepseek.com/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"JOB DESCRIPTION:\n{jd}\n\n---\n\nCANDIDATE RESUME:\n{resume_text}"},
            ],
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def call_gemini(model: str, api_key: str, jd: str, resume_text: str) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    resp = requests.post(
        url,
        json={
            "contents": [{
                "parts": [{"text": f"{SYSTEM_PROMPT}\n\nJOB DESCRIPTION:\n{jd}\n\n---\n\nCANDIDATE RESUME:\n{resume_text}"}]
            }]
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["candidates"][0]["content"]["parts"][0]["text"]


def clean_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(raw)


def score_resume(provider: str, model: str, api_key: str, jd: str, resume_text: str) -> dict:
    if provider == "groq":
        raw = call_groq(model, api_key, jd, resume_text)
    elif provider == "deepseek":
        raw = call_deepseek(model, api_key, jd, resume_text)
    elif provider == "gemini":
        raw = call_gemini(model, api_key, jd, resume_text)
    else:
        raise ValueError(f"Unknown provider: {provider}")
    return clean_json(raw)


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
if "candidates" not in st.session_state:
    st.session_state.candidates = {}  # filename -> candidate dict
if "processed_files" not in st.session_state:
    st.session_state.processed_files = set()


# ---------------------------------------------------------------------------
# Sidebar — provider + JD
# ---------------------------------------------------------------------------
st.sidebar.title("⚙️ Settings")

model_choice = st.sidebar.selectbox("AI provider", list(MODELS.keys()))
api_key = st.sidebar.text_input("API key", type="password", help="Your own key — never stored or logged.")

provider_links = {
    "groq": "Get a free key (no credit card): console.groq.com",
    "gemini": "Get a free key: aistudio.google.com/apikey",
    "deepseek": "Get a key: platform.deepseek.com",
}
st.sidebar.caption(provider_links[MODELS[model_choice]["provider"]])

st.sidebar.divider()
st.sidebar.subheader("Job description")
default_jd = """Backend Engineering Intern — Classento

Responsibilities: build and maintain REST APIs, work with databases, debug production issues, collaborate with frontend/product.
Requirements: proficiency in a backend language (Python/Go/Node/Java), understanding of DB and API design, familiarity with Git, currently pursuing or recently completed CS/related degree.
Nice to have: Docker/Kubernetes, cloud platforms, competitive programming background, prior internship experience."""

jd_text = st.sidebar.text_area("Paste or edit the JD", value=default_jd, height=280)


# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------
st.title("📋 Classento Resume Screener")
st.caption("Drop resumes in bulk. They'll be scored against the job description on the left and ranked below.")

uploaded_files = st.file_uploader(
    "Upload resumes (PDF, DOCX, or TXT) — select as many as you like",
    type=["pdf", "docx", "txt"],
    accept_multiple_files=True,
)

col_a, col_b = st.columns([1, 3])
with col_a:
    score_btn = st.button("🔍 Score new resumes", type="primary", use_container_width=True)
with col_b:
    if not api_key:
        st.info("Add your API key in the sidebar before scoring.")

if score_btn:
    if not api_key:
        st.error("Please enter an API key in the sidebar first.")
    elif not uploaded_files:
        st.warning("Upload at least one resume first.")
    else:
        new_files = [f for f in uploaded_files if f.name not in st.session_state.processed_files]
        if not new_files:
            st.info("All uploaded resumes have already been scored.")
        progress = st.progress(0, text="Starting...")
        for i, f in enumerate(new_files):
            progress.progress((i) / len(new_files), text=f"Scoring {f.name}...")
            try:
                resume_text = extract_text(f)
                if not resume_text.strip():
                    st.session_state.candidates[f.name] = {
                        "name": f.name.rsplit(".", 1)[0], "filename": f.name,
                        "status": "error", "error": "No extractable text (possibly a scanned image)",
                        "decision": "new",
                    }
                    continue
                result = score_resume(
                    MODELS[model_choice]["provider"], MODELS[model_choice]["model"], api_key, jd_text, resume_text
                )
                result["name"] = f.name.rsplit(".", 1)[0]
                result["filename"] = f.name
                result["status"] = "done"
                result["decision"] = "new"
                st.session_state.candidates[f.name] = result
            except Exception as e:
                st.session_state.candidates[f.name] = {
                    "name": f.name.rsplit(".", 1)[0], "filename": f.name,
                    "status": "error", "error": str(e), "decision": "new",
                }
            st.session_state.processed_files.add(f.name)
        progress.progress(1.0, text="Done")
        time.sleep(0.3)
        progress.empty()
        st.rerun()

st.divider()

# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
candidates = list(st.session_state.candidates.values())

if not candidates:
    st.info("No candidates yet — upload resumes above and click 'Score new resumes' to get started.")
else:
    filter_col1, filter_col2, filter_col3 = st.columns(3)
    with filter_col1:
        decision_filter = st.selectbox("Filter by decision", ["All", "new", "accepted", "hold", "rejected"])
    with filter_col2:
        verdict_filter = st.selectbox("Filter by verdict", ["All", "strong_fit", "possible_fit", "weak_fit", "not_a_fit"])
    with filter_col3:
        sort_by = st.selectbox("Sort by", ["Score (high to low)", "Name (A-Z)"])

    filtered = [c for c in candidates if decision_filter == "All" or c.get("decision") == decision_filter]
    filtered = [c for c in filtered if verdict_filter == "All" or c.get("verdict") == verdict_filter]

    if sort_by == "Score (high to low)":
        filtered.sort(key=lambda c: (c.get("score") is None, -(c.get("score") or 0)))
    else:
        filtered.sort(key=lambda c: c["name"].lower())

    st.write(f"**{len(filtered)}** candidate(s)")

    for c in filtered:
        fname = c["filename"]
        if c["status"] == "error":
            st.error(f"**{c['name']}** — {c['error']}")
            continue

        verdict = c.get("verdict", "unknown")
        emoji = VERDICT_COLOR.get(verdict, "⚪")
        decision = c.get("decision", "new")
        decision_badge = {"accepted": "✅ Accepted", "rejected": "❌ Rejected", "hold": "⏸️ Hold", "new": ""}.get(decision, "")

        with st.expander(f"{emoji}  **{c['score']}/10** — {c['name']}  {decision_badge}", expanded=False):
            col1, col2 = st.columns([2, 1])
            with col1:
                st.markdown(f"**Verdict:** {verdict.replace('_', ' ').title()}")
                if c.get("matched_skills"):
                    st.markdown(f"**Matched skills:** {', '.join(c['matched_skills'])}")
                if c.get("missing_requirements"):
                    st.markdown(f"**Missing:** {', '.join(c['missing_requirements'])}")
                if c.get("strengths"):
                    st.markdown(f"**Strengths:** {c['strengths']}")
                if c.get("concerns"):
                    st.markdown(f"**Concerns:** {c['concerns']}")
                if c.get("years_experience_estimate") is not None:
                    st.markdown(f"**Estimated experience:** ~{c['years_experience_estimate']} years")

            with col2:
                b1, b2, b3 = st.columns(3)
                if b1.button("✅ Accept", key=f"accept_{fname}", use_container_width=True):
                    st.session_state.candidates[fname]["decision"] = "accepted"
                    st.rerun()
                if b2.button("⏸️ Hold", key=f"hold_{fname}", use_container_width=True):
                    st.session_state.candidates[fname]["decision"] = "hold"
                    st.rerun()
                if b3.button("❌ Reject", key=f"reject_{fname}", use_container_width=True):
                    st.session_state.candidates[fname]["decision"] = "rejected"
                    st.rerun()
                if st.button("🗑️ Remove", key=f"remove_{fname}", use_container_width=True):
                    del st.session_state.candidates[fname]
                    st.session_state.processed_files.discard(fname)
                    st.rerun()

    st.divider()
    csv_rows = ["name,filename,score,verdict,decision,years_experience_estimate"]
    for c in candidates:
        if c["status"] == "done":
            csv_rows.append(
                f"{c['name']},{c['filename']},{c.get('score','')},{c.get('verdict','')},{c.get('decision','')},{c.get('years_experience_estimate','')}"
            )
    st.download_button("⬇️ Download results as CSV", "\n".join(csv_rows), file_name="resume_screening_results.csv", mime="text/csv")
