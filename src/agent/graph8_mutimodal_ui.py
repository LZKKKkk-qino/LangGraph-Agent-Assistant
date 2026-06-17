import asyncio
import json
import os
import uuid
import base64
from typing import Dict, Any, List
from langchain_core.messages import ToolMessage, AIMessage, HumanMessage, SystemMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.constants import END, START
from langgraph.graph import StateGraph, MessagesState
from langgraph.types import interrupt, Command
import gradio as gr
from get_env import ZHIPU_API_KEY
from src.agent.my_llm import multimodal_llm
from src.agent.tools.tool_test4 import calculate
from src.agent.tools.tool_test6 import runnable_tool
import time

# 配置 mcp

# 本地 tool mcp
local_tool_studio_config = {
            "command": "python",
            # Replace with absolute path to your math_server.py file
            "args": ["absolute path of server.py"],
            "transport": "stdio",
        }

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
            else:  # 不执行工具，包装一个ToolMessage作为tool node的返回值
                return {'messages':[ToolMessage(
                                    content=f"拒绝工具调用，理由为：{res['answer']}",
                                    name=tool_name,
                                    tool_call_id=message.tool_calls[0]['id']
                                               )
                ]}



        output = await self._execute_tool_calls(message.tool_calls)  # 得到模型调用工具的 ToolMessage, 回传给大模型
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
    print(f"graph state:{state}")
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
    # tools.extend([calculate, runnable_tool])
    print(tools)
    builder = StateGraph(State)

    llm_with_tools = multimodal_llm.bind_tools(tools)

    async def chatbot(state: State):
        # state中新加入的message与之前对话的message一起传给LLM, 进而生成一条新的模型回复AIMessage
        messages = {'messages': [await llm_with_tools.ainvoke(state['messages'])]}

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


graph = asyncio.run(create_graph())

config = {"configurable":
              {"thread_id": str(uuid.uuid4())}
          }



def get_messages(state, content=''):
    messages = state.get('messages')
    if messages:
        if isinstance(messages, list):
            message = messages[-1]  # 如果是消息列表，取最后一个消息
            if message.__class__.__name__ == 'AIMessage':
                if message.content:
                    content = message.content  # 需要展示的消息

    return content


# 记录聊天框聊天消息
# def add_message(chat_history, user_message):
#     if user_message:
#         chat_history.append({"role": "user", "content":user_message})
#     return chat_history, gr.Textbox(value=None, interactive=False)

def add_message(chat_history, user_messages):
        print("DEBUG user_messages: ", user_messages)

        # 记录上传文件路径
        for msg in user_messages['files']:
            print(msg)
            chat_history.append({ "role": "user", "content":{'path':msg}} )

        # 处理文本消息
        if user_messages['text'] is not None and user_messages['text'].strip():
            chat_history.append({"role": "user", "content":user_messages['text']})
        return chat_history, gr.Textbox(value=None, interactive=False)  # 提交后返回重置的输入框

def set_prompt(chat_history, prompt_text):
    gr.Info(f"✅ 系统提示词已设置")
    # chat_history.append({"role": "system", "content": prompt_text},
    #                      # {"role": "assistant", "content": '成功设置系统提示词'}
    #                      )
    # print(chat_history)
    return chat_history

def get_all_latest_user_message(chat_history):
    """
    用户可能同时输入文本和各种文件，因此需要将用户的所有输入合并，后续一起输入模型
    反向遍历找到最后一个 ai assistant 的位置，然后取其后面一次的 user 输入
    """

    if not chat_history:
        return None
    if chat_history[-1]['role'] == 'assistant':
        return None

    last_assistant_idx = -1
    for i in range(len(chat_history)-1, -1, -1): # (start, end, step)
        if chat_history[i]['role'] == 'assistant':
            last_assistant_idx= i
            break

    if last_assistant_idx == -1: # 此时对话刚开始，第一条就是用户的输入，所以返回全部的 chat_history
        return chat_history
    else:
        return chat_history[last_assistant_idx+1:]

