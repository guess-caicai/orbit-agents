# app/rag/embedding.py
import os
import dashscope
from typing import List, Any
from dotenv import load_dotenv
load_dotenv()
dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")


class EmbeddingService:
    @staticmethod
    def embed(texts: List[str | Any]) -> List[List[float]]:
        if not texts:
            return []
        resp = dashscope.TextEmbedding.call(
            model="text-embedding-v4",
            input=texts
        )
        if resp.get("status_code") != 200:
            raise RuntimeError(f"Embedding failed:{resp}")
        return [item["embedding"] for item in resp["output"]["embeddings"]]
