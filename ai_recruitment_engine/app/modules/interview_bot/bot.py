"""Conversational AI Screening Bot.

A LangGraph-driven chat node that asks screening questions based on a
candidate's resume and a job description, one turn at a time. The UI
(Streamlit or CLI) drives the conversation turn-by-turn; this module
just decides what the bot says next given the history so far.
"""
from typing import TypedDict

from langgraph.graph import StateGraph, END

from app.core.llm_provider import chat
from app.db.models import Candidate, Interview, JobDescription
from sqlalchemy.orm import Session

MAX_QUESTIONS = 5


class InterviewState(TypedDict):
    messages: list[dict]


def build_system_prompt(candidate: Candidate, job: JobDescription, skill_gap: dict | None = None) -> str:
    gap_section = ""
    if skill_gap:
        missing = skill_gap.get("missing_skills", [])
        if missing:
            gap_lines = "\n".join(
                f"- {g.get('skill')} (priority: {g.get('priority')}) — {g.get('reason')}"
                for g in missing
            )
            gap_section = f"""
KNOWN SKILL GAPS (from an automated analysis — do NOT reveal this list or \
mention it was computed; use it only to decide what to probe):
{gap_lines}

Prioritize at least 1-2 questions that probe the high-priority gaps above, to \
see if the candidate has relevant experience the resume didn't capture.
"""

    return f"""You are a professional, friendly technical recruiter conducting an initial \
screening interview by chat for the role of "{job.title}".

JOB DESCRIPTION:
{job.description_text}

CANDIDATE RESUME:
{candidate.resume_text}
{gap_section}
Rules:
- Ask exactly ONE question per turn, tailored to gaps or highlights in the resume \
relative to the job description.
- Keep each message short (2-4 sentences), conversational, and professional.
- Cover: technical skills relevant to the role, a past project, and role/team fit — \
across the interview, not all at once.
- Do not repeat a question already asked.
- After {MAX_QUESTIONS} questions have been asked and answered, instead of asking another \
question, thank the candidate, briefly summarize their fit for the role in 2-3 sentences, \
and say the screening is complete. Do not ask further questions after that point.
"""


def _respond_node(state: InterviewState) -> InterviewState:
    reply = chat(state["messages"], temperature=0.4)
    state["messages"].append({"role": "assistant", "content": reply})
    return state


_graph = StateGraph(InterviewState)
_graph.add_node("respond", _respond_node)
_graph.set_entry_point("respond")
_graph.add_edge("respond", END)
_compiled_graph = _graph.compile()


def get_next_bot_message(
    candidate: Candidate,
    job: JobDescription,
    history: list[dict],
    skill_gap: dict | None = None,
) -> str:
    """history: prior turns as [{"role": "assistant"|"user", "content": ...}, ...]
    (no system message — this function adds it). Returns the bot's next message."""
    messages = [{"role": "system", "content": build_system_prompt(candidate, job, skill_gap)}] + history
    result = _compiled_graph.invoke({"messages": messages})
    return result["messages"][-1]["content"]


def generate_closing_summary(candidate: Candidate, job: JobDescription, history: list[dict]) -> str:
    """Generate a concise, HR-facing assessment of the candidate based on the
    full Q&A transcript — separate from whatever the bot said conversationally
    at the end, which is often just a generic farewell."""
    transcript_text = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in history)
    messages = [
        {
            "role": "system",
            "content": (
                f"You are a technical recruiter. Based on the screening interview transcript below "
                f"for the role of \"{job.title}\", write a concise 2-3 sentence assessment of the "
                f"candidate's fit for this role — mention specific strengths or gaps they revealed in "
                f"their answers. Write it for the hiring manager, not the candidate. Do not include a "
                f"greeting or sign-off, just the assessment."
            ),
        },
        {"role": "user", "content": transcript_text},
    ]
    return chat(messages, temperature=0.3)


def save_interview(session: Session, candidate: Candidate, history: list[dict], status: str = "completed") -> Interview:
    """Persist the transcript to the database, plus a separate HR-facing
    closing summary appended as its own entry (never shown to the candidate,
    since it's added to a copy of the list, not the one driving the chat UI)."""
    try:
        job = session.query(JobDescription).order_by(JobDescription.id.desc()).first()
        summary_text = generate_closing_summary(candidate, job, history) if job else None
    except Exception:
        summary_text = None

    full_transcript = list(history)
    if summary_text:
        full_transcript.append({"role": "summary", "content": summary_text})

    interview = Interview(
        candidate_id=candidate.id,
        transcript_json=full_transcript,
        status=status,
    )
    session.add(interview)
    session.commit()
    session.refresh(interview)
    return interview