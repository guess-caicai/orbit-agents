from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from backend.app.agents.sqlite_query.tools import execute_sqlite_query

router = APIRouter()


class SqliteQueryPayload(BaseModel):
    sql: str
    params: Optional[Dict[str, Any]] = None


@router.post("/sqlite/query")
async def sqlite_query(payload: SqliteQueryPayload):
    try:
        result = execute_sqlite_query(payload.sql, payload.params)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
