"""CLI: ingest every .txt job description in data/jobs/, match against
all ingested resumes, and print a ranked candidate list.

Usage:
    python -m app.modules.matching.ingest_job
"""
from pathlib import Path

from app.config import settings, BASE_DIR
from app.db.database import SessionLocal, init_db
from app.modules.matching.matcher import ingest_job, match_job_to_candidates

JOBS_DIR = BASE_DIR / "data" / "jobs"


def main():
    init_db()
    JOBS_DIR.mkdir(parents=True, exist_ok=True)

    job_files = list(JOBS_DIR.glob("*.txt"))
    if not job_files:
        print(f"No job descriptions found in {JOBS_DIR}. Add a .txt file (title = filename) and rerun.")
        return

    session = SessionLocal()
    try:
        for file_path in job_files:
            title = file_path.stem.replace("_", " ").title()
            description = file_path.read_text(encoding="utf-8").strip()
            if not description:
                print(f"  ✗ {file_path.name}: empty file, skipped")
                continue

            job = ingest_job(session, title, description)
            print(f"\n=== {job.title} ===")

            ranked = match_job_to_candidates(session, job, top_n=10)
            if not ranked:
                print("  No candidates ingested yet — run the resume ingest pipeline first.")
                continue

            for i, r in enumerate(ranked, 1):
                c = r["candidate"]
                print(f"  {i}. {c.name} <{c.email}>  —  {r['score']*100:.1f}% match")
    finally:
        session.close()


if __name__ == "__main__":
    main()
