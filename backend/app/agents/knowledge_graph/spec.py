from backend.app.agents.base import AgentSpec
from agentscope.agent import ReActAgent
from agentscope.model import DashScopeChatModel
from agentscope.memory import InMemoryMemory
from agentscope.formatter import DashScopeChatFormatter
from agentscope.tool import Toolkit
from agentscope import init
from dotenv import load_dotenv
from backend.app.agents.knowledge_graph.tools import (
    query_graph,
    get_labels,
    get_relationship_types,
    get_node_properties,
)
import os

load_dotenv()
init()


class KnowledgeGraphAgentSpec(AgentSpec):
    name = "graph_agent"
    description = "知识图谱检索与持续学习 Agent（可自动写入/更新，保留最近5版）"

    def create(self, session_id: str):
        toolkit = Toolkit()
        toolkit.register_tool_function(query_graph)
        toolkit.register_tool_function(get_labels)
        toolkit.register_tool_function(get_relationship_types)
        toolkit.register_tool_function(get_node_properties)

        max_versions = int(os.getenv("KG_MAX_VERSIONS", "5"))

        system_prompt = f"""
        你是一个知识图谱智能体，面向用户输入做图谱检索与持续学习。
        
        【核心能力】
        - 查询：基于 Cypher 检索图谱
        - 自动写入：根据用户输入进行增量创建/更新
        - 持续学习：每次写入都生成版本快照
        - 可进化：schema 发现与自适应
        - 版本保留：只保留最近 {max_versions} 版
        
        【强约束】
        1) 任何读/写操作必须调用 query_graph
        2) 禁止编造结果，必须基于 query_graph 返回
        3) 写入必须包含来源信息：source_id + source_type='user'
        4) 更新必须创建新版本，不覆盖旧版本
        5) 版本数>{max_versions} 时必须删除最旧版本（仅删 Version，不删 Entity）
        6) 查询必须加 LIMIT（除非用户明确要求全量）
        7) 禁止危险操作（整库删除/清库）
        
        【推荐数据结构】
        - (:Entity {{id, type, name, ...}})
        - (:Version {{entity_id, version, created_at, diff, source_id}})
        - (:Source {{source_id, source_type, created_at}})
        - (:IngestionLog {{log_id, source_id, created_at, cypher, result, success}}
        )
        
        关系示例：
        - (Entity)-[:HAS_VERSION]->(Version)
        - (Version)-[:FROM_SOURCE]->(Source)
        - (IngestionLog)-[:FOR_SOURCE]->(Source)
        
        【工作流】
        1) 识别意图：查询 / 写入 / 更新 / 纠错
2) 若 schema 不明确，先做 schema discovery（优先使用 get_labels / get_relationship_types / get_node_properties）
        3) 生成 Cypher
        4) 调用 query_graph 执行
        5) 输出：简洁解释 + 关键结果（含 counters）
        
        【写入/更新规则】
        - 新实体：创建 Entity + Version v1 + Source + IngestionLog
        - 已有实体：读取最新版本，计算 diff，创建新 Version（version+1）
        - 若版本数>{max_versions}：删除最旧 Version
        - 每次写入都必须创建 IngestionLog
        
        【输出风格】
        - 简洁、直接、可验证
        - 如果是更新/写入，说明版本号变化与写入数量
        """

        model = DashScopeChatModel(
            model_name="qwen3-max-2026-01-23",
            api_key=os.getenv("DASHSCOPE_API_KEY15"),
            stream=True,
            enable_thinking=False,
        )

        return ReActAgent(
            name=f"graph_agent_{session_id}",
            sys_prompt=system_prompt,
            model=model,
            formatter=DashScopeChatFormatter(),
            memory=InMemoryMemory(),
            toolkit=toolkit,
        )
