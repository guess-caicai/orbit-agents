# app.master_brain.__init__.py
from backend.app.agents.registry import AgentRegistry
from backend.app.agents.master_brain.spec import MasterBrainAgentSpec

AgentRegistry.register(MasterBrainAgentSpec())
