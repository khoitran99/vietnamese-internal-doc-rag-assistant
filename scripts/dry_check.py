from __future__ import annotations

import argparse

from src.config.settings import ensure_directories, load_settings


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate config and paths")
    parser.add_argument("--config", default="config/default.yaml")
    args = parser.parse_args()

    settings = load_settings(args.config)
    ensure_directories(settings)

    print("Config loaded successfully")
    print(f"Version: {settings.version}")
    print(f"Raw data dir: {settings.raw_data_dir}")
    print(f"Chunk output path: {settings.chunk_output_path}")
    print(f"BM25 index path: {settings.bm25_index_path}")
    print(f"Dense index dir: {settings.dense_index_dir}")


if __name__ == "__main__":
    main()
