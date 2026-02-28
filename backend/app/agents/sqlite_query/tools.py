import os
import json
import sqlite3
from typing import Any, Dict, Optional
from agentscope.message import TextBlock
from agentscope.tool import ToolResponse
from dotenv import load_dotenv
from backend.app.agents.tool_input_sanitizer import sanitize_tool_inputs

load_dotenv()


def _get_db_path() -> str:
    path = os.getenv("SQLITE_DB_PATH")
    if path:
        return path
    # 默认使用项目内 knowledge.db（可按需修改）
    return os.path.join("backend", "knowledge.db")


def _validate_sql(sql: str) -> None:
    sql_strip = sql.strip().lower()
    if not sql_strip:
        raise ValueError("SQL 为空")

    allowed_prefixes = ("select", "with", "pragma")
    if not sql_strip.startswith(allowed_prefixes):
        raise ValueError("仅允许只读查询（SELECT / WITH / PRAGMA）")

    forbidden = ["insert", "update", "delete", "replace", "create", "drop", "alter", "truncate"]
    for kw in forbidden:
        if kw in sql_strip:
            raise ValueError("检测到非只读关键字，已阻止执行")


def execute_sqlite_query(sql: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    _validate_sql(sql)
    db_path = _get_db_path()

    if not os.path.exists(db_path):
        raise FileNotFoundError(f"数据库不存在: {db_path}")

    uri = f"file:{db_path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(sql, params or {})
        rows = cur.fetchmany(200)
        columns = [col[0] for col in cur.description] if cur.description else []
        data = [dict(row) for row in rows]
        return {
            "db_path": db_path,
            "columns": columns,
            "rows": data,
            "row_count": len(data),
        }
    finally:
        conn.close()


@sanitize_tool_inputs
def query_sqlite(sql: str, params: Optional[Dict[str, Any]] = None) -> ToolResponse:
    """{只读查询 SQLite 数据库}
    Args:
        sql (str): 查询语句（仅允许 SELECT / WITH / PRAGMA）
        params (dict, optional): 命名参数，例如 {"id": 1}
    """
    try:
        result = execute_sqlite_query(sql, params)
        text_block = TextBlock(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))
        return ToolResponse(content=[text_block])
    except Exception as e:
        text_block = TextBlock(type="text", text=f"SQLite 错误：{str(e)}")
        return ToolResponse(content=[text_block])
