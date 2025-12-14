FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    # Persist HF/transformers cache in the mounted ./data volume when using Docker Compose
    HF_HOME=/app/data/hf \
    TRANSFORMERS_CACHE=/app/data/hf

WORKDIR /app

# System dependencies
# - tesseract-ocr: optional OCR support for image uploads (enabled by default for "batteries included")
# - libgl1 + libglib2.0-0: common runtime deps for image processing wheels (Pillow/OpenCV-style deps)
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    libgl1 \
    libglib2.0-0 \
  && rm -rf /var/lib/apt/lists/*

# Install Python deps first for better layer caching
COPY requirements.txt /app/requirements.txt
RUN python -m pip install -r /app/requirements.txt

# Copy backend code only (prevents accidental leakage of local `.env`, `data/`, etc.)
COPY app/ /app/app/
COPY scripts/ /app/scripts/

# Prepare runtime directories (compose mounts ./data -> /app/data)
RUN mkdir -p /app/data/uploads /app/data/hf

# Drop privileges
RUN useradd --create-home --shell /usr/sbin/nologin appuser \
  && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Note: The backend reads configuration from `.env` at runtime.
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

