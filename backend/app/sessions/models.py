from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class Session:
    session_id: str

    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    # agent_name -> agent_instance
    agents: Dict[str, Any] = field(default_factory=dict)

    # 当前绑定的 Agent（delegate 时为 "__delegate__"）
    current_agent: Optional[str] = None

    # Agent 切换历史（纯记录，不做判断）
    agent_history: List[Dict[str, Any]] = field(default_factory=list)

    # 路由上下文：只存“事实”，不存“规则”
    routing_context: Dict[str, Any] = field(
        default_factory=lambda: {
            "last_decision": None,
            "last_query": None,
            "conversation_depth": 0,
        }
    )

    # -------------------------
    # Agent 管理（无决策）
    # -------------------------

    def get_agent(self, agent_name: str):
        return self.agents.get(agent_name)

    def add_agent(self, agent_name: str, agent_instance: Any):
        self.agents[agent_name] = agent_instance
        self.updated_at = datetime.now()

    # -------------------------
    # 状态记录（不判断）
    # -------------------------

    def set_current_agent(self, agent_name: str, query: Optional[str] = None):
        previous_agent = self.current_agent
        self.current_agent = agent_name
        self.updated_at = datetime.now()

        # 记录最后一次 query
        if query:
            self.routing_context["last_query"] = query

        # 对话深度：只统计，不参与决策
        if agent_name == previous_agent:
            self.routing_context["conversation_depth"] += 1
        else:
            self.routing_context["conversation_depth"] = 0

        # 记录 Agent 切换事件（包括 delegate）
        self.agent_history.append(
            {
                "timestamp": datetime.now().isoformat(),
                "from_agent": previous_agent,
                "to_agent": agent_name,
                "query": query,
            }
        )

        # 控制历史长度
        if len(self.agent_history) > 50:
            self.agent_history = self.agent_history[-50:]
