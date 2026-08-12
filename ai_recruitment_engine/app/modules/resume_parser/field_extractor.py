"""Lightweight heuristic extraction of structured fields from raw resume text.

This is intentionally simple (regex + first-line heuristics) rather than
another LLM call — keeps ingestion fast and free. Swap in an LLM-based
extractor later if accuracy on messy resumes becomes a problem.
"""
import re

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")


def extract_email(text: str) -> str | None:
    match = EMAIL_RE.search(text)
    return match.group(0) if match else None


def extract_name(text: str, filename: str) -> str:
    """Best-effort: use the first non-empty line if it looks like a name,
    otherwise fall back to the filename."""
    for line in text.splitlines():
        line = line.strip()
        if 2 <= len(line.split()) <= 4 and not EMAIL_RE.search(line) and len(line) < 60:
            return line
    return filename.rsplit(".", 1)[0].replace("_", " ").title()
