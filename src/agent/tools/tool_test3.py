from pydantic import BaseModel, Field
from langchain_core.tools import tool
from typing import Annotated

# 直接在函数参数中加入注释

# tools
@tool(name_or_callable='calculator')
def calculate(a:Annotated[float, "第一个输入的数字"],
              b:Annotated[float, '第二个输入的数字'],
              operation:Annotated[str, "运算类型，只能是add,subtract,multiply,divide中的一种"]) -> float:
    """
    计算器，得到运算结果
    """
    result = 0.0
    match operation:
        case "add":
            result = a+b
        case "subtract":
            result = a-b
        case "multiply":
            result = a*b
        case "divide":
            if b != 0:
                result = a/b
            else:
                raise ValueError("Error: divide 0")

    return result

#
# print(calculate.name)
# print("*"*77)
# print(calculate.description)
# print("*"*77)
# print(calculate.args) # 参数中有description
# print("*"*77)
# print(calculate.args_schema.model_json_schema())
# print("*"*77)
# print(calculate)
