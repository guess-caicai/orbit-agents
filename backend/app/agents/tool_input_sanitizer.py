# tool_input_sanitizer.py
import json
import logging
from typing import Any
from functools import wraps


def auto_fix(value: Any):
    """
    自动修复 LLM 传入的参数：
    - JSON 字符串 -> 对象
    - 单值 -> list
    - 递归处理
    """
    #  字符串尝试转 JSON
    if isinstance(value, str):
        value = value.strip()
        try:
            return auto_fix(json.loads(value))
        except Exception as e:
            print(f"[WARN] 未解析出 JSON 数据: {e}")
            return value

    #  list 递归
    if isinstance(value, list):
        return [auto_fix(v) for v in value]

    #  dict 递归
    if isinstance(value, dict):
        return {k: auto_fix(v) for k, v in value.items()}

    return value


def sanitize_tool_inputs(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        new_kwargs = {k: auto_fix(v) for k, v in kwargs.items()}
        return func(*args, **new_kwargs)
    return wrapper
