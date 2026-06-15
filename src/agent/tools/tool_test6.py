from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import SystemMessagePromptTemplate, MessagesPlaceholder, ChatPromptTemplate, \
    HumanMessagePromptTemplate
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from get_env import ZHIPU_API_KEY

# 使用 Runnable对象转化

llm = ChatOpenAI(
    temperature=0.1,
    model="glm-4.5-flash",
    api_key=ZHIPU_API_KEY,
    base_url="https://open.bigmodel.cn/api/paas/v4/"
)


human_template = """
请你基于用户输入的故事描述，生成故事标题{title},人物{character},故事摘要{summary},并进而帮我生成一段温馨的故事。
"""

human_message = HumanMessagePromptTemplate.from_template(human_template)
# input_message = MessagesPlaceholder(variable_name="messages")

# 构建聊天 prompt
prompt = ChatPromptTemplate.from_messages([human_message,
                                           # input_message
                                           ])

chain = prompt | llm | StrOutputParser()


class story_generate(BaseModel):  # 构建工具要输入的参数类，添加描述
    title: str= Field(description="生成的用户描述故事标题")
    character: str= Field(description="生成的用户描述故事人物形象")
    summary: str= Field(description="生成的用户描述故事概括")



runnable_tool = chain.as_tool(
    name="story_generator",
    description="可以通过用户的描述，帮我生成一个故事",
    args_schema=story_generate
)

# print(runnable_tool.name)
# print("*"*77)
# print(runnable_tool.description)
# print("*"*77)
# print(runnable_tool.args) # 参数中没有description
# print("*"*77)
# print(runnable_tool.args_schema.model_json_schema())
# print("*"*77)
# print(runnable_tool)
