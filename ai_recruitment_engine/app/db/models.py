import datetime as dt

from sqlalchemy import String, Text, DateTime, ForeignKey, Float, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    resume_filename: Mapped[str] = mapped_column(String(512))
    resume_text: Mapped[str] = mapped_column(Text)
    vector_id: Mapped[str] = mapped_column(String(255))  # ChromaDB doc id
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    match_scores: Mapped[list["MatchScore"]] = relationship(back_populates="candidate")
    interviews: Mapped[list["Interview"]] = relationship(back_populates="candidate")


class JobDescription(Base):
    __tablename__ = "job_descriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    description_text: Mapped[str] = mapped_column(Text)
    vector_id: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    match_scores: Mapped[list["MatchScore"]] = relationship(back_populates="job")


class MatchScore(Base):
    __tablename__ = "match_scores"

    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"))
    job_id: Mapped[int] = mapped_column(ForeignKey("job_descriptions.id"))
    similarity_score: Mapped[float] = mapped_column(Float)
    skill_gap_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    candidate: Mapped["Candidate"] = relationship(back_populates="match_scores")
    job: Mapped["JobDescription"] = relationship(back_populates="match_scores")


class Interview(Base):
    __tablename__ = "interviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"))
    transcript_json: Mapped[dict] = mapped_column(JSON)  # list of {role, content}
    status: Mapped[str] = mapped_column(String(50), default="in_progress")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    candidate: Mapped["Candidate"] = relationship(back_populates="interviews")
