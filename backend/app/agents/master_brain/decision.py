# app.agents.master_brain.decision.py
import json
from agentscope.message import Msg
from .protocol import Decision


class MasterBrainController:

    def __init__(self, agent):
        self.agent = agent

    async def decide(self, session_context: dict, query: str) -> Decision:
        prompt = {
            "session": session_context,
            "query": query
        }

        msg = Msg(
            name="user",
            role="user",
            content=json.dumps(prompt, ensure_ascii=False)
        )

        await self.agent(msg)

        memory = await self.agent.memory.get_memory()
        raw = memory[-1].content[0]["text"]

        return Decision.model_validate_json(raw)
