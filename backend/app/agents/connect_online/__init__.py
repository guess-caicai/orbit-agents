from backend.app.agents.registry import AgentRegistry
from backend.app.agents.connect_online.spec import ConnectOnlineAgentSpec

AgentRegistry.register(ConnectOnlineAgentSpec())
