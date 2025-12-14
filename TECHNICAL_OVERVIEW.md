# Technical Overview — AI-Powered Adaptive Examination System

## Architecture

- **Web framework**: FastAPI + Jinja2 templates (server-rendered HTML).
- **Session auth**: `SessionMiddleware` stores `user_id` in a signed cookie-backed session.
- **Relational DB**: SQLite via SQLAlchemy ORM for users, colleges/departments, lecture materials/chunks, exam configs, attempts, questions, and answers.
- **Vector retrieval**: A lightweight embedding + similarity search implemented in Python and **stored in SQLite** (no separate vector DB service).
- **LLM**: OpenAI-compatible *Chat Completions* endpoint, configurable via `.env` (`LLM_BASE_URL`, `LLM_MODEL`, etc.), with optional mock fallback.

## Main entrypoints

- `app/main.py`: FastAPI app setup, session middleware, static mount, router registration, table creation on startup.
- Routers:
  - `app/routers/auth.py`: `/login`, `/logout`, and `/` redirect logic by role.
  - `app/routers/teacher.py`: teacher dashboard, exam configuration, lecture upload + indexing, results view.
  - `app/routers/student.py`: student home, start/resume exam, answer flow, end exam, results.

## Data model (SQLite)

Key tables (see `app/models.py`):

- `colleges`, `departments`: academic structure.
- `users`: pre-created accounts. Fields include `role`, `college_id`, `grade_level` (students), `is_active`.
- `user_departments`: many-to-many mapping so teachers (and admins/heads) can be associated with multiple departments.
- `exam_configs`: one config per `(department_id, grade_level)` (duration, attempts, stop rules, difficulty range).
- Lecture ingestion:
  - `lecture_materials`: uploaded file metadata + extracted text.
  - `lecture_chunks`: chunked text per material, keyed to department + grade.
  - `lecture_chunk_embeddings`: binary-packed embedding vector for each chunk.
- Exam runtime:
  - `exam_attempts`: per-student attempt with start/end times, stop reason, counters, final score + rating.
  - `exam_questions`: generated question + stored “ideal answer” + the retrieval context used.
  - `exam_answers`: student answer + grading output (correctness, feedback) + time taken per question.

## Authentication & RBAC

- Login uses **only** `university_id` + `password`. Role/college/departments/grade are read from the DB.
- Password hashing: `passlib` using `pbkdf2_sha256` (`app/auth.py`).
- Page authorization:
  - Students: `Role.student`
  - Teachers: `Role.teacher`, plus elevated roles `head`, `college_admin`, `system_admin`
  - Teacher department access is validated server-side in `app/routers/teacher.py`.

## Teacher flow (upload + configure)

1. Teacher opens `/teacher`.
2. Teacher selects department + grade level.
3. Teacher edits configuration (duration, attempts, stop rules, difficulty range) → saved in `exam_configs`.
4. Teacher uploads lecture files at `/teacher/lectures/upload`:
   - Saved under `UPLOAD_DIR/<department>/<grade>/...`
   - Text extraction:
     - PDF: `pypdf`
     - Images: OCR with `pytesseract` if the `tesseract` binary is installed
   - Text is chunked and written into `lecture_chunks`.
   - Embeddings are created and stored in `lecture_chunk_embeddings`.

## Student flow (adaptive exam)

1. Student opens `/student`:
   - System finds the student’s department (currently: first assigned department) + `grade_level`.
   - Loads the active `exam_config` for that department/grade.
2. Student starts an attempt at `/student/exam/start`:
   - Enforces `max_attempts`.
   - Creates an `exam_attempts` row.
   - Generates the first question using retrieval + LLM.
3. Student answers at `/student/exam/answer`:
   - Server computes `time_taken_seconds` since the question was shown.
   - LLM grades and returns:
     - `correctness` (0..1)
     - `is_correct`
     - `feedback`
   - Attempt counters update (`questions_answered`, `consecutive_incorrect`, etc.).
4. Auto-stop rules (server-side):
   - Time limit reached
   - Too many consecutive incorrect answers
   - A question took longer than `stop_slow_seconds`
   - Max questions reached
