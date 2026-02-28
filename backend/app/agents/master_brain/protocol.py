# app.agents.master_brain.protocol.py
from typing import List, Optional, Literal
from pydantic import BaseModel

ActionType = Literal["keep", "route", "delegate"]


class SubTask(BaseModel):
    agent: str
    input: str


class Decision(BaseModel):
    action: ActionType
    target_agent: Optional[str] = None
    sub_tasks: Optional[List[SubTask]] = None
