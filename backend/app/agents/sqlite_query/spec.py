from backend.app.agents.base import AgentSpec
from agentscope.agent import ReActAgent
from agentscope.model import DashScopeChatModel
from agentscope.memory import InMemoryMemory
from agentscope.formatter import DashScopeChatFormatter
from agentscope.tool import Toolkit
from agentscope import init
from backend.app.agents.sqlite_query.tools import *

load_dotenv()
init()


class SqliteQueryAgentSpec(AgentSpec):
    name = "sqlite_query_agent"
    description = "SQLite 数据库只读查询 Agent"

    def create(self, session_id: str):
        toolkit = Toolkit()
        toolkit.register_tool_function(query_sqlite)

        system_prompt = """
            你是一个 SQLite 只读查询助手。

            可用工具：
            - query_sqlite 通过查询语句查询相应信息
            
            【SQLite 规则】
            1. 只允许 SELECT / WITH / PRAGMA。
            2. 涉及数据库前，必须先执行：
               SELECT name FROM sqlite_master WHERE type='table';
                禁止猜表名。
            3. 使用表前必须执行：
               PRAGMA table_info(table_name);
                禁止猜字段。
            4. 时间字段精确到【秒】：
                禁止 = / DATE / strftime
                只能使用 LIKE / BETWEEN / >= <=（字符串比较）。
                注意：
                LIKE 不支持正则
                时间请使用 BETWEEN
            5. 未确认 schema 不得查询。
            【IP 规则】
            - 仅在用户明确要求 IP 信息时调用 query_ip_info
            - 支持批量 IP
            【输出】
            - 简洁直接，无推测
            """

        model = DashScopeChatModel(
            model_name="qwen3-max-2026-01-23",
            api_key=os.getenv("DASHSCOPE_API_KEY16"),
            stream=True,
            enable_thinking=False,
        )

        return ReActAgent(
            name=f"sqlite_query_{session_id}",
            sys_prompt=system_prompt,
            model=model,
            formatter=DashScopeChatFormatter(),
            memory=InMemoryMemory(),
            toolkit=toolkit,
        )
