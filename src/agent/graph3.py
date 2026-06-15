import asyncio
import json
from typing import Dict, Any, List
from langchain_core.messages import ToolMessage, AIMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.constants import END, START
from langgraph.graph import StateGraph, MessagesState
from get_env import ZHIPU_API_KEY
from src.agent.my_llm import llm

# 配置 mcp
local_mcp_config = {
    'url': 'http://127.7.7.1:7777/streamable',
    "transport": "streamable_http",
}

# 可视化图表mcp
chart_mcp_server_config = {
    "url": "https://mcp.api-inference.modelscope.net/d28d57421afb4a/sse",
    "transport": "sse"
}

# 智普ai
search_mcp_server_config = {
    "url": f"https://open.bigmodel.cn/api/mcp-broker/proxy/web-search/mcp?Authorization={ZHIPU_API_KEY}",
    "transport": "streamable_http"
}

# 爬虫工具mcp
fetch_mcp_server_config = {
    "url": "https://mcp.api-inference.modelscope.net/1c0fa2fb594140/sse",
    "transport": "sse"
}

get12306_mcp_server_config = {
    "url": "https://mcp.api-inference.modelscope.net/df90ca00e66540/sse",
    "transport": "sse"
}





# 创建多 MCP 服务器
mcp_lient = MultiServerMCPClient(
    {
        # "gaode_mcp_server_config" : gaode_mcp_server_config,
        "search_mcp_server_config" : search_mcp_server_config,
        "fetch_mcp_server_config" : fetch_mcp_server_config,
        "get12306_mcp_server_config" : get12306_mcp_server_config,
        "chart_mcp_server_config" : chart_mcp_server_config,
        # "local_mcp_config" : local_mcp_config,
    }
)


# 自定义工具节点的类型与其中的函数
class BasicToolsNode:
    """
    创建工具调用节点，用于处理AIMessages中的工具调用请求
    功能:
    1. 接收工具列表并建立名称索引
    2. 并发执行消息中的工具调用请求
    3. 自动处理同步/异步适配
    """

    def __init__(self, tools: list):
        """
        初始化工具节点
        Args:
            tools: 工具列表，每个工具需有name属性

        """
        self.tools_name = {tool.name: tool for tool in tools}  # 得到所有工具名字

    async def __call__(self, state: Dict[str, Any]) -> Dict[str, List[ToolMessage]]:

        """
        工具异步调用
        Args:
            state: 图节点状态，有图执行的数据，包含 ‘messages’ 字段
        Returns:
            包含 ToolMessage 的字典
        Raises：
            ValueError： 输入无效时给出

        """
        if not (messages := state.get('messages')):
            raise  ValueError("未找到消息内容")
        message = messages[-1]

        output = await self._execute_tool_calls(message.tool_calls)
        return {'messages': output}




    async def _execute_tool_calls(self, tool_calls: List[Dict]) -> List[ToolMessage]:
        """
        实际执行工具调用
        Args:
            tool_calls: 模型工具调用请求
        Returns:
             本次所有工具执行结果 ToolMessage 的列表

        """

        # 定义单个工具调用的函数
        async def _invoke_tool(tool_call: Dict) -> ToolMessage:
            # tool_call为 AIMessage 中 tool_calls，具体为 list[ToolCall]
            # list[ToolCall] 为继承了 ToolCall类，里面包含了： name: str, args: dict[str, Any], id: Optional[str]
            """"
            单个工具调用
            Args:
                tool_call: 模型工具调用请求
            Returns:
                 封装工具执行结果的ToolMessage
            Raises:
                KeyError: 工具未注册时给出
                RuntimeError: 工具调用失败时给出
            """
            try:
                # 异步工具调用
                # tools_name 为 {tool.name: tool} 的 dict
                tool = self.tools_name.get(tool_call["name"])
                if not tool:
                    raise KeyError(f'工具{tool_call["name"]}未注册')

                if hasattr(tool, "ainvoke"):
                    tool_result = await tool.ainvoke(tool_call["args"])

                else:
                    # 如果同步调用，则丢到线程池里跑，避免阻塞主事件循环。
                    loop = asyncio.get_running_loop()
                    tool_result = await loop.run_in_executor(
                        None, # 默认线程池
                        tool.invoke, # 执行同步调用
                        tool_call['args'] # 输入工具调用参数
                    )
                if isinstance(tool_result, (dict, list)):
                    content = json.dumps(tool_result, ensure_ascii=False)
                elif isinstance(tool_result, str):
                    content = tool_result
                else:
                    content = str(tool_result)
                return ToolMessage(content=content,
                                   name=tool_call["name"],
                                   tool_call_id=tool_call['id'])
            except Exception as e:
                raise  RuntimeError(f"工具{tool_call['name']}调用失败") from e

        try:
            # 使大模型能够并行调用工具
            return await asyncio.gather(*[_invoke_tool(tool_call) for tool_call in tool_calls])
        except Exception as e:
            print(e)
            raise RuntimeError('并发工具时发生错误') from e


class State(MessagesState):
    pass





def route_tool_function(state: State) -> str:
    """
    动态路由函数，如果大模型输出后的AIMessges中有工具调用的请求，就进入tool节点执行工具调用
    """
    print(state)
    if isinstance(state, list):
        ai_message = state[-1]
    elif isinstance(state, dict) and (messages := state.get("messages", [])):
        ai_message = messages[-1]
    elif messages := getattr(state, "messages", []):
        ai_message = messages[-1]
    else:
        raise ValueError("no message found in State")

    if hasattr(ai_message, 'tool_calls') and len(ai_message.tool_calls) >0:
        return 'tools'

    return END



async def create_graph():
    tools = await mcp_lient.get_tools()

    builder = StateGraph(State)

    llm_with_tools = llm.bind_tools(tools)

    async def chatbot(state: State):
        messages = {'messages': [await llm_with_tools.ainvoke(state['messages'])]}
        print(state)
        return messages

    builder.add_node('chatbot', chatbot)

    tool_node = BasicToolsNode(tools=tools)

    builder.add_node('tools', tool_node)

    builder.add_conditional_edges(source='chatbot', path=route_tool_function, path_map={'tool':'tools', END:END})
    builder.add_edge(START, 'chatbot')
    builder.add_edge('tools', 'chatbot')

    graph = builder.compile()

    return graph

graph = asyncio.run(create_graph())
