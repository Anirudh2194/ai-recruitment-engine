# AI-Driven Smart Recruitment Engine

Automated resume parsing, semantic skill matching, skill-gap roadmap generation,
and a GenAI screening interview bot.

## Architecture

```
app/
  core/
    embeddings.py       # Sentence-Transformers wrapper (local, free)
    vector_store.py      # ChromaDB wrapper
    llm_provider.py       # Swappable LLM backend (Ollama / OpenAI / Anthropic)
  db/
    models.py             # SQLAlchemy models (candidates, jobs, interviews)
    database.py            # Engine/session setup (PostgreSQL or SQLite fallback)
  modules/
    resume_parser/          # Stage 1: PDF/DOCX -> text -> embeddings -> ChromaDB
    matching/                 # Stage 2: job description vs. resume similarity scoring
    skill_gap/                 # Stage 3: LLM-generated skill-gap roadmap (JSON)
    interview_bot/               # Stage 4: LangGraph conversational screening bot
  ui/
    streamlit_app.py             # Recruiter dashboard + candidate chat
data/
  resumes/                        # Drop sample PDF/DOCX resumes here
  chroma_db/                       # Persisted vector store (auto-created)
```

## Setup

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # fill in DB url / API keys if using hosted LLMs
```

### LLM backend

Default is **local Ollama** (free, no API key):

```bash
# install Ollama from https://ollama.com, then:
ollama pull llama3:8b
```

To use a hosted model instead, set in `.env`:
```
LLM_PROVIDER=openai        # or anthropic
OPENAI_API_KEY=...
```

### Database

Defaults to local SQLite (`data/app.db`) so you can run everything with zero
setup. To use PostgreSQL (recommended for the production target in the spec),
set `DATABASE_URL` in `.env`, e.g.
`postgresql://user:pass@localhost:5432/recruitment`.

## Running

```bash
# 1. Ingest resumes (parses + embeds every file in data/resumes/)
python -m app.modules.resume_parser.ingest

# 2. Launch the dashboard
streamlit run app/ui/streamlit_app.py
```

## Build stages

1. ✅ Scaffolding — repo, config, DB models
2. ✅ Resume Parsing & Embedding Pipeline
3. ✅ Semantic Match Engine
4. ✅ Skill-Gap & Roadmap Generator
5. ✅ Conversational AI Screening Bot
6. ✅ Streamlit dashboard — candidates, matching, skill-gap, interview chat all live
7. ⬜ Integration polish, sample data, final docs

## Two separate pages (HR vs candidate)

The dashboard is split into two Streamlit pages so candidates never see
rankings, other candidates, or skill-gap reports:

- **HR Dashboard** (`app/ui/streamlit_app.py`, the main page) — resume
  review, job matching/ranking, skill-gap roadmaps. Internal use only.
- **Candidate Interview** (`app/ui/pages/1_Candidate_Interview.py`,
  appears in the sidebar) — the candidate picks their email + the job
  they applied for, then goes through the screening chat. Nothing about
  ranking or other candidates is visible here.

Run both with a single command — Streamlit auto-discovers `pages/`:
```bash
streamlit run app/ui/streamlit_app.py
```
Then use the sidebar to switch between "streamlit app" (HR) and
"Candidate Interview".

**Note:** for this project, the candidate identifies themselves with a
dropdown of already-ingested candidates. In a production deployment
you'd instead send each candidate a unique link (e.g. with a token in
the URL) so they only ever see their own interview.

## Screening interview

**Via the dashboard** — go to the "Candidate Interview" page (sidebar), pick a
candidate + job, and click "Begin Interview". A chat window opens; type
answers as if you were the candidate. After a few questions the bot wraps
up and the transcript is saved to the database automatically.

**Via terminal** (useful for quick testing without the UI):
```bash
python -m app.modules.interview_bot.cli
```

## Matching a job description

Two ways:

**A. Via the dashboard** — run `streamlit run app/ui/streamlit_app.py`, scroll to
"Match Candidates to a Job", paste a title + description, click the button.
Then click "Generate Skill-Gap Roadmap" under any candidate to get an
LLM-generated skill gap + learning plan.

**B. Via file** — drop a `.txt` file into `data/jobs/` (filename becomes the
job title) and run:
```bash
python -m app.modules.matching.ingest_job
python -m app.modules.skill_gap.generate_cli
```

The skill-gap step calls your configured LLM (Ollama by default — make sure
`ollama serve` is running / the Ollama app is open) and returns matched
skills, missing skills with priority, and a week-by-week learning roadmap.
