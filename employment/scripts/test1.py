import asyncio

async def predict_stream(model, params, i):
    # 假设这是一个简单的示例，实际实现可能更复杂
        yield {"text": f"Prediction {i + 1}"}
        yield "none"


# 使用 async for 迭代生成器
async def main(i=None):
    # 假设 request.model 和 gen_params 已经定义
    predict_stream_generator = predict_stream('request.model', 'gen_params', i= i)
    async for output in predict_stream_generator:
        print(output)  # 输出: {'text': 'Prediction i'}


# 运行主异步函数
for i in range(5):
    print(i)
    asyncio.run(main(i))
