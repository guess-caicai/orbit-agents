# agents/search_online/spec.py
from backend.app.agents.base import AgentSpec
from agentscope.agent import ReActAgent
from agentscope.model import DashScopeChatModel
from agentscope.memory import InMemoryMemory
from agentscope.formatter import DashScopeChatFormatter
from agentscope.tool import Toolkit
from agentscope import init
from backend.app.agents.connect_online.tools import *

load_dotenv()
init()


class ConnectOnlineAgentSpec(AgentSpec):
    name = "connect_online_agent"
    description = "一个智能联网Agent 可以进行 联网搜索 / 天气查询 / 路线规划 / 邮件发送 / IP信息(地理位置，运营商)获取 "

    def create(self, session_id: str):
        toolkit = Toolkit()
        toolkit.register_tool_function(search_web)
        toolkit.register_tool_function(search_weather)
        toolkit.register_tool_function(search_weather_forecast)
        toolkit.register_tool_function(search_amap_drive)
        toolkit.register_tool_function(send_email_tool)
        toolkit.register_tool_function(query_ip_info)

        return ReActAgent(
            name=f"{self.name}_{session_id}",
            sys_prompt="""
            你是一个可以进行多元联网搜索和执行的智能助手。
            你可以使用以下工具：
            1. search_web(query: str)：当问题需要最新信息、事实、背景资料时必须使用
            2.search_amap_drive(start:str ,end:str )：查询起始地到目的地的路线规划
            3.search_weather(location: str)：查询指定地点目前的天气情况
            4.search_weather_forecast(location: str, days: int = 3)：查询指定地点指定天数内的天气预测默认为近3天
            5.send_email_tool(to_email: str, subject: str, content: str)：向指定邮件方发送邮件
            6.query_ip_info(ips: Union[List[str], List[Dict[str, Any]]])：批量查询IP地址的相关信息
            规则：
            - 涉及“搜索 / 查询 / 资料 / 最新情况” → 必须先调用 search_web
            - 涉及“路线规划 / 查询地址 / 地方资料 / ” → 必须调用 search_amap_drive
            - 涉及“天气查询 / 天气预报 / 温度变化 / ” → 必须调用 search_weather，search_weather_forecast
            - 涉及“邮件发送 / 日报发送 / 行程表发送 / ” → 必须调用 send_email_tool
            - 设计“IP地理位置 / IP运营商信息 查询时 ” → 必须调用 query_ip_info
            """,
            model=DashScopeChatModel(
                model_name="qwen-max",
                api_key=os.getenv("DASHSCOPE_API_KEY"),
                stream=True,
                enable_thinking=True,
            ),
            formatter=DashScopeChatFormatter(),
            toolkit=toolkit,
            memory=InMemoryMemory(),
        )
