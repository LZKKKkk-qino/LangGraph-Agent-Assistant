import asyncio
import uuid

from langchain_core.messages import ToolMessage, AIMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.memory import MemorySaver
from langgraph.constants import END, START
from langgraph.graph import StateGraph, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
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
        # "fetch_mcp_server_config" : fetch_mcp_server_config,
        "get12306_mcp_server_config" : get12306_mcp_server_config,
        "chart_mcp_server_config" : chart_mcp_server_config,
        # "local_mcp_config" : local_mcp_config,
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

    builder.add_node('chatbot', chatbot)

    tool_node = ToolNode(tools=tools)
    builder.add_node('tools', tool_node)

    builder.add_conditional_edges(source='chatbot', path=tools_condition, path_map={'tools':'tools', END:END})
    builder.add_edge(START, 'chatbot')
    builder.add_edge('tools', 'chatbot')

    memory = MemorySaver()
    graph = builder.compile(interrupt_before=['tools'], checkpointer=memory)

    return graph

# 创建 graph 实例，可在 langgraph dev 中启动
# graph = asyncio.run(create_graph())

async def run_graph():
    graph = await create_graph()
    config = {"configurable":
                  {"thread_id": str(uuid.uuid4())}
              }

    def print_messages(state, result):
        messages = state.get('messages')
        if messages:
            if isinstance(messages, list):
                message = messages[-1]  # 如果是消息列表，取最后一个消息
                if message.__class__.__name__ == 'AIMessage':
                    if message.content:
                        result = message.content  # 需要展示的消息
                msg_represent = message.pretty_repr(html=True)
                if len(msg_represent) > 1500:
                    msg_represent = msg_represent[:1500] + '...Truncation'
                    print(msg_represent)
        return result

    def get_update_answer(tool_message, user_answer):
        tool_name = tool_message.tool_calls[0]['name']
        answer = f'强制终止了工具：{tool_name},拒绝理由为:{user_answer}'

        new_message = [ToolMessage(content=answer,
                                   tool_call_id=tool_message.tool_calls[0]['tool_call_id'],
                                   id=tool_message.tool_calls[0]['id']
                                   ),
                       AIMessage(content=answer)] # 模拟 LLM 在看到ToolMessage后，给出ai回复消息

        graph.update_state(
            config=config,
            values={'messages': new_message}
        )

    async def execute_graph(user_input: str):

        result = ''

        if user_input.strip().lower() != 'y': # 不进行工具调用，可能继续提问或者给出拒绝理由
            current_state = graph.get_state(config=config)
            if current_state.next: # 有下一步,表示当前工作流处在中断状态, 没有进入 END 节点
                tools_script_message = current_state.values['messages'][-1]
                get_update_answer(tools_script_message, user_input)
                message = graph.get_state(config).values['messages'][-1]
                result = message.content
                return result

            else: # 正常输入 human message
                async for chunk in graph.astream(
                        {'messages': ('user', user_input)}, config, stream_mode='values'):
                    result = print_messages(chunk, result)

        else:  # 用户输入了'y',想继续调用工具
            async for chunk in graph.astream(None, config, stream_mode='values'): # 传入None继续执行工具
                result = print_messages(chunk, result)

        # 刚进行工具调用请求
        current_state = graph.get_state(config=config)
        if current_state.next: # 有下一步,表示当前工作流处在中断状态, 没有进入 END 节点
            ai_message = current_state.values['messages'][-1]
            tool_name = ai_message.tool_calls[0]['name']
            result = f'模型决定执行{tool_name}工具，是否继续？输入y进入工具调用.'

        return result

    while True:
        user_input = input('用户: ')
        res = await  execute_graph(user_input)
        print("Assistant:", res)



if __name__ == '__main__':
    asyncio.run(run_graph())


