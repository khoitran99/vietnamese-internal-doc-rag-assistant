from __future__ import annotations

import argparse

from src.config.settings import ensure_directories, load_settings
from src.indexing.build_indices import build_all_indices
from src.ingestion.pipeline import ingest_and_chunk


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest documents and build indices")
    parser.add_argument("--config", default="config/default.yaml")
    args = parser.parse_args()

    settings = load_settings(args.config)
    ensure_directories(settings)
    chunks = ingest_and_chunk(settings)
    build_all_indices(settings)

    print(f"Ingested {len(chunks)} chunks")
    print(f"Chunk file: {settings.chunk_output_path}")
    print(f"BM25 index: {settings.bm25_index_path}")
    print(f"Dense index dir: {settings.dense_index_dir}")


if __name__ == "__main__":
    main()
