# app/rag/storage.py
import sqlite3
import json
import threading
import time
from backend.app.rag.schema import KBItem


class SQLiteKnowledgeStorage:

    def __init__(self, db_path="knowledge.db"):
        self.db_path = db_path
        self._local = threading.local()
        self._write_lock = threading.Lock()
        self._init_lock = threading.Lock()
        self._table_initialized = False

    def _get_conn(self):
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._init_pragmas(conn)
            self._local.conn = conn
        self._ensure_table(conn)
        return conn

    def _init_pragmas(self, conn):
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
        except Exception as e:
            import logging
            logging.error(msg=f"Unexpected error while initializing pragmas: {e}", exc_info=True)
            pass

    def _ensure_table(self, conn):
        if self._table_initialized:
            return
        with self._init_lock:
            if self._table_initialized:
                return
            conn.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_items (
                id TEXT PRIMARY KEY,
                kb_type TEXT,
                content TEXT,
                embedding TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            conn.commit()
            self._table_initialized = True

    def save_item(self, kb_type: str, item: KBItem):
        conn = self._get_conn()
        with self._write_lock:
            self._retry_write(conn, lambda c: c.execute(
                """
                INSERT OR REPLACE INTO knowledge_items
                (id, kb_type, content, embedding, metadata)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    item.id,
                    kb_type,
                    item.content,
                    json.dumps(item.embedding),
                    json.dumps(item.metadata),
                )
            ))
            conn.commit()

    def save_items(self, kb_type: str, items: list[KBItem]):
        if not items:
            return
        conn = self._get_conn()
        rows = [
            (
                item.id,
                kb_type,
                item.content,
                json.dumps(item.embedding),
                json.dumps(item.metadata),
            )
            for item in items
        ]
        with self._write_lock:
            self._retry_write(conn, lambda c: c.executemany(
                """
                INSERT OR REPLACE INTO knowledge_items
                (id, kb_type, content, embedding, metadata)
                VALUES (?, ?, ?, ?, ?)
                """,
                rows
            ))
            conn.commit()

    def delete_item(self, item_id: str):
        conn = self._get_conn()
        with self._write_lock:
            self._retry_write(conn, lambda c: c.execute(
                "DELETE FROM knowledge_items WHERE id = ?",
                (item_id,)
            ))
            conn.commit()

    def load_by_type(self, kb_type: str) -> list[KBItem]:
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT id, content, embedding, metadata FROM knowledge_items WHERE kb_type = ?",
            (kb_type,)
        )
        items = []
        for row in cursor.fetchall():
            items.append(
                KBItem(
                    id=row[0],
                    content=row[1],
                    embedding=json.loads(row[2]),
                    metadata=json.loads(row[3]),
                )
            )
        return items

    def close(self):
        try:
            conn = getattr(self._local, "conn", None)
            if conn is not None:
                conn.close()
                self._local.conn = None
        except Exception as e:
            import logging
            logging.error(msg=f"Unexpected error while closing connection: {e}", exc_info=True)
            pass

    def _retry_write(self, conn, op, retries: int = 3, base_delay: float = 0.05):
        last_exc = None
        for i in range(retries):
            try:
                return op(conn)
            except sqlite3.OperationalError as e:
                last_exc = e
                if "locked" not in str(e).lower():
                    raise
                time.sleep(base_delay * (2 ** i))
        if last_exc:
            raise last_exc
