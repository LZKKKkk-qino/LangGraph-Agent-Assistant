from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Literal

# 定义 ChoiceDeltaToolCallFunction 类
class ChoiceDeltaToolCallFunction(BaseModel):
    name: Optional[str] = None
    arguments: Optional[str] = None

# 定义 FunctionCall 类
class FunctionCall(BaseModel):
    name: str
    arguments: Dict[str, str]


# 定义 ChatCompletionMessageToolCall 类
class ChatCompletionMessageToolCall(BaseModel):
    index: Optional[int] = 0
    id: Optional[str] = None
    function: FunctionCall
    type: Optional[Literal["function"]] = 'function'

# 定义 DeltaMessage 类
class DeltaMessage(BaseModel):
    role: Optional[Literal["user", "assistant", "system"]] = None
    content: Optional[str] = None
    function_call: Optional[ChoiceDeltaToolCallFunction] = None
    tool_calls: Optional[List[ChatCompletionMessageToolCall]] = None

# 创建一个 ChoiceDeltaToolCallFunction 实例
function_call = ChoiceDeltaToolCallFunction(
    name="get_weather",
    arguments='{"city": "New York"}'
)

# 创建一个 FunctionCall 实例
function_call_detail = FunctionCall(
    name="get_weather",
    arguments={"city": "New York"}
)

# 创建一个 ChatCompletionMessageToolCall 实例
tool_call = ChatCompletionMessageToolCall(
    index=1,
    id="call-123",
    function=function_call_detail
)

# 创建一个 DeltaMessage 实例
delta_message = DeltaMessage(
    role="assistant",
    content="Here is the weather report.",
    function_call=function_call,
    tool_calls=[tool_call]
)

# 打印 DeltaMessage 的信息
print(delta_message.model_dump_json(indent=2))