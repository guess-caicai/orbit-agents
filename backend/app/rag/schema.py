# app/rag/schema.py
from dataclasses import dataclass


@dataclass
class KBItem:
    id: str
    content: str
    embedding: list[float]
    metadata: dict
