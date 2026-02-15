from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List, TypeVar, Callable

T = TypeVar("T")


def write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> List[dict]:
    items: List[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            items.append(json.loads(line))
    return items


def read_jsonl_typed(path: Path, factory: Callable[[dict], T]) -> List[T]:
    return [factory(item) for item in read_jsonl(path)]
