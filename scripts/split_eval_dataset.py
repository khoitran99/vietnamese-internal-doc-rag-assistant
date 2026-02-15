#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Tuple


def load_jsonl(path: Path) -> List[dict]:
    rows: List[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: List[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def stratified_split(rows: List[dict], holdout_ratio: float, seed: int) -> Tuple[List[dict], List[dict]]:
    rng = random.Random(seed)

    # Stratify by query_type + difficulty to keep distribution stable.
    buckets: Dict[Tuple[str, str], List[dict]] = defaultdict(list)
    for row in rows:
        key = (str(row.get("query_type", "unknown")), str(row.get("difficulty", "unknown")))
        buckets[key].append(row)

    train: List[dict] = []
    holdout: List[dict] = []

    for key in sorted(buckets.keys()):
        bucket = sorted(buckets[key], key=lambda r: str(r.get("id", "")))
        rng.shuffle(bucket)
        n = len(bucket)
        n_holdout = int(round(n * holdout_ratio))
        if n > 1:
            n_holdout = max(1, min(n - 1, n_holdout))
        else:
            n_holdout = 0
        holdout.extend(bucket[:n_holdout])
        train.extend(bucket[n_holdout:])

    train = sorted(train, key=lambda r: str(r.get("id", "")))
    holdout = sorted(holdout, key=lambda r: str(r.get("id", "")))
    return train, holdout


def summarize(rows: List[dict], label: str) -> str:
    qt = Counter(str(r.get("query_type", "unknown")) for r in rows)
    diff = Counter(str(r.get("difficulty", "unknown")) for r in rows)
    return (
        f"{label}: total={len(rows)} | "
        f"query_type={dict(sorted(qt.items()))} | "
        f"difficulty={dict(sorted(diff.items()))}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Create deterministic train/holdout splits for eval dataset.")
    parser.add_argument("--input", default="data/eval/qa_eval.jsonl")
    parser.add_argument("--train-output", default="data/eval/qa_eval_train.jsonl")
    parser.add_argument("--holdout-output", default="data/eval/qa_eval_holdout.jsonl")
    parser.add_argument("--holdout-ratio", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    if args.holdout_ratio <= 0 or args.holdout_ratio >= 1:
        raise SystemExit("--holdout-ratio must be between 0 and 1 (exclusive).")

    rows = load_jsonl(Path(args.input))
    if not rows:
        raise SystemExit(f"No rows found in {args.input}")

    train, holdout = stratified_split(rows, holdout_ratio=args.holdout_ratio, seed=args.seed)
    write_jsonl(Path(args.train_output), train)
    write_jsonl(Path(args.holdout_output), holdout)

    print(summarize(rows, "full"))
    print(summarize(train, "train"))
    print(summarize(holdout, "holdout"))
    print(f"Wrote train -> {args.train_output}")
    print(f"Wrote holdout -> {args.holdout_output}")


if __name__ == "__main__":
    main()
