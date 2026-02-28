# app/rag/base_kb.py
from abc import ABC, abstractmethod
from backend.app.rag.schema import KBItem
import numpy as np


class BaseKnowledgeBase(ABC):

    def __init__(self, storage, kb_type: str):
        self.items: dict[str, KBItem] = {}
        self.storage = storage
        self.kb_type = kb_type

    def load_from_storage(self):
        items = self.storage.load_by_type(self.kb_type)
        for item in items:
            self.items[item.id] = item

    @abstractmethod
    def upsert(self, source):
        pass

    def add(self, item: KBItem):
        self.items[item.id] = item
        self.storage.save_item(self.kb_type, item)

    def add_many(self, items: list[KBItem]):
        if not items:
            return
        for item in items:
            self.items[item.id] = item
        self.storage.save_items(self.kb_type, items)

    def delete(self, item_id: str):
        self.items.pop(item_id, None)
        self.storage.delete_item(item_id)

    def search(self, query_embedding, top_k=5):
        if not self.items:
            return []

        vectors = np.array([i.embedding for i in self.items.values()])
        query = np.array(query_embedding)
        scores = vectors @ query
        idx = scores.argsort()[-top_k:][::-1]
        values = list(self.items.values())
        return [values[i] for i in idx]
