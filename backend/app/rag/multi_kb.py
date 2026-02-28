# app/rag/multi_kb.py
from backend.app.rag.storage import SQLiteKnowledgeStorage
from backend.app.rag.text_kb import TextKnowledgeBase
from backend.app.rag.excel_kb import ExcelKnowledgeBase
from backend.app.rag.pdf_kb import PDFKnowledgeBase
from backend.app.rag.image_kb import ImageKnowledgeBase
from backend.app.rag.embedding import EmbeddingService
from backend.app.rag.reranker import QwenReRanker


class MultiKnowledgeBase:

    def __init__(self):
        self.storage = SQLiteKnowledgeStorage("knowledge.db")
        self.embedder = EmbeddingService()
        self.reranker = QwenReRanker()

        self.kbs = [
            TextKnowledgeBase(self.storage),
            ExcelKnowledgeBase(self.storage),
            PDFKnowledgeBase(self.storage),
            ImageKnowledgeBase(self.storage),
        ]
    
    def close(self):
        if hasattr(self.storage, "close"):
            self.storage.close()

    def search(
        self,
        query: str,
        recall_top_n: int = 20,
        final_top_k: int = 5,
    ):
        """
        recall_top_n: 向量召回数量
        final_top_k: rerank 后最终返回数量
        """
        q_emb = self.embedder.embed([query])[0]

        # ---------- 向量召回 ----------
        recalled_items = []
        for kb in self.kbs:
            recalled_items.extend(
                kb.search(q_emb, top_k=recall_top_n)
            )

        if not recalled_items:
            return []

        docs = [item.content for item in recalled_items]

        # ---------- Re-Rank ----------
        ranked_indices = self.reranker.rerank(
            query=query,
            documents=docs,
            top_k=final_top_k,
        )

        return [recalled_items[i] for i in ranked_indices]
