import argparse
import json
import os
import sys
import uuid
import requests


def load_session_id(path: str) -> str | None:
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            value = f.read().strip()
            return value or None
    except Exception as e:
        print(f"[load_session_id_error] {e}")
        return None


def save_session_id(path: str, session_id: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(session_id)


def chat_loop(base_url: str, session_id: str) -> None:
    print(f"[session_id] {session_id}")
    print("输入 /exit 退出，/new 新会话，/sid 查看当前会话ID。")
    while True:
        try:
            user_input = input("你> ").strip()
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
            print(f"已创建新会话: {session_id}")
            continue

        try:
            resp = requests.post(
                f"{base_url}/api/agent/chatMasterBrain",
                data={"session_id": session_id, "query": user_input},
                timeout=120,
            )
            resp.raise_for_status()
            data = resp.json()
            if "error" in data:
                print(f"[error] {data['error']}")
                continue
            result = data.get("result")
            if isinstance(result, dict):
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                print(f"助手> {result}")
        except Exception as e:
            print(f"[request_error] {e}")


def main() -> None:
    parser = argparse.ArgumentParser(description="AgentProject CLI")
    parser.add_argument(
        "--base-url",
        default="http://localhost:8010",
        help="FastAPI 服务地址，默认 http://localhost:8010",
    )
    parser.add_argument(
        "--session-id",
        default=None,
        help="指定会话ID（不指定则自动读取或生成）",
    )
    parser.add_argument(
        "--session-file",
        default=os.path.join("backend", ".session_id"),
        help="会话ID保存路径",
    )
    args = parser.parse_args()

    session_id = args.session_id or load_session_id(args.session_file) or str(uuid.uuid4())
    save_session_id(args.session_file, session_id)

    chat_loop(args.base_url, session_id)


if __name__ == "__main__":
    main()
