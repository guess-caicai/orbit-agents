from agentscope.tool import ToolResponse
from agentscope.message import (
    TextBlock,
)
from dotenv import load_dotenv
import requests
import os

load_dotenv()
PROJECT_ROOT = "D:/agent_workspace"
PROJECT_ROOT = os.path.normcase(os.path.abspath(PROJECT_ROOT))
assert os.path.isabs(PROJECT_ROOT), "PROJECT_ROOT must be absolute"


def _ensure_root():
    os.makedirs(PROJECT_ROOT, exist_ok=True)


# 路径规范 + 越权拦截
def resolve_path(path: str) -> str:
    abs_root = os.path.abspath(PROJECT_ROOT)
    abs_path = os.path.abspath(os.path.join(abs_root, path))

    if os.path.commonpath([abs_root, abs_path]) != abs_root:
        raise PermissionError("Access outside sandbox is forbidden")

    return abs_path


def read_file(path: str) -> ToolResponse:
    """{读取指定路径的文本文件内容（sandbox 内）}
    Args:
        path (str):
            {需要读取的文件路径}
    """
    abs_path = resolve_path(path)
    try:
        if not os.path.exists(abs_path):
            raise FileNotFoundError(f"File not found: {path}")
    
        if os.path.isdir(abs_path):
            raise IsADirectoryError(f"{path} is a directory")
    
        with open(abs_path, "r", encoding="utf-8") as f:
            content = f.read()
            text_block = TextBlock(type="text", text=content)
            return ToolResponse(content=[text_block])
    except Exception as e:
        content = f"读取文件失败：{e}"
        text_block = TextBlock(type="text", text=content)
        return ToolResponse(content=[text_block])


def write_file(path: str, content: str, overwrite: bool = True) -> ToolResponse:
    """{写入文本文件（sandbox 内）}
    Args:
        path (str):
            {写入内容的文件路径}
        content (str):
            {待写入的文本内容}
        overwrite (bool):
            {是否覆盖已存在的文件；默认为 True，若设为 False 且文件已存在则报错}
    """
    abs_path = resolve_path(path)
    try:
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    
        if os.path.exists(abs_path) and not overwrite:
            raise FileExistsError(f"File exists: {path}")
    
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content)
        content = f"Written: {path}"
        text_block = TextBlock(type="text", text=content)
        return ToolResponse(content=[text_block])
    except Exception as e:
        content = f"写入文件失败：{e}"
        text_block = TextBlock(type="text", text=content)
        return ToolResponse(content=[text_block])


def list_dir(path: str = ".") -> ToolResponse:
    """{列出 sandbox 内指定目录的内容}
    Args:
        path (str):
            {目标目录路径；默认为当前目录 "."}
    """   
    abs_path = resolve_path(path)
    try:
        if not os.path.exists(abs_path):
            raise FileNotFoundError(path)
    
        if not os.path.isdir(abs_path):
            raise NotADirectoryError(path)
        items = sorted(os.listdir(abs_path))
        text_block = TextBlock(type="text", text="\n".join(items))
        return ToolResponse(content=[text_block])
    except Exception as e:
        content = f"获取文件目录失败：{e}"
        text_block = TextBlock(type="text", text=content)
        return ToolResponse(content=[text_block])


def file_exists(path: str) -> ToolResponse:
    """{判断文件或目录是否存在}
    Args:
        path (str):
            {检验是否存在的文件或目录的路径}
    """
    try:
        abs_path = resolve_path(path)
    except PermissionError:
        content = "文件或目录不存在"
        text_block = TextBlock(type="text", text=content)
        return ToolResponse(content=[text_block])
    text_block = TextBlock(type="text", text=str(os.path.exists(abs_path)))
    return ToolResponse(content=[text_block])


def search_code(keyword: str, path: str = ".") -> ToolResponse:
    """{在受限的 sandbox 项目空间内，对文本源码文件进行关键字搜索}
    Args:
        keyword (str):
            {要搜索的字符串关键字，区分大小写,应为明确的函数名、变量名、配置项或错误信息片段}
        path (str):
            {搜索起始目录的相对路径（相对于项目根目录）默认 "." 表示整个项目}
    """
    abs_root = resolve_path(path)
    results = []

    for root, _, files in os.walk(abs_root):
        for name in files:
            if not name.endswith((".py", ".txt", ".md", ".json", ".yaml", ".yml")):
                continue

            file_path = os.path.join(root, name)
            rel_path = os.path.relpath(file_path, PROJECT_ROOT)

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    for idx, line in enumerate(f, start=1):
                        if keyword in line:
                            results.append({
                                "file": rel_path,
                                "line": idx,
                                "content": line.strip()
                            })
            except Exception as e:
                import logging
                logging.error(f"Unexpected error while reading file: {e}", exc_info=True)
                continue
    text_block = TextBlock(type="text", text="\n".join(map(str, results)))
    return ToolResponse(content=[text_block])


