"""Semantic Match Engine.

Embeds a job description with the same model used for resumes, then scores
it against every resume already sitting in ChromaDB (rather than only
against candidates fetched from SQL first) — that keeps matching correct
even if a candidate somehow exists in one store but not the other.
"""
import uuid

from sqlalchemy.orm import Session

from app.core.embeddings import embed_text
from app.core.vector_store import upsert, query
from app.db.models import Candidate, JobDescription, MatchScore


def ingest_job(session: Session, title: str, description_text: str) -> JobDescription:
    """Embed + persist a job description. Returns the JobDescription row."""
    vector_id = str(uuid.uuid4())
    embedding = embed_text(description_text)

    upsert(
        doc_id=vector_id,
        embedding=embedding,
        text=description_text,
        metadata={"type": "job", "title": title},
    )

    job = JobDescription(
        title=title,
        description_text=description_text,
        vector_id=vector_id,
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def match_job_to_candidates(session: Session, job: JobDescription, top_n: int = 10) -> list[dict]:
    """Return candidates ranked by semantic similarity to the job description.

    Each result: {"candidate": Candidate, "score": float in [0, 1]}
    Also persists a MatchScore row per result.
    """
    job_embedding = embed_text(job.description_text)

    results = query(
        embedding=job_embedding,
        n_results=top_n,
        where={"type": "resume"},
    )

    ranked = []
    ids = results.get("ids", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for vector_id, distance in zip(ids, distances):
        candidate = session.query(Candidate).filter_by(vector_id=vector_id).one_or_none()
        if candidate is None:
            continue

        # ChromaDB with hnsw:space="cosine" returns cosine *distance*;
        # similarity = 1 - distance, clamped to [0, 1] for display safety.
        similarity = max(0.0, min(1.0, 1 - distance))

        match = MatchScore(
            candidate_id=candidate.id,
            job_id=job.id,
            similarity_score=similarity,
        )
        session.add(match)
        ranked.append({"candidate": candidate, "score": similarity})

    session.commit()
    ranked.sort(key=lambda r: r["score"], reverse=True)
    return ranked
