"""Turn a parsed resume into a vector embedding and persist it:
- ChromaDB: the embedding, for semantic search
- SQL database: the candidate record + raw text
"""
import uuid

from sqlalchemy.orm import Session

from app.core.embeddings import embed_text
from app.core.vector_store import upsert
from app.db.models import Candidate
from app.modules.resume_parser.field_extractor import extract_email, extract_name


def ingest_resume(session: Session, file_path: str, raw_text: str) -> Candidate:
    """Parse + embed a single resume and persist it. Returns the Candidate row."""
    filename = file_path.split("/")[-1]
    email = extract_email(raw_text) or f"unknown+{uuid.uuid4().hex[:8]}@example.com"
    name = extract_name(raw_text, filename)
    vector_id = str(uuid.uuid4())

    embedding = embed_text(raw_text)
    upsert(
        doc_id=vector_id,
        embedding=embedding,
        text=raw_text,
        metadata={"type": "resume", "filename": filename, "email": email},
    )

    candidate = session.query(Candidate).filter_by(email=email).one_or_none()
    if candidate is None:
        candidate = Candidate(
            name=name,
            email=email,
            resume_filename=filename,
            resume_text=raw_text,
            vector_id=vector_id,
        )
        session.add(candidate)
    else:
        candidate.resume_text = raw_text
        candidate.resume_filename = filename
        candidate.vector_id = vector_id

    session.commit()
    session.refresh(candidate)
    return candidate
