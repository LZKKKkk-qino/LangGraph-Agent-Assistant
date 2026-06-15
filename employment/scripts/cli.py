from openai import OpenAI


base_url = "http://127.0.0.1:6006/v1/"
client = OpenAI(api_key="EMPTY", base_url=base_url)

messages = [
    {"role": "system","content": "你是一个乐于助人的ai助手，请回答我的问题。"},
    { "role": "user","content": "请问大模型是什么呢？"}
]
response = client.chat.completions.create(
    model="Qwen2.5-0.5B-Instruct",
    messages=messages,
    # stream=True,
    max_tokens=256,
    temperature=0.4,
    presence_penalty=1.2,
    top_p=0.8,
)

# 流试的输出
# for s in response:
#     print(s.choices[0].delta.content)
print(response.choices[0].message)