5. Finalization:
   - Computes score and rating and stores them in `exam_attempts`.
   - Student sees `/student/results/<attempt_id>`.
6. Retakes:
   - “AGAIN” simply starts a new attempt until `max_attempts` is reached.
   - Previously asked questions are added to an “avoid list” when generating new questions.

## LLM integration

Implemented in `app/services/llm.py`:

- **Provider**: `openai_compat` (default) or `mock`.
- **OpenAI-compatible** uses `POST {LLM_BASE_URL}/chat/completions` with:
  - `model`, `messages`, `temperature`, `max_tokens`
- **Robustness**:
  - The generator and grader request strict JSON; response parsing attempts to extract a JSON object.
  - Optional fallback: `FallbackLLMClient` wraps a real client and falls back to `MockLLMClient` if calls fail.

## Vector retrieval system (how embeddings work)

The app uses embeddings for **retrieval** (RAG-style): selecting the most relevant lecture chunks to pass as context into question generation and grading.

By default it uses a real embedding model: **`sentence-transformers/all-MiniLM-L6-v2`** (local, downloaded on first use). A hash-based fallback provider also exists for fully offline/no-ML environments.

### 1) Chunk creation

- Extracted lecture text is split into overlapping chunks by character count (`CHUNK_SIZE_CHARS`, `CHUNK_OVERLAP_CHARS`) in `app/services/lecture_processing.py`.
- Each chunk is stored in `lecture_chunks` with `(department_id, grade_level)` for filtering.

### 2) Embedding generation

Implemented in `app/services/embeddings.py` and wired through `app/services/vector_index.py`:

- **Sentence-Transformers provider** (`EMBEDDING_PROVIDER=sentence_transformers`):
  - Loads `SentenceTransformer(EMBEDDING_MODEL_NAME)` once per process.
  - Encodes text with `normalize_embeddings=True` so cosine similarity becomes a dot product.
  - Uses float32 vectors and stores them as bytes in SQLite.
- **Hash provider** (`EMBEDDING_PROVIDER=hash`):
  - A deterministic token-hashing embedding (fast lexical fallback).

### 3) Storage format

- Float vectors are packed with `array('f')` into bytes (`pack_embedding`) and stored in SQLite as `LargeBinary` (`lecture_chunk_embeddings.embedding`).

### 4) Similarity search

- `query_similar_chunks(...)`:
  - Embeds the query text using the same function.
  - Loads candidate chunk embeddings from SQLite filtered by `(department_id, grade_level)`.
  - Computes cosine similarity via dot product (because vectors are normalized).
  - Returns the top `N` chunks.

### 5) How retrieval is used in question generation

In `app/services/exam_logic.py`:

- When generating a question, the system:
  - Picks a query text (initially a generic prompt; later uses the last asked question).
  - Retrieves top chunks using `query_similar_chunks(...)`.
  - Builds a context string from those chunks.
  - Calls the LLM to generate **one** question + ideal answer from that context.
  - Stores question + context in `exam_questions` for traceability.

## Scoring

In `app/services/exam_logic.py`:

- Uses weighted scoring:
  - correctness average (0..1)
  - speed score (based on average time per question vs `stop_slow_seconds`)
  - consistency score (based on max consecutive incorrect vs `stop_consecutive_incorrect`)
- Weights are configurable in `.env` (`SCORE_WEIGHT_*`).
- Rating thresholds:
  - `>= 85`: very_good
  - `>= 70`: good
  - `>= 50`: needs_improvement
  - else: bad

## Configuration surface

Most “nice to change” knobs are in `.env` / `.env.example`:

- DB path (`DATABASE_URL`), uploads (`UPLOAD_DIR`)
- Chunking + retrieval limits
- LLM endpoint/model/limits and mock fallback
- Exam defaults and stop rules
- Scoring weights
- Upload size limit

## Notes / limitations (by design)

- Student department selection is simplified to “first assigned department”; it can be extended to choose among multiple.
- Switching embedding models/providers on an existing DB requires reindexing (`python -m scripts.reindex_embeddings`) so previously stored embeddings match the new model.
- No admin UI yet for creating users; demo data is created via `scripts/seed_demo.py`.
