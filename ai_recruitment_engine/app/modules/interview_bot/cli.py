"""CLI: run a screening interview in the terminal for the most recent
job description against a candidate you pick by email.

Usage:
    python -m app.modules.interview_bot.cli
"""
from app.db.database import SessionLocal, init_db
from app.db.models import Candidate, JobDescription
from app.modules.interview_bot.bot import get_next_bot_message, save_interview, MAX_QUESTIONS


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

        print(f"Job: {job.title}\n")
        for i, c in enumerate(candidates, 1):
            print(f"  {i}. {c.name} <{c.email}>")
        choice = input("\nPick a candidate number: ").strip()
        candidate = candidates[int(choice) - 1]

        print(f"\n--- Screening interview: {candidate.name} ---")
        print("(type your answers; Ctrl+C to abort without saving)\n")

        history: list[dict] = []
        for turn in range(MAX_QUESTIONS + 1):
            bot_message = get_next_bot_message(candidate, job, history)
            print(f"Bot: {bot_message}\n")
            history.append({"role": "assistant", "content": bot_message})

            if turn == MAX_QUESTIONS:
                break

            answer = input("You: ").strip()
            history.append({"role": "user", "content": answer})
            print()

        save_interview(session, candidate, history)
        print("Interview saved.")
    finally:
        session.close()


if __name__ == "__main__":
    main()
