import asyncio
from typing import Dict, Optional, Tuple

from backend.app.sessions.models import Session
from backend.app.agents.registry import AgentRegistry
from backend.app.agents.master_brain.decision import MasterBrainController
from backend.app.agents.master_brain.protocol import Decision


class SessionManager:
    """
    SessionManager 只负责三件事：
    1. Session 生命周期管理
    2. Agent 实例缓存 / 获取
    3. 调用 MasterBrain 做“唯一决策”
    """

    def __init__(self):
        self._sessions: Dict[str, Session] = {}
        self._lock = asyncio.Lock()

    # -------------------------
    # Session 生命周期
    # -------------------------

    async def get_or_create(self, session_id: str) -> Session:
        async with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = Session(session_id=session_id)
            return self._sessions[session_id]

    async def delete(self, session_id: str) -> bool:
        async with self._lock:
            return self._sessions.pop(session_id, None) is not None

    def list_sessions(self):
        return list(self._sessions.keys())

    async def get_session_info(self, session_id: str) -> Optional[Dict]:
        async with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return None

            return {
                "session_id": session.session_id,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "current_agent": session.current_agent,
                "agent_count": len(session.agents),
                "routing_context": session.routing_context,
                "agent_history": session.agent_history[-5:],
            }

    # -------------------------
    # Agent 管理
    # -------------------------
    async def get_agent(self, session: Session, agent_name: str):
        """
        获取或创建 Agent 实例（无任何路由逻辑）
        """
        agent = session.get_agent(agent_name)
        if agent:
            return agent

        spec = AgentRegistry.get(agent_name)
        agent = spec.create(session.session_id)
        session.add_agent(agent_name, agent)
        return agent

    # -------------------------
    # 核心：MasterBrain 决策（解耦）
    # -------------------------

    async def decide(
        self,
        session: Session,
        query: str,
        force_agent: Optional[str] = None,
    ) -> Decision:
        """
        仅生成决策，不做状态更新或 Agent 创建
        """
        if force_agent:
            return Decision(
                action="route",
                target_agent=force_agent,
            )

        master_brain = await self.get_agent(session, "master_brain")
        controller = MasterBrainController(master_brain)

        decision: Decision = await controller.decide(
            session_context=session.routing_context,
            query=query,
        )
        return decision

    async def apply_decision(
        self,
        session: Session,
        decision: Decision,
        query: str,
    ) -> Tuple[Decision, Optional[object]]:
        """
        应用决策：更新状态并在需要时创建/获取 Agent
        返回：
        - decision: 可能被修正后的决策（如冷启动时 keep -> route）
        - agent: 单 Agent 模式下的 Agent 实例（delegate 时为 None）
        """
        session.routing_context["last_decision"] = decision.model_dump()

        if decision.action == "keep":
            if not session.current_agent:
                agent_name = "connect_online_agent"
                decision = Decision(
                    action="route",
                    target_agent=agent_name,
                    reason="cold_start_no_current_agent",
                )
            else:
                agent_name = session.current_agent
            agent = await self.get_agent(session, agent_name)
            session.set_current_agent(agent_name, query)
            return decision, agent

        if decision.action == "route":
            agent_name = decision.target_agent
            if not agent_name:
                raise RuntimeError("ROUTE action without target_agent")

            agent = await self.get_agent(session, agent_name)
            session.set_current_agent(agent_name, query)
            return decision, agent

        if decision.action == "delegate":
            session.set_current_agent("__delegate__", query)
            return decision, None

        raise RuntimeError(f"Unknown decision action: {decision.action}")

    async def decide_and_get_agent(
        self,
        session: Session,
        query: str,
        force_agent: Optional[str] = None,
    ) -> Tuple[Decision, Optional[object]]:
        """
        兼容旧接口：先决策，再应用
        """
        decision = await self.decide(
            session=session,
            query=query,
            force_agent=force_agent,
        )
        return await self.apply_decision(
            session=session,
            decision=decision,
            query=query,
        )
