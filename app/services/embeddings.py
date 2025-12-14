from __future__ import annotations

import threading

_lock = threading.Lock()
_model = None
_model_key: tuple[str, str | None] | None = None


def embed_texts_sentence_transformers(
    texts: list[str], *, model_name: str, device: str | None
) -> list[list[float]]:
    global _model, _model_key
    key = (model_name, device or None)
    with _lock:
        if _model is None or _model_key != key:
            from sentence_transformers import SentenceTransformer

            _model = SentenceTransformer(model_name, device=device) if device else SentenceTransformer(model_name)
            _model_key = key

        model = _model

    vectors = model.encode(
        texts,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    return vectors.astype("float32").tolist()

