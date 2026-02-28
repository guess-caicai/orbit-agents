from fastapi import Request


def get_session_manager(request: Request):
    return request.app.state.session_manager


def get_orchestrator(request: Request):
    return request.app.state.orchestrator


def get_kb_writer(request: Request):
    return request.app.state.kb_writer
