from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def init_db():
    """Create all tables, then auto-seed jobs/resumes if the DB is empty —
    this makes cloud deployments (where you can't run CLI commands) work
    out of the box, using whatever files are committed under data/."""
    from app.db import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    _auto_seed()


def _auto_seed():
    from app.db.models import Candidate, JobDescription

    session = SessionLocal()
    try:
        if session.query(JobDescription).count() == 0:
            jobs_dir = settings.RESUME_DIR.parent / "jobs"
            if jobs_dir.exists():
                from app.modules.matching.matcher import ingest_job
                for f in sorted(jobs_dir.glob("*.txt")):
                    text = f.read_text(encoding="utf-8").strip()
                    if text:
                        title = f.stem.replace("_", " ").title()
                        ingest_job(session, title, text)

        if session.query(Candidate).count() == 0:
            if settings.RESUME_DIR.exists():
                from app.modules.resume_parser.parser import extract_text, UnsupportedFileType
                from app.modules.resume_parser.embedder import ingest_resume
                for f in sorted(settings.RESUME_DIR.iterdir()):
                    if f.suffix.lower() in (".pdf", ".docx"):
                        try:
                            text = extract_text(f)
                            ingest_resume(session, str(f), text)
                        except (UnsupportedFileType, ValueError):
                            pass
    finally:
        session.close()