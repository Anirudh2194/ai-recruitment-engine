"""CLI: generate a skill-gap roadmap for each candidate against the most
recently ingested job description.

Usage:
    python -m app.modules.skill_gap.generate_cli
"""
import json

from app.db.database import SessionLocal, init_db
from app.db.models import Candidate, JobDescription
from app.modules.skill_gap.generator import generate_skill_gap


def main():
    init_db()
    session = SessionLocal()
    try:
        job = session.query(JobDescription).order_by(JobDescription.id.desc()).first()
        if job is None:
            print("No job descriptions found. Run app.modules.matching.ingest_job first.")
            return

        candidates = session.query(Candidate).all()
        if not candidates:
            print("No candidates found. Run app.modules.resume_parser.ingest first.")
            return

        print(f"Generating skill-gap roadmaps against job: {job.title}\n")
        for candidate in candidates:
            print(f"=== {candidate.name} <{candidate.email}> ===")
            try:
                result = generate_skill_gap(session, candidate, job)
                print(json.dumps(result, indent=2))
            except ValueError as e:
                print(f"  ✗ Failed: {e}")
            print()
    finally:
        session.close()


if __name__ == "__main__":
    main()
