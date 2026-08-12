"""HR Dashboard — internal use only. Resume ingestion review, candidate
ranking against already-ingested job roles, skill-gap summary, and
interview summaries. The full learning roadmap is shown to the candidate
only, on the Candidate Assessment page.

Run with: streamlit run app/ui/streamlit_app.py
"""
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.config import settings
from app.db.database import SessionLocal, init_db
from app.db.models import Candidate, Interview, JobDescription
from app.modules.matching.matcher import match_job_to_candidates
from app.modules.skill_gap.generator import generate_skill_gap

st.set_page_config(page_title="AI Smart Recruitment Engine — HR Dashboard", layout="wide")
init_db()

# --- HR login gate ---
if "hr_authenticated" not in st.session_state:
    st.session_state["hr_authenticated"] = False

if not st.session_state["hr_authenticated"]:
    st.title("HR Login")
    password = st.text_input("Password", type="password")
    if st.button("Log in"):
        if password == settings.HR_PASSWORD:
            st.session_state["hr_authenticated"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    st.stop()

st.title("AI-Driven Smart Recruitment Engine — Candidate Ranking")
st.caption("Select a job role to evaluate applied candidates, ATS match scores, and screening summaries.")
st.info(
    "This page is for recruiters only. The candidate-facing screening interview "
    "is a separate page — see 'Candidate Interview' in the sidebar.",
    icon="🔒",
)

session = SessionLocal()
candidates = session.query(Candidate).all()
all_jobs = session.query(JobDescription).order_by(JobDescription.id.desc()).all()
session.close()

if not candidates:
    st.info(
        "No candidates yet. Add resumes to `data/resumes/` and run:\n\n"
        "`python -m app.modules.resume_parser.ingest`"
    )
else:
    with st.expander(f"View {len(candidates)} ingested candidate(s)"):
        for c in candidates:
            st.write(f"**{c.name}** — {c.email}")

seen_titles = set()
job_options = []
for j in all_jobs:
    key = j.title.strip().lower()
    if key not in seen_titles:
        job_options.append(j)
        seen_titles.add(key)

st.divider()
st.header("📋 Select Job Role")

if not job_options:
    st.info(
        "No job roles ingested yet. Add `.txt` files to `data/jobs/` (one per role) and run:\n\n"
        "`python -m app.modules.matching.ingest_job`"
    )
    st.stop()

selected_job = st.selectbox(
    "Choose a job title to view applicant rankings:",
    options=job_options,
    format_func=lambda j: j.title,
)

if st.button("Evaluate & Rank Candidates", type="primary"):
    if not candidates:
        st.warning("No candidates ingested yet — add resumes to data/resumes/ and run the ingest pipeline first.")
    else:
        with st.spinner("Scoring candidates against this role..."):
            match_session = SessionLocal()
            try:
                ranked = match_job_to_candidates(match_session, selected_job, top_n=10)
                results = [
                    {
                        "candidate_id": r["candidate"].id,
                        "name": r["candidate"].name,
                        "email": r["candidate"].email,
                        "score": r["score"],
                    }
                    for r in ranked
                ]
                st.session_state["match_job_id"] = selected_job.id
                st.session_state["match_job_title"] = selected_job.title
                st.session_state["match_results"] = results
            finally:
                match_session.close()

if "match_results" in st.session_state:
    st.subheader(f"Ranked candidates for: {st.session_state['match_job_title']}")

    for i, r in enumerate(st.session_state["match_results"], 1):
        st.write(f"**{i}. {r['name']}** — {r['email']}  \n"
                 f"ATS Match Score: **{r['score']*100:.1f}%**")
        st.progress(r["score"])

        interview_session = SessionLocal()
        try:
            interview = (
                interview_session.query(Interview)
                .filter_by(candidate_id=r["candidate_id"])
                .order_by(Interview.id.desc())
                .first()
            )
            if interview:
                transcript = interview.transcript_json or []
                assistant_msgs = [m["content"] for m in transcript if m.get("role") == "assistant"]
                closing_summary = assistant_msgs[-1] if assistant_msgs else "No summary available."
                status = interview.status
        finally:
            interview_session.close()

        if interview:
            label = f"📝 Screening Summary ({status})"
            with st.expander(label):
                st.write(closing_summary)
        else:
            st.caption("No screening interview completed yet for this candidate.")

        roadmap_key = f"roadmap_{r['candidate_id']}_{st.session_state['match_job_id']}"

        if st.button(f"Generate Skill-Gap Summary for {r['name']}", key=f"btn_{roadmap_key}"):
            with st.spinner("Analyzing skill gap with the LLM..."):
                gap_session = SessionLocal()
                try:
                    candidate = gap_session.get(Candidate, r["candidate_id"])
                    job = gap_session.get(JobDescription, st.session_state["match_job_id"])
                    try:
                        roadmap = generate_skill_gap(gap_session, candidate, job)
                        st.session_state[roadmap_key] = roadmap
                    except ValueError as e:
                        st.error(str(e))
                finally:
                    gap_session.close()

        if roadmap_key in st.session_state:
            roadmap = st.session_state[roadmap_key]
            st.markdown(f"**Summary:** {roadmap.get('overall_summary', '')}")

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**✅ Matched skills**")
                for skill in roadmap.get("matched_skills", []):
                    st.write(f"- {skill}")
            with col2:
                st.markdown("**⚠️ Missing skills**")
                for gap in roadmap.get("missing_skills", []):
                    st.write(f"- **{gap.get('skill')}** ({gap.get('priority')}): {gap.get('reason')}")

        st.divider()