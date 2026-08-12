"""CLI: parse + embed every resume in data/resumes/, print a summary.

Usage:
    python -m app.modules.resume_parser.ingest
"""
from app.config import settings
from app.db.database import SessionLocal, init_db
from app.modules.resume_parser.parser import extract_text, UnsupportedFileType
from app.modules.resume_parser.embedder import ingest_resume


def main():
    init_db()
    settings.RESUME_DIR.mkdir(parents=True, exist_ok=True)

    resume_files = [
        f for f in settings.RESUME_DIR.iterdir()
        if f.suffix.lower() in (".pdf", ".docx")
    ]
    if not resume_files:
        print(f"No resumes found in {settings.RESUME_DIR}. Add .pdf or .docx files and rerun.")
        return

    session = SessionLocal()
    ok, failed = 0, 0
    try:
        for file_path in resume_files:
            try:
                text = extract_text(file_path)
                candidate = ingest_resume(session, str(file_path), text)
                print(f"  ✓ {file_path.name}  ->  {candidate.name} <{candidate.email}>")
                ok += 1
            except (UnsupportedFileType, ValueError) as e:
                print(f"  ✗ {file_path.name}: {e}")
                failed += 1
    finally:
        session.close()

    print(f"\nIngested {ok} resume(s), {failed} failed.")


if __name__ == "__main__":
    main()
