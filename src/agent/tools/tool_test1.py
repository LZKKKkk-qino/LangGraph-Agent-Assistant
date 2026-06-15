from langchain_core.tools import tool

# 直接通过函数构建工具，无具体细节注释

# tools
@tool()
def calculate(a:float, b:float, operation:str) -> float:
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

print(calculate.name)
print("*"*77)
print(calculate.description)
print("*"*77)
print(calculate.args) # 参数中没有description
print("*"*77)
print(calculate.args_schema.model_json_schema())
print("*"*77)
print(calculate)