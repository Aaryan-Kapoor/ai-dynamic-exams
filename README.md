# AI-Powered Adaptive Examination System

Local-first adaptive exams for universities:

- **No registration**: users are pre-created in the database.
- **Teacher dashboard**: upload lectures (PDF/images), configure exam settings per department + grade.
- **Student exam**: timed, adaptive questions; stops early when performance/time thresholds are hit.
- **SQLite** for the relational database + **local vector index stored in SQLite** (no separate service).
- **Local LLM** via an **OpenAI-compatible** endpoint (`LLM_BASE_URL` in `.env`).

## Quickstart

1) Create a virtualenv and install deps:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2) Create `.env`:

```bash
cp .env.example .env
```

3) Initialize + seed demo data:

```bash
python -m scripts.seed_demo
```

4) Run the web app:

```bash
python -m uvicorn app.main:app --reload
```

Open `http://localhost:8000`.

## Demo accounts

Seed script creates:

- **Admin**: `admin` / `admin123`
- **Teacher**: `t1001` / `teacher123`
- **Student**: `s2001` / `student123`

## Local LLM configuration

This project calls an OpenAI-compatible Chat Completions API.

Example (Ollama):

1) Run Ollama.
2) Set in `.env`:

```env
LLM_BASE_URL="http://localhost:11434/v1"
LLM_MODEL="llama3.1"
LLM_API_KEY="ollama"
```

If you don’t have a local LLM running, set:

```env
LLM_PROVIDER="mock"
```

or keep `LLM_FALLBACK_TO_MOCK=true`.

## Neural embeddings (MiniLM)

Lecture retrieval uses **`sentence-transformers/all-MiniLM-L6-v2`** by default (configured in `.env`).

- If you change `EMBEDDING_PROVIDER` / `EMBEDDING_MODEL_NAME` on an existing database, rebuild embeddings:
  - `python -m scripts.reindex_embeddings`

## Docker (optional)

```bash
cp .env.example .env
docker compose up --build
```

Data persists in `./data` (SQLite DB + uploads).

## OCR for images (optional)

Image text extraction uses `pytesseract`. You must install the `tesseract` binary.

Ubuntu/Debian:

```bash
sudo apt-get update && sudo apt-get install -y tesseract-ocr
```

## Project layout

- `app/main.py`: FastAPI app + routes
- `app/models.py`: SQLAlchemy models (SQLite)
- `app/services/llm.py`: Local LLM client (OpenAI-compatible) + mock fallback
- `app/services/lecture_processing.py`: PDF parsing + optional OCR + chunking
- `app/services/vector_index.py`: Simple vector index stored in SQLite (cosine similarity)
- `scripts/seed_demo.py`: creates colleges/departments + demo users