# 文件处理函数
def transcribe_audio(audio_path):
    """使用 Base64 处理音频文件"""
    try:
        with open(audio_path, 'rb') as audio_file:
            audio_base = base64.b64encode(audio_file.read()).decode('utf-8')
        audio_message = {
            'type': 'audio_url',
            'audio_url': {
            'url': f"data:audio/wav;base64,{audio_base}",  # wav 可换为 mp3
            'duration': 30,
                         }
        }
        return audio_message
    except Exception as e:
        print(e)
        return {}

def transcribe_image(img_path):
    with open(img_path, 'rb') as img_file:
        img_data = base64.b64encode(img_file.read()).decode('utf-8')
    img_message ={
        "type": "image_url",
        "image_url": {
            "url": img_data,
            "detail": 'low'
        }
    }
    return  img_message

def transcribe_video(video_path):

    video_message ={
        "type": "video_url",
        "video_url": {
            "url": video_path,

        }
    }
    return  video_message

def read_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            text_content = f.read()
            file_message = {"type": "text", "text": f"[文件内容]\n{text_content}"}
    except Exception:
        file_message = {"type": "text", "text": f"[文件] {os.path.basename(file_path)}"}
    return file_message




async def submit_messages(chat_history: list[dict], user_prompt: list[dict]) :  # 结果是新增AIMessage中content内容，或者是interrupt()中的value显示值的chat_history

    content=''
    # user_input = chat_history[-1]['content'] if chat_history else ''
    user_messages = get_all_latest_user_message(chat_history)

    # 如果用户提交的内容是空的，则不做改动
    if not user_messages:
        return chat_history

    user_input = []
    if user_messages:
        for msg in user_messages:
            for item in msg['content']:
                item_type = item.get('type')

                if item_type == 'text':
                    user_input.append({'type': 'text', 'text': item['text']})

                elif item_type == 'file':
                    file_path = item['file']['path']

                    # 音频文件转换为用户消息
                    if file_path.lower().endswith(('.mp3', '.wav', '.m4a')):
                        file_message = transcribe_audio(file_path)
                        user_input.append(file_message)

                    # 图片文件转换为用户消息
                    elif file_path.lower().endswith(('.png', '.jpeg', '.jpg', '.webp')):
                        file_message = transcribe_image(file_path)
                        user_input.append(file_message)

                    # 视频文件转换为用户消息
                    elif file_path.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
                        file_message = transcribe_video(file_path)
                        user_input.append(file_message)

                    else:
                        file_message = read_file(file_path)
                        user_input.append(file_message)

                else:
                    pass


    # 等待用户中断输入内容
    # 不进行工具调用，可能继续提问或者给出拒绝理由
    current_state = graph.get_state(config=config)
    if current_state.next: # 有下一步,表示当前于工具节点处于中断状态, 没有进入 END 节点

        human_command = Command(resume={'answer': user_input[0]['text']})  # 在中断点之后继续运行，输入进 interrupt 函数中，得到上面的 res

        # 1. 若 Command 中的 answer 为 y，则进行工具调用
        # 接着执行工作流，返回工具结果给LLM，完成全部工具调用且不再调用工具后，得到模型想给用户的最终输出 result ,就是这次用户提问模型通过调用工具后得到的最终结果
        # 2. 若 Command 中的 answer 不为 y， 则工具节点返回我们设定好的 'messages' 作为 result 输出给 LLM，进而使LLM生成后直接进入 END 节点
        async for chunk in graph.astream(human_command, config, stream_mode='values'):
            content = get_messages(chunk, content)           # 将用户决定发送给模型,得到模型回复
            chat_history.append(gr.ChatMessage(role="assistant", content=content))
        return chat_history

    else: # 正常输入 human message
        messages = []
        if user_prompt:
             messages.append(SystemMessage(content=user_prompt))
        messages.append(HumanMessage(content=user_input))
        print(f"提交给大模型的输入：{messages}")
        async for chunk in graph.astream(
                {'messages': messages}, config, stream_mode='values'):
            content = get_messages(chunk, content)

    # 检查中断点，在正常输入后第一次遇到中断点
    current_state = graph.get_state(config=config)

    # 有 state.next ,表示当前工作流处在节点 node 是中断状态, 且没有进入 END 节点
    # 当工作流已经到达终点（END），或者不需要等待外部输入时，state.next 为 False。
    if current_state.next:
        content = current_state.interrupts[0].value  # 返回中断点中value参数设定好的内容

    chat_history.append(gr.ChatMessage(role="assistant", content=content))
    return chat_history


