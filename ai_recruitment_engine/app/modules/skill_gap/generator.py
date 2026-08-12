"""Skill-Gap & Roadmap Generator.

Compares a candidate's resume against a job description via the LLM
(Ollama by default — see app/core/llm_provider.py) and returns a
structured JSON roadmap: missing skills, priority, and a suggested
learning order/timeline.
"""
import json
import re

from sqlalchemy.orm import Session

from app.core.llm_provider import chat
from app.db.models import Candidate, JobDescription, MatchScore

SYSTEM_PROMPT = """You are a technical recruiter's assistant. Given a candidate's \
resume text and a job description, identify the skill gap and produce a learning \
roadmap.

Respond with ONLY valid JSON (no markdown fences, no commentary) in exactly this shape:
{
  "matched_skills": ["skill1", "skill2"],
  "missing_skills": [
    {"skill": "string", "priority": "high|medium|low", "reason": "string"}
  ],
  "roadmap": [
    {"step": 1, "topic": "string", "estimated_weeks": 2, "resources": ["string"]}
  ],
  "overall_summary": "2-3 sentence summary of the candidate's readiness for this role"
}
"""


def _extract_json(raw: str) -> dict:
    """LLMs sometimes wrap JSON in markdown fences or add stray text — strip that."""
    raw = raw.strip()
    raw = re.sub(r"^```(json)?", "", raw).strip()
    raw = re.sub(r"```$", "", raw).strip()
    # Fallback: grab the outermost {...} block if there's still extra text around it.
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        raw = match.group(0)
    return json.loads(raw)


def generate_skill_gap(session: Session, candidate: Candidate, job: JobDescription) -> dict:
    """Call the LLM to produce a skill-gap roadmap, save it on the MatchScore row
    (if one exists for this candidate+job), and return the parsed JSON dict."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"JOB TITLE: {job.title}\n\n"
                f"JOB DESCRIPTION:\n{job.description_text}\n\n"
                f"CANDIDATE RESUME:\n{candidate.resume_text}"
            ),
        },
    ]

    raw_response = chat(messages, temperature=0.2)

    try:
        result = _extract_json(raw_response)
    except (json.JSONDecodeError, AttributeError) as e:
        raise ValueError(
            f"LLM did not return valid JSON. Raw response was:\n{raw_response}"
        ) from e

    match = (
        session.query(MatchScore)
        .filter_by(candidate_id=candidate.id, job_id=job.id)
        .order_by(MatchScore.id.desc())
        .first()
    )
    if match is not None:
        match.skill_gap_json = result
        session.commit()

    return result
