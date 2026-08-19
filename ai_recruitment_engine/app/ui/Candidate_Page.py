"""Candidate Screening Assessment Page with Resume Upload & Proctoring."""
import os
import sys
import tempfile
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

# Path Setup
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.db.database import SessionLocal, init_db
from app.db.models import Candidate, JobDescription
from app.modules.interview_bot.bot import get_next_bot_message, save_interview, MAX_QUESTIONS
from app.modules.matching.matcher import match_job_to_candidates
from app.modules.skill_gap.generator import generate_skill_gap
from app.modules.resume_parser.parser import extract_text, UnsupportedFileType
from app.modules.resume_parser.embedder import ingest_resume

st.set_page_config(page_title="Candidate Assessment", layout="centered")
init_db()

# ==============================================================================
# PROCTORING SCRIPT
# ==============================================================================
def inject_proctoring_system():
    proctor_js = """
    <script>
    (function() {
        const pDoc = window.parent.document;
        const pWin = window.parent;

        function disablePaste(e) {
            if (e.type === 'paste') {
                e.preventDefault();
                alert('SECURITY ALERT: Pasting content is strictly disabled!');
            }
            if (e.type === 'contextmenu' || e.type === 'copy') {
                e.preventDefault();
            }
        }

        pDoc.addEventListener('paste', disablePaste, true);
        pDoc.addEventListener('contextmenu', disablePaste, true);
        pDoc.addEventListener('copy', disablePaste, true);

        setInterval(function() {
            const textareas = pDoc.querySelectorAll('textarea, input');
            textareas.forEach(el => {
                if (!el.dataset.protected) {
                    el.addEventListener('paste', disablePaste, true);
                    el.dataset.protected = "true";
                }
            });
        }, 300);

        if (!pWin.hasProctorListener) {
            pWin.hasProctorListener = true;
            pDoc.addEventListener('visibilitychange', function() {
                if (pDoc.hidden) {
                    alert('CHEATING WARNING: You switched browser tabs or minimized the window! Remaining on this page is mandatory.');
                }
            });
        }
    })();
    </script>
    """
    components.html(proctor_js, height=0)

# ==============================================================================

st.title("Candidate Screening Assessment")
st.caption("Complete your screening assessment in a secure environment.")

session = SessionLocal()
jobs = session.query(JobDescription).order_by(JobDescription.id.desc()).all()
session.close()

if not jobs:
    st.info("No job roles available yet. Please check back later.")
    st.stop()

unique_jobs = list({j.title: j for j in jobs}.values())

# ==============================================================================
# 1. RESUME UPLOAD
# ==============================================================================
st.subheader("1. Upload Your Resume")
uploaded_file = st.file_uploader("Upload your resume (PDF or DOCX)", type=["pdf", "docx"])

candidate_choice = None
if uploaded_file is not None:
    if st.session_state.get("uploaded_filename") != uploaded_file.name:
        with st.spinner("Processing your resume..."):
            suffix = Path(uploaded_file.name).suffix
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(uploaded_file.getbuffer())
                tmp_path = tmp.name
            try:
                text = extract_text(tmp_path)
                up_session = SessionLocal()
                try:
                    cand_obj = ingest_resume(up_session, uploaded_file.name, text)
                    st.session_state["uploaded_candidate_id"] = cand_obj.id
                    st.session_state["uploaded_candidate_name"] = cand_obj.name
                    st.session_state["uploaded_candidate_email"] = cand_obj.email
                    st.session_state["uploaded_filename"] = uploaded_file.name
                finally:
                    up_session.close()
            except (UnsupportedFileType, ValueError) as e:
                st.error(f"Could not process resume: {e}")
            finally:
                os.unlink(tmp_path)

    if "uploaded_candidate_id" in st.session_state:
        st.success(
            f"Resume processed: {st.session_state['uploaded_candidate_name']} "
            f"({st.session_state['uploaded_candidate_email']})"
        )
        lookup_session = SessionLocal()
        candidate_choice = lookup_session.get(Candidate, st.session_state["uploaded_candidate_id"])
        lookup_session.close()

# ==============================================================================
# 2. JOB ROLE SELECTION
# ==============================================================================
st.subheader("2. Select Job Role")
job_choice = st.selectbox(
    "Job Role Applying For:",
    options=unique_jobs,
    format_func=lambda j: j.title if j else "",
)

if not candidate_choice:
    st.info("Upload your resume above to continue.")
    st.stop()
if not job_choice:
    st.warning("Please select a job role.")
    st.stop()

chat_key = f"candidate_chat_{candidate_choice.id}_{job_choice.id}"
gap_key = f"candidate_gap_{candidate_choice.id}_{job_choice.id}"
ats_key = f"candidate_ats_{candidate_choice.id}_{job_choice.id}"

