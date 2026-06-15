from get_env import ZHIPU_API_KEY, GEMINI_API_KEY
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

llm = ChatOpenAI(
    temperature=0.1,
    model="glm-4.5-flash",
    api_key=ZHIPU_API_KEY,
    base_url="https://open.bigmodel.cn/api/paas/v4/"
)


base_url = "http://127.0.0.1:6006/v1/"
llm = ChatOpenAI(
    temperature=0.1,
    model="Qwen3-8B",
    api_key='KEY',
    base_url=base_url
)

