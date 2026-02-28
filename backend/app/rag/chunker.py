# app/rag/chunker.py
from typing import List


def chunker_text(
    text: str,
    chunker_size: int = 500,
    overlap: int = 50,
) -> List[str]:
    chunks = []
    start = 0
    text = text.strip()
    while start < len(text):
        end = start + chunker_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap

    return [c for c in chunks if c.strip()]
