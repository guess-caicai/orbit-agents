from backend.app.agents.registry import AgentRegistry
from backend.app.agents.knowledge_graph.spec import KnowledgeGraphAgentSpec

AgentRegistry.register(KnowledgeGraphAgentSpec())
