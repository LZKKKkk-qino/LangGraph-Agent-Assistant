import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.constants import END, START
from langgraph.graph import StateGraph, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from get_env import ZHIPU_API_KEY
from src.agent.my_llm import llm

# 配置 mcp

# 本地 tool
local_tool_studio_config = {
            "command": "python",
            # Replace with absolute path to your math_server.py file
            "args": ["absolute path of server.py"],
            "transport": "stdio",
        }

# 本地 mcp
local_mcp_config = {
    # streamable
    'url': 'http://127.7.7.1:7777/streamable',
    "transport": "streamable_http",

    # sse
    # 'url': 'http://127.7.7.1:7777/sse',
    # "transport": "sse",

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
        # "search_mcp_server_config" : search_mcp_server_config,
        # "fetch_mcp_server_config" : fetch_mcp_server_config,
        # "get12306_mcp_server_config" : get12306_mcp_server_config,
        # "chart_mcp_server_config" : chart_mcp_server_config,
        # "local_mcp_config" : local_mcp_config,
        "local_tool_studio_config" : local_tool_studio_config,
    }
)

class State(MessagesState):
    pass

async def create_graph():
    tools = await mcp_lient.get_tools()

    builder = StateGraph(State)

    llm_with_tools = llm.bind_tools(tools)

    async def chatbot(state: State):
        messages = {'messages': [await llm_with_tools.ainvoke(state['messages'])]}
        print(state)
        return messages

    builder.add_node("agent", chatbot)

    tool_node = ToolNode(tools=tools)
    builder.add_node('tools', tool_node)

    builder.add_conditional_edges(source="agent", path=tools_condition, path_map={'tools':'tools', END:END})
    builder.add_edge(START, "agent")
    builder.add_edge('tools', "agent")

    graph = builder.compile()

    return graph

graph = asyncio.run(create_graph())
