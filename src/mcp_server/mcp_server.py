from fastmcp import FastMCP
from fastmcp.server.auth.providers.jwt import RSAKeyPair
from fastmcp.server.dependencies import get_access_token
from mcp.types import TextContent, PromptMessage
from fastmcp.server.auth import JWTVerifier, AccessToken
# from src.agent.tools.tool_test7 import search_tool
from src.agent.tools.tool_test8 import get_user_info



# 若想开发 Java 的 mcp server, 需要用 spring 的 java 框架进行开发


# 认证机制

# # 1. 生成 RSA 密钥对(公钥、私钥）
# key_pair = RSAKeyPair.generate()
#
# # 2. 配置认证提供方
# auth = JWTVerifier(
#     public_key=key_pair.public_key,
#     issuer='http://127.0.0.1:7777',
#     audience='my_mcp_server_with_auth',
#     required_scopes=['QIYE','XIAOHONG'] # # scopes 所需的最小权限
# )
#
# # 模拟生成一个 TOKEN
# token = key_pair.create_token(
#     subject='default_user',
#     issuer='http://127.0.0.1:7777',
#     audience='my_mcp_server_with_auth',
#     scopes=['QIYE','XIAOHONG','NONO', 'LIUZHENG'],  # scopes 权限范围，后续将服务端内容进行划分给不同权限
#     expires_in_seconds=3600  # 接口有效时间
# )
#
# print(f'Test token:{token}')

# 部署 mcp 服务端
my_mcp = FastMCP(name='Qi的mcp',
                 # auth=auth
                 )



# 定义 mcp 的工具 tool
@my_mcp.tool()
def say_hello(user_name: str) -> str:
    """
    根据用户名称去给用户打招呼
    """

    # access_token: AccessToken = get_access_token()
    # if access_token:
    #     print(f"TOKEN 为：{access_token}")
    # else:
    #     ValueError('access error')

    return f"hello,{user_name}."

@my_mcp.tool()
def get_user_info(user_name: str) -> str:
    """
    根据用户名称去获取用户信息
    """
    return get_user_info(user_name)



# 内置提示词模板

@my_mcp.prompt()
def ask_about_topic(topic: str) -> str:
    """
    生成请求解释特定主题的用户消息模板
    """
    return f"请您描述一下{topic}的含义"

@my_mcp.prompt()
def generate_code_prompt(language: str, task_description: str) -> PromptMessage:
    """
    生成用户要求代码的编写请求模板
    """
    content = f"请用该计算机语言：{language}, 来编写一个实现以下功能的函数： {task_description}"

    return PromptMessage(role='user', content=TextContent(type='text', text=content))


# 结构化资源

@my_mcp.resource("resource://my-resource")
def hello_world() -> str:
    return "Hello, world!"

@my_mcp.resource("resource://config")
def get_config() -> dict:
    return {
        "theme": "dark",
        "version": "1.2.0",
        "features": ["tools", "prompts", "resources"],
    }
