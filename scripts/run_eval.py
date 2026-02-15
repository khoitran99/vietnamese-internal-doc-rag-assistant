from __future__ import annotations

import argparse
import json

from src.eval.run_eval import run_full_eval


def main() -> None:
    parser = argparse.ArgumentParser(description="Run retrieval and answer evaluation")
    parser.add_argument("--config", default="config/default.yaml")
    parser.add_argument("--top_k", type=int, default=5)
    args = parser.parse_args()

    report = run_full_eval(args.config, top_k=args.top_k)
    output = {
        "bm25": report["retrieval"]["bm25"]["summary"],
        "dense": report["retrieval"]["dense"]["summary"],
        "hybrid": report["retrieval"]["hybrid"]["summary"],
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
