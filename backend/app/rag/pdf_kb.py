# app/rag/pdf_kb.py
import fitz
import uuid
from backend.app.rag.base_kb import BaseKnowledgeBase
from backend.app.rag.schema import KBItem
from backend.app.rag.embedding import EmbeddingService


class PDFKnowledgeBase(BaseKnowledgeBase):

    def __init__(self, storage):
        super().__init__(storage, kb_type="pdf")
        self.embedder = EmbeddingService()
        self.load_from_storage()

    def upsert(self, pdf_path: str):
        doc = fitz.open(pdf_path)
        texts = [page.get_text() for page in doc]
        embeddings = self.embedder.embed(texts)

        items = []
        for page_idx, (text, emb) in enumerate(zip(texts, embeddings)):
            items.append(KBItem(
                id=str(uuid.uuid4()),
                content=text,
                embedding=emb,
                metadata={
                    "type": "pdf",
                    "source": pdf_path,
                    "page": page_idx,
                },
            ))
        self.add_many(items)
