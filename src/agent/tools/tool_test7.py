from typing import Any, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from zai import ZhipuAiClient
from get_env import ZHIPU_API_KEY


client = ZhipuAiClient(api_key=ZHIPU_API_KEY)



class SearchArgs(BaseModel):  # 构建工具要输入的参数类，添加描述
   query: str= Field(description="用户搜索提问")


class SearchTool(BaseTool):
    name: str = 'zhipu_search_tool'

    description: str = "联网搜索内容的工具"

    args_schema: Type[BaseModel] = SearchArgs

    def _run(self, query) -> str:
        try:
            response = client.web_search.web_search(
                search_engine="search_pro",
                search_query= query,
                content_size="high" ,   # 控制网页摘要的字数，默认medium

            )
            # print(response)
            # print(response.search_result)
            # print(type(response.search_result))           # 整个列表类型
            # print(type(response.search_result[0]))      # 第一个元素类型

            if response.search_result:
                return "\n\n".join([d.content for d in response.search_result])
            return 'no content'
        except Exception as e:
            print(e)
            return 'no content'

search_tool = SearchTool()


# print(search_tool.name)
# # print("*"*77)
# # print(search_tool.description)
# # print("*"*77)
# # print(search_tool.args) # 参数中没有description
# # print("*"*77)
# # print(search_tool.args_schema.model_json_schema())
# # print("*"*77)
# # print(search_tool)
# result = search_tool._run(query='请问donk和monesy谁强')
# print(result)
