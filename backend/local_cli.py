import argparse
import json
import os
import sys
import uuid
import asyncio
from dotenv import load_dotenv
from backend.app.sessions.manager import SessionManager
from backend.app.sessions.orchestrator import SessionOrchestrator
from backend.app.agents.master_brain.protocol import Decision
import backend.app.agents  # 注册所有 Agent
load_dotenv()


def safe_input(prompt: str = "") -> str:
    try:
        # 如果是交互式终端，优先用 input（体验最好）
        if sys.stdin.isatty():
            return input(prompt).strip()
        # 非 TTY（管道 / Docker / CI）
        sys.stdout.write(prompt)
        sys.stdout.flush()
        data = sys.stdin.buffer.readline()
        if not data:
            return ""
        return data.decode("utf-8", errors="ignore").strip()
    except EOFError:
        return ""


def load_session_id(path: str) -> str | None:
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            value = f.read().strip()
            return value or None
    except Exception:
        return None


def save_session_id(path: str, session_id: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(session_id)


def print_help():
    print("命令：/exit 退出，/new 新会话，/sid 当前会话ID，/force <agent> 强制指定Agent，/help 帮助")


def run(coro):
    return asyncio.run(coro)


def main() -> None:
    parser = argparse.ArgumentParser(description="AgentProject Local CLI")
    parser.add_argument(
        "--session-id",
        default=None,
        help="指定会话ID（不指定则自动读取或生成）",
    )
    parser.add_argument(
        "--session-file",
        default=os.path.join("session_id_dir", ".session_id_local"),
        help="会话ID保存路径",
    )
    parser.add_argument(
        "--force-agent",
        default=None,
        help="强制指定Agent（如 search_online / rag_agent / coding_agent）",
    )
    args = parser.parse_args()

    session_id = args.session_id or load_session_id(args.session_file) or str(uuid.uuid4())
    save_session_id(args.session_file, session_id)

    session_manager = SessionManager()
    orchestrator = SessionOrchestrator()

    print(f"[session_id] {session_id}")
    print_help()

    force_agent = args.force_agent

    while True:
        try:
            user_input = safe_input("你> ")
        except (EOFError, KeyboardInterrupt):
            print("\n已退出。")
            return

        if not user_input:
            continue
        if user_input == "/exit":
            print("已退出。")
            return
        if user_input == "/sid":
            print(f"当前会话ID: {session_id}")
            continue
        if user_input == "/new":
            session_id = str(uuid.uuid4())
            save_session_id(args.session_file, session_id)
            print(f"已创建新会话: {session_id}")
            continue
        if user_input.startswith("/force "):
            force_agent = user_input.replace("/force ", "", 1).strip() or None
            print(f"强制Agent: {force_agent}")
            continue
        if user_input == "/help":
            print_help()
            continue

        session = run(session_manager.get_or_create(session_id))

        if force_agent:
            decision = Decision(action="route", target_agent=force_agent)
        else:
            decision = run(session_manager.decide(session=session, query=user_input))

        decision, agent = run(
            session_manager.apply_decision(session=session, decision=decision, query=user_input)
        )

        result = run(
            orchestrator.handle(session=session, query=user_input, decision=decision, agent=agent)
        )

        if isinstance(result, dict):
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"助手> {result}")


if __name__ == "__main__":
    main()
