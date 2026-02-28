from backend.app.agents.registry import AgentRegistry
from backend.app.agents.search_rag.spec import RAGAgentSpec

AgentRegistry.register(RAGAgentSpec())
