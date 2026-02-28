from backend.app.agents.registry import AgentRegistry
from backend.app.agents.sqlite_query.spec import SqliteQueryAgentSpec

AgentRegistry.register(SqliteQueryAgentSpec())
