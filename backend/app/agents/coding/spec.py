from backend.app.agents.base import AgentSpec
from agentscope.agent import ReActAgent
from agentscope.model import DashScopeChatModel
from agentscope.memory import InMemoryMemory
from agentscope.formatter import DashScopeChatFormatter
from agentscope.tool import execute_python_code, Toolkit
from agentscope import init
from backend.app.agents.coding.tools import *
load_dotenv()
init()


class CodingAgentSpec(AgentSpec):
    """
    专职程序员智能体：
    - 项目搭建
    - 写代码
    - 改代码
    - 查 Bug
    - 运行代码验证
    """

    name = "coding_agent"
    description = "专业的软件工程智能体（Coding Agent），可以根据需求实现整个项目的搭建"

    def create(self, session_id: str):
        toolkit = Toolkit()
        toolkit.register_tool_function(execute_python_code)
        toolkit.register_tool_function(generate_code_with_deepseek)
        toolkit.register_tool_function(lint_coding)
        toolkit.register_tool_function(read_file)
        toolkit.register_tool_function(write_file)
        toolkit.register_tool_function(list_dir)
        toolkit.register_tool_function(create_project_tree)
        # -------- Model --------
        model = DashScopeChatModel(
            model_name="qwen-max",
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            stream=True,
            enable_thinking=True,
        )

        # -------- System Prompt（升级重点）--------
        system_prompt = """
           你是一个专业的软件工程智能体（Coding Agent），专注于项目级代码实现与维护。
                【可用工具】
                你可以通过以下工具与代码或项目交互：
                - execute_python_code  ：用于运行 Python 代码、确认 Bug 行为
                - generate_code_with_deepseek  ：用于生成“完整且可运行”的代码实现
                - lint_coding  ： 用于静态检查代码的语法、结构与基本规范问题
                - read_file ：文件内容的读取
                - write_file ：写入内容到指定的文件中
                - list_dir：列出内指定目录的内容
                - create_project_tree：在受限的项目空间内，根据结构化字典批量创建项目目录与文件
            你要做的：
            - 根据用户需求合理调用工具实现项目的搭建和代码的撰写
            - 你可以根据用户的需求利用 create_project_tree 快速搭建项目结构
            - 根据业务难度决定是否调用 generate_code_with_deepseek 工具求助deepseek
            - 获取代码后需要调动 write_file 写入到搭建好的项目文件中
            - 高灵活度的调用已有工具实现项目搭建和审查
            【提交规则（非常重要）】
            - 当 generate_code_with_deepseek 已返回完整代码时，视为实现已确认
            - 必须立即调用 write_file 将代码写入对应文件
            - 不允许停留在自然语言描述阶段  
            """

        formatter = DashScopeChatFormatter()
        memory = InMemoryMemory()

        return ReActAgent(
            name=f"{self.name}_{session_id}",
            sys_prompt=system_prompt,
            model=model,
            formatter=formatter,
            memory=memory,
            toolkit=toolkit,
        )
