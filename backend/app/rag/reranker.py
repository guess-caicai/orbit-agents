import os
import logging
import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class QwenReRanker:

    def __init__(self):
        self.api_key = os.getenv("DASHSCOPE_API_KEY16")
        self.url = "https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/"

    def rerank(
        self,
        query: str,
        documents: list[str],
        top_k: int = 5,
    ) -> list[int]:
        if not documents:
            return []

        # 默认：不重排（原顺序）
        fallback_indices = list(range(len(documents)))

        payload = {
            "model": "qwen-rerank",
            "task": "text_rerank",
            "input": {
                "query": query,
                "passages": [
                    {"id": str(i), "text": doc}
                    for i, doc in enumerate(documents)
                ],
            },
            "parameters": {
                "top_n": min(top_k, len(documents)),
            },
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            resp = requests.post(
                self.url,
                json=payload,
                headers=headers,
                timeout=15,  # 建议比 LLM 短
            )
            if resp.status_code != 200:
                logger.warning(
                    "Rerank skipped (status=%s): %s",
                    resp.status_code,
                    resp.text,
                )
                return fallback_indices

            data = resp.json()
            results = data.get("output", {}).get("results")

            if not results:
                logger.warning(
                    "Rerank skipped (empty results, status=%s): %s",
                    resp.status_code,
                    resp.text,
                )
                return fallback_indices

            return [int(item["id"]) for item in results]

        except Exception as e:
            logger.exception("Rerank skipped due to exception: %s", e)
            return fallback_indices
