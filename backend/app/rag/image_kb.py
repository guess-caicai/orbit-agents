# app/rag/image_kb.py
import uuid
import os
from backend.app.rag.base_kb import BaseKnowledgeBase
from backend.app.rag.schema import KBItem
from backend.app.rag.embedding import EmbeddingService
from agentscope.model import DashScopeChatModel
from dotenv import load_dotenv
load_dotenv()


class ImageKnowledgeBase(BaseKnowledgeBase):

    def __init__(self, storage):
        super().__init__(storage, kb_type="image")
        self.embedder = EmbeddingService()
        self.load_from_storage()
        self.vision_model = DashScopeChatModel(
            model_name="qwen-vl-plus",
            api_key=os.getenv("DASHSCOPE_API_KEY"),
        )

    async def upsert(self, image_paths: list[str]):
        captions = []
        for path in image_paths:
            caption = await self.vision_model(
                [{"role": "user", "content": [{"type": "image", "image": path}]}]
            )
            captions.append(caption)

        embeddings = self.embedder.embed(captions)
        items = []
        for path, cap, emb in zip(image_paths, captions, embeddings):
            items.append(KBItem(
                id=str(uuid.uuid4()),
                content=cap,
                embedding=emb,
                metadata={
                    "type": "image",
                    "source": path,
                },
            ))
        self.add_many(items)
