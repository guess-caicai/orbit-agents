# runtime_context.py
from datetime import datetime


class RuntimeContextBuilder:

    context = None

    def build_runtime_context(self, query: str):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.context = query
        return (
            f"当前时间: {now}\n"
            f"用户输入: {self.context}\n"
        )
