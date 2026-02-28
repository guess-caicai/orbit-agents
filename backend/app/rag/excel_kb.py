# app/rag/excel_kb.py
import pandas as pd
import uuid
from backend.app.rag.base_kb import BaseKnowledgeBase
from backend.app.rag.schema import KBItem
from backend.app.rag.embedding import EmbeddingService


class ExcelKnowledgeBase(BaseKnowledgeBase):

    def __init__(self, storage):
        super().__init__(storage, kb_type="excel")
        self.embedder = EmbeddingService()
        self.load_from_storage()

    def upsert(self, excel_path: str):
        df = pd.read_excel(excel_path)
        rows = df.astype(str).apply(lambda x: " | ".join(x), axis=1).tolist()
        embeddings = self.embedder.embed(rows)

        items = []
        for row, emb in zip(rows, embeddings):
            items.append(KBItem(
                id=str(uuid.uuid4()),
                content=row,
                embedding=emb,
                metadata={
                    "type": "excel",
                    "source": excel_path,
                },
            ))
        self.add_many(items)
