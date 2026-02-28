from fastapi import APIRouter, HTTPException, Form, Depends
from typing import Optional
from backend.app.agents.master_brain.protocol import Decision
from backend.app.dependencies import get_session_manager, get_orchestrator

router = APIRouter()


@router.post("/agent/session/create")
async def create_session(session_id: str, session_manager=Depends(get_session_manager)):
    session = await session_manager.get_or_create(session_id)
    return {
        "session_id": session.session_id,
        "status": "created",
        "agents": list(session.agents.keys()),
    }


@router.delete("/agent/session/delete")
async def delete_session(session_id: str, session_manager=Depends(get_session_manager)):
    ok = await session_manager.delete(session_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "session_id": session_id,
        "status": "deleted",
    }


@router.get("/agent/session/list")
async def list_sessions(session_manager=Depends(get_session_manager)):
    sessions = session_manager.list_sessions()
    return {
        "sessions": sessions,
        "count": len(sessions),
    }


@router.post("/agent/chat")
async def chat(
    session_id: str = Form(),
    query: str = Form(),
    session_manager=Depends(get_session_manager),
    orchestrator=Depends(get_orchestrator),
):

    session = await session_manager.get_or_create(session_id)
    agent = await session_manager.get_agent(session, agent_name="search_online")

    decision = Decision(action="keep")
    result = await orchestrator.handle(
        session=session,
        query=query,
        decision=decision,
        agent=agent,
    )

    return {
        "session_id": session_id,
        "agent": "search_online",
        "mode": "single",
        "result": result,
    }


@router.post("/agent/chatMasterBrain")
async def chat_master_brain(
    session_id: str = Form(),
    query: str = Form(),
    force_agent: Optional[str] = None,
    session_manager=Depends(get_session_manager),
    orchestrator=Depends(get_orchestrator),
):
    """支持智能路由的聊天接口"""
    try:
        session = await session_manager.get_or_create(session_id)
        decision, agent = await session_manager.decide_and_get_agent(
            session=session,
            query=query,
            force_agent=force_agent,
        )

        result = await orchestrator.handle(
            session=session,
            query=query,
            decision=decision,
            agent=agent,
        )

        agent_name = decision.target_agent or session.current_agent
        if hasattr(session_manager, "log_interaction"):
            if isinstance(result, dict):
                preview = str(result)[:100]
            else:
                preview = result[:100] if result else ""
            await session_manager.log_interaction(
                session_id=session_id,
                agent=agent_name,
                query=query,
                result=preview,
            )

        return {
            "session_id": session_id,
            "agent": agent_name,
            "routing_type": "intelligent" if not force_agent else "forced",
            "decision": decision.model_dump(),
            "result": result,
            "session_info": {
                "conversation_depth": session.routing_context.get("conversation_depth", 0),
                "agent_history_count": len(session.agent_history),
            },
        }

    except Exception as e:
        return {
            "session_id": session_id,
            "error": str(e),
            "fallback_agent": "search_online",
            "suggestion": "请尝试重新发送或指定具体Agent",
        }
