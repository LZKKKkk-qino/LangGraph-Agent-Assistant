from typing import Annotated

from langchain_core.messages import ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool, InjectedToolCallId
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from src.agent.state_test import CustomState

# tools
@tool(name_or_callable='get_user_name')
def get_user_name(config: RunnableConfig,
                  tool_call_id: Annotated[str, InjectedToolCallId]) -> Command:
    """
    获取对话的用户名，并更新 Command 中 state 存储的消息
    """

    user_name = config['configurable'].get('user_name', 'anonymous')

    print(f"调用tool: 当前对话用户名为 {user_name}")

    return Command(update={"user_name": user_name,
                           "messages": ToolMessage(content='得到了当前用户名字',
                                                   tool_call_id=tool_call_id),
                           }
                   )

def greet_user(state: Annotated[CustomState, InjectedState]) -> str:
    """
    给用户一个祝福语
    """
    user_name = state['user_name']

    return f'祝您好运：{user_name}'


#
# print(calculate.name)
# print("*"*77)
# print(calculate.description)
# print("*"*77)
# print(calculate.args) # 参数中没有description， 函数的description中有参数的注释
# print("*"*77)
# print(calculate.args_schema.model_json_schema())
# print("*"*77)
# print(calculate)
