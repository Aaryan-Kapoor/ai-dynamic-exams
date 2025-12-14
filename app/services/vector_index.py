from __future__ import annotations

import hashlib
import math
from array import array

from sqlalchemy import select
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import LectureChunk, LectureChunkEmbedding
from app.services.embeddings import embed_texts_sentence_transformers


def _tokenize(text: str) -> list[str]:
    return [t for t in "".join(ch.lower() if ch.isalnum() else " " for ch in text).split() if t]


def _hash_embed_text(text: str, *, dim: int) -> list[float]:
    tokens = _tokenize(text)
    vec = [0.0] * dim
    if not tokens:
        return vec

    for tok in tokens:
        h = hashlib.sha1(tok.encode("utf-8")).digest()
        idx = int.from_bytes(h[:4], "little") % dim
        sign = 1.0 if (h[4] & 1) == 0 else -1.0
        vec[idx] += sign

    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def embed_text(text: str, *, dim: int) -> list[float]:
    settings = get_settings()
    if settings.embedding_provider == "hash":
        return _hash_embed_text(text, dim=dim)
    if settings.embedding_provider == "sentence_transformers":
        vec = embed_texts_sentence_transformers(
            [text], model_name=settings.embedding_model_name, device=settings.embedding_device or None
        )[0]
        if len(vec) != dim:
            raise ValueError(f"Embedding dim mismatch: expected {dim}, got {len(vec)}")
        return vec
    raise ValueError(f"Unknown embedding provider: {settings.embedding_provider}")


def pack_embedding(vec: list[float]) -> bytes:
    return array("f", vec).tobytes()


def unpack_embedding(blob: bytes) -> list[float]:
    arr = array("f")
    arr.frombytes(blob)
    return list(arr)


def ensure_chunk_embeddings(
    db: Session, *, chunk_ids: list[int], dim: int, force: bool = False
) -> None:
    if not chunk_ids:
        return
    if force:
        db.execute(delete(LectureChunkEmbedding).where(LectureChunkEmbedding.chunk_id.in_(chunk_ids)))
        db.commit()
        missing = list(chunk_ids)
    else:
        existing = {
            row[0]
            for row in db.execute(
                select(LectureChunkEmbedding.chunk_id).where(
                    LectureChunkEmbedding.chunk_id.in_(chunk_ids)
                )
            ).all()
        }
        missing = [cid for cid in chunk_ids if cid not in existing]
    if not missing:
        return

    chunks = db.scalars(select(LectureChunk).where(LectureChunk.id.in_(missing))).all()
    settings = get_settings()
    if settings.embedding_provider == "hash":
        vectors = [_hash_embed_text(c.text, dim=dim) for c in chunks]
    elif settings.embedding_provider == "sentence_transformers":
        vectors = embed_texts_sentence_transformers(
            [c.text for c in chunks],
            model_name=settings.embedding_model_name,
            device=settings.embedding_device or None,
        )
        if vectors and len(vectors[0]) != dim:
            raise ValueError(f"Embedding dim mismatch: expected {dim}, got {len(vectors[0])}")
    else:
        raise ValueError(f"Unknown embedding provider: {settings.embedding_provider}")
    for chunk, vec in zip(chunks, vectors):
        db.add(LectureChunkEmbedding(chunk_id=chunk.id, embedding_dim=dim, embedding=pack_embedding(vec)))
    db.commit()


def query_similar_chunks(
    db: Session,
    *,
    query: str,
    department_id: int,
    grade_level: int,
    limit: int,
    dim: int,
) -> list[LectureChunk]:
    if limit <= 0:
        return []

    query_vec = embed_text(query, dim=dim)

    rows = db.execute(
        select(LectureChunk, LectureChunkEmbedding.embedding)
        .join(LectureChunkEmbedding, LectureChunkEmbedding.chunk_id == LectureChunk.id)
        .where(LectureChunk.department_id == department_id)
        .where(LectureChunk.grade_level == grade_level)
    ).all()

    scored: list[tuple[float, LectureChunk]] = []
    for chunk, emb_blob in rows:
        vec = unpack_embedding(emb_blob)
        sim = sum(a * b for a, b in zip(query_vec, vec))
        scored.append((sim, chunk))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:limit]]
