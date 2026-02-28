# app/rag/text_kb.py
import uuid
from backend.app.rag.base_kb import BaseKnowledgeBase
from backend.app.rag.schema import KBItem
from backend.app.rag.embedding import EmbeddingService


class TextKnowledgeBase(BaseKnowledgeBase):

    def __init__(self, storage):
        super().__init__(storage, kb_type="text")
        self.embedder = EmbeddingService()
        self.load_from_storage()

    def upsert(self, texts: list[str]):
        embeddings = self.embedder.embed(texts)
        items = []
        for text, emb in zip(texts, embeddings):
            items.append(KBItem(
                id=str(uuid.uuid4()),
                content=text,
                embedding=emb,
                metadata={"type": "text"},
            ))
        self.add_many(items)
