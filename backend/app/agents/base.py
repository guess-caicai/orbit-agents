# app/agents/base.py
from abc import ABC, abstractmethod
from typing import Any


class AgentSpec(ABC):
    """
    Agent 的“定义”，不是运行实例
    """
    name: str
    description: str

    @abstractmethod
    def create(self, session_id: str) -> Any:
        """
        创建并返回一个 Agent 运行实例
        """
        pass