def create_project_tree(tree: dict, base_path: str = ".") -> ToolResponse:
    """{在受限的 sandbox 项目空间内，根据结构化字典批量创建项目目录与文件。}
    Args:
        tree (dict):
            {项目结构描述字典，必须是合法的嵌套 dict不允许包含绝对路径或路径穿越（如 ../）
            参数示例： tree = {
                "app": {
                    "__init__.py": "",
                    "main.py": "",
                    "api": {
                        "__init__.py": "",
                        "router.py": ""
                    }
                },
                "tests": {
                    "__init__.py": "",
                    "test_main.py": ""
                },
                "README.md": "# Project"
            }}
        base_path (str):
            {项目创建的起始目录，相对于 sandbox 项目根目录,默认 "." 表示在项目根目录下创建}
    """
    base_abs = resolve_path(base_path)

    def _create(node: dict, current_path: str):
        for name, value in node.items():
            target = os.path.join(current_path, name)
            if isinstance(value, dict):
                os.makedirs(target, exist_ok=True)
                _create(value, target)
            else:
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with open(target, "w", encoding="utf-8") as f:
                    f.write(value or "")

    _create(tree, base_abs)
    text_block = TextBlock(type="text", text="Project structure created")
    return ToolResponse(content=[text_block])


def generate_code_with_deepseek(
    requirement: str,
    language: str = "python",
) -> ToolResponse:
    """{使用 DashScope 通道的 DeepSeek 模型生成代码只返回最终可用代码，不包含解释}
    Args:
        requirement (str):
            {生成完整代码需求说明}
        language (str):
            {代码语言类型}
    """
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        content = "DASHSCOPE_API_KEY not set"
        text_block = TextBlock(type="text", text=content)
        return ToolResponse(content=[text_block])

    url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"

    system_prompt = f"""
        你是一个专业的软件工程师。
        请使用 {language} 编写【完整、可运行】的代码。
        要求：
        - 只输出代码
        - 不要解释
        - 不要 markdown
        """

    payload = {
        "model": "deepseek-v3.2",
        "input": {
            "messages": [
                {"role": "system", "content": system_prompt.strip()},
                {"role": "user", "content": requirement},
            ]
        },
        "parameters": {
            "enable_thinking": False,
            "incremental_output": False,
            "result_format": "message",
        },
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=180,
            )
        resp.raise_for_status()
        data = resp.json()

        message = data["output"]["choices"][0]["message"]
        content = message.get("content")

        # -------- 核心修复逻辑 --------
        # 情况 1：直接是字符串
        if isinstance(content, str):
            code = content.strip()
        # 情况 2：是结构化 list
        elif isinstance(content, list):
            parts = []
            for item in content:
                if not isinstance(item, dict):
                    continue
                text = item.get("text")
                if text:
                    parts.append(text)
            code = "\n".join(parts).strip()
        else:
            code = ""
        if not code:
            text_block = TextBlock(type="text", text="No code generated.")
            return ToolResponse(content=[text_block])
        code = [TextBlock(type="text", text=code)]
        return ToolResponse(content=code)
    except requests.exceptions.Timeout:
        content = "DeepSeek generation timeout (model is slow, retry recommended)"
        text_block = TextBlock(type="text", text=content)
        return ToolResponse(content=[text_block])
    except Exception as e:
        content = f"DeepSeek code generation failed：{e}"
        text_block = TextBlock(type="text", text=content)
        return ToolResponse(content=[text_block])


def lint_coding(code: str) -> ToolResponse:
    """{对 Python 代码做基础静态检查（语法级）}
    Args:
        code (str):
            {需要检查的代码段}
    """
    try:
        compile(code, "<string>", "exec")
        text_block = [TextBlock(type="text", text="Syntax OK")]
        return ToolResponse(content=text_block)
    except SyntaxError as e:
        text_block = [TextBlock(type="text", text=f"Syntax Error: {e.msg}")]
        return ToolResponse(content=text_block)
