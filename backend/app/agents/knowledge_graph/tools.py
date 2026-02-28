from agentscope.tool import ToolResponse
from dotenv import load_dotenv
from backend.app.graph.graph_pool import Neo4jPool
import os
import json
import time
from typing import Any, Dict
from agentscope.message import TextBlock

load_dotenv()
neo4j_pool = Neo4jPool(
    url=os.getenv("NEO4J_URL"),
    user=os.getenv("NEO4J_USER"),
    password=os.getenv("NEO4J_PASSWORD"),
    database=os.getenv("NEO4J_DB"),
).create_driver()

_MAX_RETURN = int(os.getenv("KG_MAX_RETURN", "200"))
_MAX_LIMIT = int(os.getenv("KG_QUERY_LIMIT", str(_MAX_RETURN)))
_TIMEOUT_SEC = float(os.getenv("KG_QUERY_TIMEOUT_SEC", "0") or "0")
_READONLY = os.getenv("KG_READONLY", "false").strip().lower() in ("1", "true", "yes")
_LOG_PATH = os.getenv("KG_LOG_PATH", "").strip()


def _log_query(payload: Dict[str, Any]) -> None:
    if not _LOG_PATH:
        return
    try:
        with open(_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception as e:
        print("warning:", e)
        pass


def _has_write_keywords(cypher: str) -> bool:
    lower = cypher.lower()
    write_keywords = [
        "create ",
        "merge ",
        "set ",
        "delete ",
        "detach delete",
        "remove ",
        "drop ",
        "call dbms",
        "call apoc",
    ]
    return any(k in lower for k in write_keywords)


def _guard_cypher(cypher: str):
    lower = cypher.lower()

    dangerous = [
        "detach delete",
        "drop database",
        "drop graph",
        "create database",
        "call dbms",
    ]
    if any(k in lower for k in dangerous):
        raise ValueError("操作风险过高，已阻止")

    if _READONLY and _has_write_keywords(cypher):
        raise ValueError("read-only 模式下禁止写入/更新/删除操作")


def _ensure_limit(cypher: str) -> str:
    lower = cypher.lower()
    if "limit" in lower:
        return cypher
    if _has_write_keywords(cypher):
        return cypher
    if ";" in cypher.strip().rstrip(";"):
        return cypher
    if "return" not in lower and not lower.strip().startswith("call"):
        return cypher
    trimmed = cypher.strip().rstrip(";")
    return f"{trimmed} LIMIT {_MAX_LIMIT}"


def _execute_cypher(cypher: str) -> Dict[str, Any]:
    _guard_cypher(cypher)
    cypher = _ensure_limit(cypher)

    with neo4j_pool.session() as se:
        if _TIMEOUT_SEC > 0:
            res = se.run(cypher, timeout=_TIMEOUT_SEC)
        else:
            res = se.run(cypher)

        records = [dict(r) for r in res]
        keys = res.keys()

        summary = res.consume()

        return {
            "columns": list(keys),
            "rows": records[:_MAX_RETURN],
            "row_count": len(records),
            "counters": {
                "nodes_created": summary.counters.nodes_created,
                "nodes_deleted": summary.counters.nodes_deleted,
                "relationships_created": summary.counters.relationships_created,
                "relationships_deleted": summary.counters.relationships_deleted,
                "properties_set": summary.counters.properties_set,
            },
        }


def _build_response(payload: Dict[str, Any]) -> ToolResponse:
    block = TextBlock(
        type="text",
        text=json.dumps(payload, ensure_ascii=False, indent=2),
    )
    return ToolResponse(content=[block])


def query_graph(cypher: str) -> ToolResponse:
    """{Neo4j 图数据库读写工具}
    Args:
        cypher (str):
            {可执行的 cypher 语句: - 查询 - 创建节点 - 创建关系 - 更新属性}
    """

    try:
        start = time.time()
        data = _execute_cypher(cypher)
        cost = round(time.time() - start, 3)

        payload = {
            "success": True,
            "time_cost": cost,
            "result": data,
        }
        _log_query(
            {
                "tool": "query_graph",
                "success": True,
                "time_cost": cost,
                "cypher": cypher,
                "row_count": data.get("row_count"),
                "counters": data.get("counters"),
            }
        )
        return _build_response(payload)

    except Exception as e:
        _log_query(
            {
                "tool": "query_graph",
                "success": False,
                "error": str(e),
                "cypher": cypher,
            }
        )
        return _build_response({"success": False, "error": str(e)})


def get_labels() -> ToolResponse:
    """{获取图谱 labels}"""
    try:
        cypher = """
                CALL db.labels()
                YIELD label
                RETURN label
                """
        data = _execute_cypher(cypher)
        return _build_response({"success": True, "result": data})
    except Exception as e:
        return _build_response({"success": False, "error": str(e)})


def get_relationship_types() -> ToolResponse:
    """{获取图谱关系类型}"""
    try:
        cypher = """
                CALL db.relationshipTypes()
                YIELD relationshipType
                RETURN relationshipType
                """
        data = _execute_cypher(cypher)
        return _build_response({"success": True, "result": data})
    except Exception as e:
        return _build_response({"success": False, "error": str(e)})


def get_node_properties() -> ToolResponse:
    """{获取节点属性schema}"""
    try:
        cypher = """
                CALL db.schema.nodeTypeProperties()
                YIELD nodeType, propertyName, propertyTypes, mandatory
                RETURN nodeType, propertyName, propertyTypes, mandatory
                """
        data = _execute_cypher(cypher)
        return _build_response({"success": True, "result": data})
    except Exception as e:
        return _build_response({"success": False, "error": str(e)})


if __name__ == "__main__":
    with neo4j_pool.session() as session:
        result = session.run("MATCH (n) RETURN n LIMIT 10")
        print(result)
