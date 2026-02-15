from __future__ import annotations

import re
import unicodedata


_WHITESPACE_RE = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFC", text)
    normalized = normalized.replace("\x00", " ")
    cleaned_lines = []
    for line in normalized.splitlines():
        compact = _WHITESPACE_RE.sub(" ", line).strip()
        if compact:
            cleaned_lines.append(compact)
    return "\n".join(cleaned_lines).strip()
