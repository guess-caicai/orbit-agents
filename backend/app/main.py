# app/main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager
from backend.app.api.agent import router as agent_router
from backend.app.api.knowledge import router as knowledge_router
from backend.app.api.sqlite import router as sqlite_router
import backend.app.agents
from backend.app.sessions.manager import SessionManager
from backend.app.sessions.orchestrator import SessionOrchestrator
from backend.app.rag.multi_kb import MultiKnowledgeBase
from backend.app.rag.knowledge_writer import KnowledgeWriter
from backend.app.agents.search_rag import tools as rag_tools


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.session_manager = SessionManager()
    app.state.orchestrator = SessionOrchestrator()
    app.state.kb = MultiKnowledgeBase()
    app.state.kb_writer = KnowledgeWriter(app.state.kb)
    rag_tools.set_kb(app.state.kb)
    try:
        yield
    finally:
        kb = getattr(app.state, "kb", None)
        if kb and hasattr(kb, "close"):
            kb.close()


app = FastAPI(lifespan=lifespan)

# Include the agent router
app.include_router(agent_router, prefix="/api", tags=["Agent"])
app.include_router(knowledge_router, prefix="/api", tags=["Knowledge"])
app.include_router(sqlite_router, prefix="/api", tags=["SQLite"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8010)
