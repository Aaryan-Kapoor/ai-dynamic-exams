from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.config import get_settings
from app.db import Base, SessionLocal, engine
from app.models import LectureChunk
from app.services.vector_index import ensure_chunk_embeddings


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild lecture chunk embeddings.")
    parser.add_argument("--department-id", type=int, default=None)
    parser.add_argument("--grade-level", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=128)
    args = parser.parse_args()

    settings = get_settings()
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        stmt = select(LectureChunk.id).order_by(LectureChunk.id)
        if args.department_id is not None:
            stmt = stmt.where(LectureChunk.department_id == args.department_id)
        if args.grade_level is not None:
            stmt = stmt.where(LectureChunk.grade_level == args.grade_level)

        chunk_ids = [row[0] for row in db.execute(stmt).all()]
        if not chunk_ids:
            print("No chunks found (nothing to do).")
            return

        print(
            f"Reindexing {len(chunk_ids)} chunks using provider={settings.embedding_provider} model={settings.embedding_model_name}"
        )
        bs = max(1, int(args.batch_size))
        for i in range(0, len(chunk_ids), bs):
            batch = chunk_ids[i : i + bs]
            ensure_chunk_embeddings(db, chunk_ids=batch, dim=settings.embedding_dim, force=True)
            print(f"  {min(i+bs, len(chunk_ids))}/{len(chunk_ids)}", end="\r")
        print("\nDone.")
    finally:
        db.close()


if __name__ == "__main__":
    main()

