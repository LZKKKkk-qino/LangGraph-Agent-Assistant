import asyncio
import json
import uuid
from typing import Dict, Any, List
from langchain_core.messages import ToolMessage, AIMessage, HumanMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.memory import MemorySaver
from langgraph.constants import END, START
from langgraph.graph import StateGraph, MessagesState
from langgraph.types import interrupt, Command

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

        message: AIMessage = messages[-1] # 状态中的ai回复的最新消息

        tool_name = message.tool_calls[0]['name'] if message.tool_calls else None
        if tool_name == 'webSearchStd' or tool_name == 'webSearchSogou':
            # res为一个dict
            res = interrupt(value=f'模型尝试调用工具:{tool_name},请选择是否调用，调用则回复“y”')

            if res['answer'].strip().lower() == 'y':
                pass
            else:
                return {'messages':[ToolMessage(
                                    content=f"中断工具调用，理由为：{res['answer']}",
                                    name=tool_name,
                                    tool_call_id=message.tool_calls[0]['id']
                                               )
                ]}



        output = await self._execute_tool_calls(message.tool_calls)  # 得到模型调用工具后工具执行结果的 ToolMessage
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
        # state中新加入的message与之前对话的message一起传给LLM, 进而生成一条新的模型回复AIMessage
        messages = {'messages': [await llm_with_tools.ainvoke(state['messages'])]}
        print(state)
        return messages

    builder.add_node('chatbot', chatbot)

    tool_node = BasicToolsNode(tools=tools)

    builder.add_node('tools', tool_node)

    builder.add_conditional_edges(source='chatbot', path=route_tool_function, path_map={'tools':'tools', END:END})
    builder.add_edge(START, 'chatbot')
    builder.add_edge('tools', 'chatbot')

    memory = MemorySaver()
    graph = builder.compile(checkpointer=memory)

    return graph

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


    async def execute_graph(user_input: str) -> str:   # 结果是AIMessage中的content内容，或者是interrupt()中的value显示值

        result = ''

        # 等待用户中断输入内容
        # 不进行工具调用，可能继续提问或者给出拒绝理由
        current_state = graph.get_state(config=config)
        if current_state.next: # 有下一步,表示当前工作流处在中断状态, 没有进入 END 节点

            human_command = Command(resume={'answer': user_input})  # 在中断点之后继续运行，输入进 interrupt 函数中，得到上面的 res

            # 1. 若 Command 中的 answer 为 y，则进行工具调用
            # 接着执行工作流，返回工具结果给LLM，完成全部工具调用且不再调用工具后，得到模型想给用户的最终输出 result ,就是这次用户提问模型通过调用工具后得到的最终结果
            # 2. 若 Command 中的 answer 不为 y， 则工具节点返回我们设定好的 'messages' 作为 result 输出给 LLM，进而使LLM生成后直接进入 END 节点
            async for chunk in graph.astream(human_command, config, stream_mode='values'):
                result = print_messages(chunk, result)           # 将用户决定发送给模型,得到模型回复
            return result

        else: # 正常输入 human message
            async for chunk in graph.astream(
                    {'messages': [HumanMessage(content=user_input)]}, config, stream_mode='values'):
                result = print_messages(chunk, result)


        # 刚发出工具调用请求，询问用户是否调用工具，返回设定好的返回值
        current_state = graph.get_state(config=config)

        # 有 state.next ,表示当前工作流处在节点 node 是中断状态, 且没有进入 END 节点
        # 当工作流已经到达终点（END），或者不需要等待外部输入时，state.next 为 False。
        if current_state.next:
           result = current_state.interrupts[0].value

        return result

    while True:
        user_input = input('用户: ')
        res = await execute_graph(user_input)
        print("Assistant:", res)

if __name__ == '__main__':
    asyncio.run(run_graph())
