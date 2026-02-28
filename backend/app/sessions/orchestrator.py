# sessions.orchestrator.py
from agentscope.message import Msg
from backend.app.agents.registry import AgentRegistry
from backend.app.sessions.runtime_context import RuntimeContextBuilder

runtime_context = RuntimeContextBuilder()


class SessionOrchestrator:

    def _extract_last_text(self, memory) -> str:
        if not memory:
            return ""
        # 从后往前找可读文本
        for msg in reversed(memory):
            content = getattr(msg, "content", None)
            if content is None:
                continue
            # content 可能是字符串
            if isinstance(content, str):
                return content
            # content 可能是 list[dict]
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and "text" in item:
                        return item["text"]
        return ""

    async def handle(self, session, query, decision, agent):

        if decision.action in ("keep", "route"):
            msg = Msg(name="user", role="user", content=runtime_context.build_runtime_context(query))
            await agent(msg)
            memory = await agent.memory.get_memory()
            return self._extract_last_text(memory)

        # delegate
        if decision.action == "delegate":
            results = []
            context_chunks = []
            for task in decision.sub_tasks:
                sub_agent = session.get_agent(task.agent)
                if not sub_agent:
                    spec = AgentRegistry.get(task.agent)
                    sub_agent = spec.create(session.session_id)
                    session.add_agent(task.agent, sub_agent)

                task_input = task.input
                if context_chunks:
                    task_input = (
                        f"{task_input}\n\n"
                        "已完成子任务结果：\n"
                        + "\n\n".join(context_chunks)
                    )

                try:
                    msg = Msg(name="user", role="user", content=runtime_context.build_runtime_context(task_input))
                    await sub_agent(msg)
                    mem = await sub_agent.memory.get_memory()
                    output = self._extract_last_text(mem)
                except Exception as e:
                    output = f"[subtask_error] {e}"

                results.append({
                    "agent": task.agent,
                    "input": task_input,
                    "output": output,
                })
                if output:
                    context_chunks.append(f"[{task.agent}]\n{output}")
            return {
                "mode": "delegate",
                "results": results,
            }
