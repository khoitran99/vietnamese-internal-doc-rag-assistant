from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from src.common.io import read_jsonl


@dataclass
class EvalItem:
    id: str
    question: str
    gold_chunk_ids: List[str]
    reference_answer: Optional[str] = None


def load_eval_dataset(path: Path) -> List[EvalItem]:
    rows = read_jsonl(path)
    items: List[EvalItem] = []
    for row in rows:
        items.append(
            EvalItem(
                id=str(row["id"]),
                question=str(row["question"]),
                gold_chunk_ids=list(row.get("gold_chunk_ids", [])),
                reference_answer=row.get("reference_answer"),
            )
        )
    return items
