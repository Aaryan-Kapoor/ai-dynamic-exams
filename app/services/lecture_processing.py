from __future__ import annotations

import re
import shutil
from pathlib import Path

from pypdf import PdfReader


def extract_text_from_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    parts: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            parts.append(text)
    return "\n\n".join(parts).strip()


def extract_text_from_image(path: Path) -> str:
    try:
        from PIL import Image
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("Pillow is required for image uploads") from exc

    if not shutil.which("tesseract"):
        raise RuntimeError(
            "OCR requires the `tesseract` binary. Install it (e.g. `apt-get install tesseract-ocr`)."
        )

    try:
        import pytesseract
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("pytesseract is required for OCR") from exc

    with Image.open(path) as img:
        return (pytesseract.image_to_string(img) or "").strip()


def extract_text_from_upload(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".pdf":
        return extract_text_from_pdf(path)
    if ext in {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"}:
        return extract_text_from_image(path)

    # Best-effort plain text
    if ext in {".txt", ".md", ".csv"}:
        return path.read_text(encoding="utf-8", errors="ignore").strip()

    return ""


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    cleaned = re.sub(r"\r\n?", "\n", text).strip()
    if not cleaned:
        return []

    chunk_size = max(200, chunk_size)
    overlap = max(0, min(overlap, chunk_size - 1))

    chunks: list[str] = []
    start = 0
    while start < len(cleaned):
        end = min(len(cleaned), start + chunk_size)
        chunk = cleaned[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(cleaned):
            break
        start = end - overlap

    return chunks

