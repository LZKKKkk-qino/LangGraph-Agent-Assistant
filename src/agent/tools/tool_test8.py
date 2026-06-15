from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool




# tools
@tool(name_or_callable='get_user_info_by_name')
def get_user_info(config: RunnableConfig,) -> dict:
    """
    通过用户名来获取该用户的所有信息，包括但不限于性别、年龄、身高、住址

    Args：
        config: 输入的用户config字典，里面有“user_name”的 key


    """

    user_name = config['configurable'].get('user_name', 'anonymous')

    print(f"调用tool: 当前对话用户名为 {user_name}")

    return {"user_name": user_name, 'sex': 'man', 'age': 25}


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