# 创建 Gradio 界面
with gr.Blocks(title="my assistant", theme=gr.themes.Soft()) as demo:

    # 聊天历史记录框组件
    chatbot = gr.Chatbot(height=500, render_markdown=True, line_breaks=False, layout='bubble',buttons=["share", "copy", "copy_all"])

    # 创建一个行布局
    with gr.Row(equal_height=True):  #):  # 水平布局容器

        # 创建一个列布局
        with gr.Column(scale=3):  # 垂直布局容器
            # 创建一个文本框用于用户输入
            with gr.Column(scale=12):
                chat_input = gr.MultimodalTextbox(
                    interactive=True,
                    file_count='multiple',
                    file_types=['image','video','audio','text'],
                    placeholder='你好！有什么可以帮助您',
                    show_label=False,
                    sources=['microphone', 'upload'],
                    lines=12
                )
                # chat_input = gr.Textbox(show_label=False, placeholder="你好！有什么可以帮助您", lines=12, container=False, submit_btn=True, stop_btn=True)
            # 创建一个提交按钮
            with gr.Column(min_width=32, scale=2):
                submit_buttton = gr.Button(value="发送", variant="primary")  # 提交用户问题的 按钮

        # 创建另一个列布局
        with gr.Column(scale=1):
            # 创建一个文本框用于输入提示词
            prompt_input = gr.Textbox(show_label=False, placeholder="提示词", lines=15, container=True)
            # 创建一个按钮用于设置提示词
            pBtn = gr.Button("系统提示词设置")

        # 创建第三个列布局
        with gr.Column(scale=1):
            # 创建一个滑块用于设置最大长度
            max_length = gr.Slider(0, 32768, value=1024, step=1.0, label="最大长度", interactive=True)
            # 创建一个滑块用于设置Top P值
            top_p = gr.Slider(0, 1, value=0.8, step=0.01, label="Top P", interactive=True)
            # 创建一个滑块用于设置温度
            temperature = gr.Slider(0.01, 1, value=0.6, step=0.01, label="Temperature", interactive=True)
            # 创建一个按钮用于清除聊天记录
            clear_button = gr.Button("clear")

    # 消息提交处理链
    msg_handler = chat_input.submit(fn=add_message,
                                    inputs=[chatbot, chat_input],
                                    outputs=[chatbot, chat_input],
                                    queue=False
                                    ).then(fn=submit_messages,
                                           inputs=[chatbot, prompt_input],
                                           outputs=chatbot,
                                           api_name="chat_stream"
                                           )

    # 按钮处理链
    button_handler = submit_buttton.click(fn=add_message,
                                          inputs=[chatbot, chat_input],
                                          outputs=[chatbot, chat_input],
                                          queue=False
                                          ).then(fn=submit_messages,
                                                 inputs=[chatbot, prompt_input],
                                                 # inputs=[chatbot, prompt_input, max_length, top_p, temperature],
                                                 outputs=chatbot
                                                 )
    # 对话清空处理
    clear_button.click(fn=lambda :[], inputs=None, outputs=chatbot, queue=False)

    # 将设置提示词的函数绑定到按钮点击事件
    pBtn.click(set_prompt, inputs=[chatbot,prompt_input], outputs=chatbot)

    # 重置输入框状态
    msg_handler.then(fn=lambda : gr.Textbox(interactive=True), inputs=None, outputs=[chat_input])
    button_handler.then(fn=lambda : gr.Textbox(interactive=True), inputs=None, outputs=[chat_input])


if __name__ == '__main__':
    # To create a public link, set `share = True` in `launch()`.
    demo.launch()

