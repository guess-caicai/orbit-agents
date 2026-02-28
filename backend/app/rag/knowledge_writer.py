# app/rag/knowledge_writer.py
from backend.app.rag.text_kb import TextKnowledgeBase
from backend.app.rag.excel_kb import ExcelKnowledgeBase
from backend.app.rag.pdf_kb import PDFKnowledgeBase
from backend.app.rag.image_kb import ImageKnowledgeBase
from backend.app.rag.chunker import chunker_text


class KnowledgeWriter:

    def __init__(self, multi_kb):
        self.multi_kb = multi_kb
        self.type_map = {
            "text": TextKnowledgeBase,
            "excel": ExcelKnowledgeBase,
            "pdf": PDFKnowledgeBase,
            "image": ImageKnowledgeBase,
        }

    def upsert_text(self, texts: list[str]):
        all_chunks: list[str] = []
        for text in texts:
            all_chunks.extend(chunker_text(text))
        if all_chunks:
            self._get_kb("text").upsert(all_chunks)

    def upsert_excel(self, path: str):
        self._get_kb("excel").upsert(path)

    def upsert_pdf(self, path: str):
        self._get_kb("pdf").upsert(path)

    def upsert_image(self, paths: list[str]):
        self._get_kb("image").upsert(paths)

    def _get_kb(self, kb_type: str):
        for kb in self.multi_kb.kbs:
            if kb.kb_type == kb_type:
                return kb
        raise ValueError(f"KB not found: {kb_type}")
