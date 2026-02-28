# app/agents/search_rag/tools.py
from agentscope.message import TextBlock
from agentscope.tool import ToolResponse
from backend.app.rag.multi_kb import MultiKnowledgeBase

_kb = None


def set_kb(kb: MultiKnowledgeBase):
    global _kb
    _kb = kb


def get_kb() -> MultiKnowledgeBase:
    global _kb
    if _kb is None:
        _kb = MultiKnowledgeBase()
    return _kb


def retrieve_knowledge(query: str) -> ToolResponse:
    """{从多模态知识库中检索相关上下文}
    Args:
        query (str):
            {需向量检索的文本内容}
    """
    results = get_kb().search(
        query=query,
        recall_top_n=20,
        final_top_k=5,
    )
    context = "\n\n".join(
        f"[{r.metadata['type']}]\n{r.content}"
        for r in results
    )
    text_block = TextBlock(type="text", text=context)
    return ToolResponse(content=[text_block])
