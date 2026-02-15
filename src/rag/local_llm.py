from __future__ import annotations

import json
from dataclasses import dataclass
from typing import List

from src.common.schemas import RetrievalHit


@dataclass
class GeneratedAnswer:
    answer: str
    citations: List[dict]
    raw_output: str


class LocalLLM:
    def __init__(self, backend: str, model_name: str, max_new_tokens: int = 256) -> None:
        self.backend = backend
        self.model_name = model_name
        self.max_new_tokens = max_new_tokens
        self._pipe = None

        if backend == "transformers":
            try:
                from transformers import pipeline

                self._pipe = pipeline("text-generation", model=model_name)
            except Exception:
                self._pipe = None
                self.backend = "heuristic"

    def _heuristic_generate(self, question: str, hits: List[RetrievalHit]) -> GeneratedAnswer:
        if not hits:
            return GeneratedAnswer(answer="NOT_FOUND", citations=[], raw_output="NOT_FOUND")

        selected = hits[: min(3, len(hits))]
        bullets = []
        citations = []
        for hit in selected:
            chunk = hit.chunk_ref
            sentence = chunk.text.split(".")[0].strip()
            if not sentence:
                sentence = chunk.text[:200].strip()
            bullets.append(f"- {sentence}")
            citations.append(
                {
                    "title": chunk.title,
                    "section_path": chunk.section_path,
                    "chunk_id": chunk.chunk_id,
                }
            )

        answer = "\n".join(bullets)
        if not answer:
            answer = "NOT_FOUND"
        return GeneratedAnswer(answer=answer, citations=citations, raw_output=answer)

    def _transformers_generate(self, prompt: str, hits: List[RetrievalHit]) -> GeneratedAnswer:
        if self._pipe is None:
            return self._heuristic_generate(prompt, hits)

        output = self._pipe(prompt, max_new_tokens=self.max_new_tokens, do_sample=False)[0]["generated_text"]
        maybe_json = output.split("\n")[-1].strip()
        try:
            payload = json.loads(maybe_json)
            answer = str(payload.get("answer", "NOT_FOUND"))
            citations = payload.get("citations", []) if isinstance(payload.get("citations", []), list) else []
            return GeneratedAnswer(answer=answer, citations=citations, raw_output=output)
        except Exception:
            return self._heuristic_generate(prompt, hits)

    def generate(self, question: str, prompt: str, hits: List[RetrievalHit]) -> GeneratedAnswer:
        if self.backend == "transformers":
            return self._transformers_generate(prompt, hits)
        return self._heuristic_generate(question, hits)
