# agents/master_brain/spec.py
import os
import json
from backend.app.agents.base import AgentSpec
from agentscope.agent import ReActAgent
from agentscope.model import DashScopeChatModel
from agentscope.memory import InMemoryMemory
from agentscope.formatter import DashScopeChatFormatter
from dotenv import load_dotenv
from agentscope import init

load_dotenv()
init()


class MasterBrainAgentSpec(AgentSpec):
    """
    MasterBrain 只负责“决策”，不负责“执行”
    """
    name = "master_brain"
    description = "主脑决策智能体 - 输出 ACP 协议决策"

    def create(self, session_id: str):
        from backend.app.agents.registry import AgentRegistry

        # --------- 可用 Agent 列表（给 LLM 认知用）---------
        available_agents = []
        for agent_name in AgentRegistry.list_agents():
            if agent_name != self.name:
                spec = AgentRegistry.get(agent_name)
                available_agents.append(
                    {
                        "name": spec.name,
                        "description": spec.description,
                    }
                )

        # --------- ACP 协议 Prompt（强约束）---------
        system_prompt = f"""
            你是 MasterBrain，一个“只负责决策”的中枢智能体。
            
            【你的职责】
            - 不回答用户问题
            - 不调用任何工具
            - 只输出一个 JSON 决策对象
            - 严格遵守 ACP（Agent Collaboration Protocol）
            
            【可用 Agent】
            {json.dumps(available_agents, ensure_ascii=False, indent=2)}
            
            【决策协议（必须严格遵守）】
            你必须输出以下 JSON 之一，不得输出任何多余文本：
            
            1️ 保持当前 Agent：
            {{
              "action": "keep"
            }}
            
            2️ 切换到单一 Agent：
            {{
              "action": "route",
              "target_agent": "<agent_name>"
            }}
            
            3️ 拆分为多 Agent 协作：
            {{
              "action": "delegate",
              "sub_tasks": [
                {{
                  "agent": "<agent_name>",
                  "input": "<子任务输入>"
                }}
              ]
            }}
            
            【决策规则】
            - 如果用户是在延续当前话题，优先 keep
            - 如果用户明确要求某能力，route 到对应 Agent
            - 如果任务需要多个步骤或多领域，delegate
            - 不确定时，优先 route 到通用能力强的 Agent
            
            【输入格式】
            你将收到一个 JSON：
            {{
              "session": <session_context>,
              "query": "<用户输入>"
            }}
            
            【再次强调】
            - 只输出 JSON
            - 不要解释
            - 不要自然语言
            """
        return ReActAgent(
            name="MasterBrain",
            sys_prompt=system_prompt,
            model=DashScopeChatModel(
                model_name="qwen-max",
                api_key=os.getenv("DASHSCOPE_API_KEY"),
                stream=False,
                enable_thinking=False),
            formatter=DashScopeChatFormatter(),
            memory=InMemoryMemory()
            )
