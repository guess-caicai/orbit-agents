# app.coding.__init__.py
from backend.app.agents.registry import AgentRegistry
from backend.app.agents.coding.spec import CodingAgentSpec

AgentRegistry.register(CodingAgentSpec())