# ==============================================================================
# 3. PRE-INTERVIEW STEP
# ==============================================================================
if chat_key not in st.session_state:
    st.divider()
    st.subheader("3. Profile Match & Skill Gap Analysis")

    if st.button("📊 Calculate Match Score & Analyze Skill Gap", type="secondary"):
        status = st.empty()
        calc_session = SessionLocal()
        try:
            status.info("Step 1/2: Computing ATS match score...")
            ranked = match_job_to_candidates(calc_session, job_choice, top_n=10)
            cand_match = next((r for r in ranked if r["candidate"].id == candidate_choice.id), None)
            ats_score = cand_match["score"] if cand_match else 0.0
            st.session_state[ats_key] = ats_score
            status.info("Step 2/2: Analyzing skill gap with LLM...")

            try:
                skill_gap = generate_skill_gap(calc_session, candidate_choice, job_choice)
            except Exception as e:
                status.empty()
                st.error(f"Skill-gap error: {e}")
                skill_gap = None
            st.session_state[gap_key] = skill_gap
            status.empty()
        except Exception as e:
            status.empty()
            st.error(f"Match score error: {e}")
        finally:
            calc_session.close()

    if ats_key in st.session_state and gap_key in st.session_state:
        ats_val = st.session_state[ats_key] * 100
        st.metric(label="🎯 Resume ATS Match Score", value=f"{ats_val:.1f}%")
        st.progress(st.session_state[ats_key])

        skill_gap = st.session_state[gap_key]
        if skill_gap:
            st.info(f"**Resume Summary:** {skill_gap.get('overall_summary', '')}")

            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**✅ Matched Skills:**")
                for s in skill_gap.get("matched_skills", []):
                    st.write(f"- {s}")
            with c2:
                st.markdown("**⚠️ Identified Skill Gaps:**")
                for g in skill_gap.get("missing_skills", []):
                    st.write(f"- **{g.get('skill')}** ({g.get('priority')}): {g.get('reason', '')}")

            st.markdown("**📚 Your Learning Roadmap:**")
            roadmap_steps = skill_gap.get("roadmap", [])
            if roadmap_steps:
                for step in roadmap_steps:
                    resources = ", ".join(step.get("resources", []))
                    st.write(
                        f"{step.get('step')}. **{step.get('topic')}** "
                        f"(~{step.get('estimated_weeks')} weeks) - {resources}"
                    )
            else:
                st.caption("No roadmap steps available.")
        else:
            st.warning("Skill-gap analysis could not be generated. You can still proceed.")

        st.divider()
        st.error("🔒 Proctoring Enabled: Copy-Paste is blocked & Tab switching is monitored.")

        if st.button("🚀 Start Assessment", type="primary"):
            with st.spinner("Initializing AI Interviewer..."):
                first_msg = get_next_bot_message(
                    candidate_choice, job_choice, [], skill_gap=st.session_state.get(gap_key)
                )

            st.session_state[chat_key] = {
                "history": [{"role": "assistant", "content": first_msg}],
                "completed": False
            }
            st.rerun()

# ==============================================================================
# 4. INTERVIEW CHAT SCREEN
# ==============================================================================
else:
    inject_proctoring_system()

    chat_state = st.session_state[chat_key]
    skill_gap = st.session_state.get(gap_key)

    st.divider()
    st.subheader("💬 AI Screening Assessment (Proctored)")
    st.caption("Active Proctoring Session - Type your responses directly.")

    for msg in chat_state["history"]:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    if not chat_state["completed"]:
        answer = st.chat_input("Type your answer directly...")
        if answer:
            chat_state["history"].append({"role": "user", "content": answer})
            asked_so_far = sum(1 for m in chat_state["history"] if m["role"] == "assistant")
            force_close = asked_so_far >= MAX_QUESTIONS

            with st.spinner("Generating next targeted question..."):
                next_msg = get_next_bot_message(
                    candidate_choice, job_choice, chat_state["history"],
                    skill_gap=skill_gap, force_close=force_close,
                )

            chat_state["history"].append({"role": "assistant", "content": next_msg})

            if force_close:
                chat_state["completed"] = True
                save_session = SessionLocal()
                try:
                    candidate = save_session.get(Candidate, candidate_choice.id)
                    job = save_session.get(JobDescription, job_choice.id)
                    save_interview(save_session, candidate, chat_state["history"], job=job)
                finally:
                    save_session.close()
            st.rerun()
    else:
        st.balloons()
        st.success("Assessment Completed! Responses submitted for HR review.")
