# app/agents/registry.py
from typing import Dict
from backend.app.agents.base import AgentSpec


class AgentRegistry:
    _registry: Dict[str, AgentSpec] = {}

    @classmethod
    def register(cls, spec: AgentSpec):
        cls._registry[spec.name] = spec

    @classmethod
    def get(cls, name: str) -> AgentSpec:
        if name not in cls._registry:
            raise ValueError(f"Agent '{name}' not registered")
        return cls._registry[name]

    @classmethod
    def list_agents(cls):
        return list(cls._registry.keys())
