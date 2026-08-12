"""Extract raw text from PDF or DOCX resumes.

Scope note (per project spec, slide 7): text-based resumes only.
Scanned/image-only PDFs and video/audio formats are out of scope.
"""
from pathlib import Path

from pypdf import PdfReader
from docx import Document


class UnsupportedFileType(Exception):
    pass


def extract_text(file_path: str | Path) -> str:
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        return _extract_pdf(path)
    elif suffix in (".docx",):
        return _extract_docx(path)
    else:
        raise UnsupportedFileType(f"Unsupported resume format: {suffix}")


def _extract_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    pages = [page.extract_text() or "" for page in reader.pages]
    text = "\n".join(pages).strip()
    if not text:
        raise ValueError(
            f"No extractable text in {path.name} — likely a scanned/image PDF, "
            "which is out of scope for this pipeline."
        )
    return text


def _extract_docx(path: Path) -> str:
    doc = Document(str(path))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
