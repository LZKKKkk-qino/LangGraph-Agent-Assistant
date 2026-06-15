from pydantic import BaseModel, Field
from langchain_core.tools import tool, StructuredTool
from typing import Annotated


# 使用 StructuredTool 构建工具函数，可传入参数，使工具同时能接受同步或异步的调用

# functions

def calculate(a:float,
              b:float,
              operation:str) -> float:
    """
    计算器，得到运算结果

    Args：
        a: 第一个输入的数字
        b: 第二个输入的数字
        operation: 运算类型，只能是‘add’,subtract,multiply,divide中的一种。

    Returns:
        返回输入数字的运算结果
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

async def calculate_async(a:float,
                    b:float,
                    operation:str) -> float:
    """
    计算器，得到运算结果

    Args：
        a: 第一个输入的数字
        b: 第二个输入的数字
        operation: 运算类型，只能是‘add’,subtract,multiply,divide中的一种。

    Returns:
        返回输入数字的运算结果
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

# 创建工具
calculator = StructuredTool.from_function(
    func=calculate,
    name='calculator',
    coroutine=calculate_async,
    description= """
    计算器，得到运算结果

    Args：
        a: 第一个输入的数字
        b: 第二个输入的数字
        operation: 运算类型，只能是‘add’,subtract,multiply,divide中的一种。

    Returns:
        返回输入数字的运算结果
    """,

)

print(calculator.name)
print("*"*77)
print(calculator.description)
print("*"*77)
print(calculator.args)  # 参数中没有description， 函数的description中有参数的注释
print("*"*77)
print(calculator.args_schema.model_json_schema())
print("*"*77)
print(calculator)
