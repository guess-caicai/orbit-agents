import os
from agentscope.tool import Toolkit
from backend.app.agents.base import AgentSpec
from agentscope.agent import ReActAgent
from agentscope.model import DashScopeChatModel
from agentscope.memory import InMemoryMemory
from agentscope.formatter import DashScopeChatFormatter
from dotenv import load_dotenv
from agentscope import init
from backend.app.agents.search_rag.tools import retrieve_knowledge

load_dotenv()
init()


class RAGAgentSpec(AgentSpec):
    name = "rag_agent"
    description = "多模态 RAG 检索与生成智能体，用于解决用户非联网问题的检索回答"

    def create(self, session_id: str):
        toolkit = Toolkit()
        toolkit.register_tool_function(retrieve_knowledge)

        model = DashScopeChatModel(
            model_name="qwen-max",
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            stream=True,
        )

        system_prompt = """
            你是一个 RAG 智能体。
            你可使用工具：
            - retrieve_knowledge 检索多模态知识库返回检索答案
            工作流程：
            1. 先调用 retrieve_knowledge 获取上下文
            2. 基于上下文进行严谨回答
            3. 不编造知识库中不存在的内容
            """

        return ReActAgent(
            name=f"rag_agent_{session_id}",
            sys_prompt=system_prompt,
            model=model,
            formatter=DashScopeChatFormatter(),
            memory=InMemoryMemory(),
            toolkit=toolkit,
        )
