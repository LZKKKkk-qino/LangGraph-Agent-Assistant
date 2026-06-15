from typing import TypedDict, Literal

from langgraph.constants import START, END
from langgraph.graph import StateGraph
from pydantic import BaseModel, Field

from src.agent.my_llm import llm


class State(TypedDict):
    joke: str
    topic: str
    feedback: str
    funny_or_not: str

class Feedback(BaseModel):
    """结构化模型响应的输出数据"""
    grade: Literal["funny", "not_funny"] = Field(description='判断笑话是否足够幽默',
                                                 examples=["funny", "not_funny"]
                                                )
    feedback: str = Field(description='若不够幽默，则输出改进建议',
                          examples=['可以加入意想不到的情况']
                          )

# 构建一个workflow
builder = StateGraph(State)  # type: ignore

# 节点函数
def generator(state: State, ):
    """使用大模型生成笑话"""
    prompt = (f'根据反馈改进笑话内容：{state['feedback']}\n主题：{state['topic']}'
              if state.get('feedback', None)
              else f'请你帮我写一个关于{state['topic']}的笑话'
              )
    res = llm.invoke(prompt)
    print("*"*125)
    print(state)
    return {'joke': res.content}

def evaluator(state: State,):

    # 如果 LLM 支持 with_structured_output() 函数
    # chain = llm.with_structured_output(Feedback)
    # res = chain.invoke(input=f"""评估此笑话的幽默程度: \n{state['joke']}
    #                     注意: 幽默应包含意外性或巧妙措辞(暗喻)
    #                     """)
    # return {
    #     'feedback': res.feedback,
    #     'funny_or_not': res.grade
    #        }

    # zhipu不支持
    # 如果 LLM 不支持 with_structured_output() 函数
    # 使用 bind_tool 函数将输出的结构化参数绑定到模型中去
    chain = llm.bind_tools([Feedback])
    res = chain.invoke(f"""评估此笑话的幽默程度: \n{state['joke']}\
                         注意: 幽默应包含意外性或巧妙措辞(暗喻)
                         """ )
    print("*"*125)
    print(state)
    evaluation = res.tool_calls[-1]['args']
    return {
        'feedback': evaluation['feedback'],
        'funny_or_not': evaluation['grade']
           }

#
def routing_function(state: State,):
    """动态路由决策下一个节点"""
    return (
        'Accepted' if state.get('funny_or_not', None) == 'funny' else 'Rejected'
    )


builder.add_node('generator', generator) # type: ignore
builder.add_node('evaluator', evaluator) # type: ignore

builder.add_edge(START, 'generator')
builder.add_edge('generator', 'evaluator')
builder.add_conditional_edges('evaluator',
                              path=routing_function,
                              path_map={'Accepted': END,
                                         'Rejected': 'generator'})

graph = builder.compile()
