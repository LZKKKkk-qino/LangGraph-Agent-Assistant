# 导入必要的库和模块
import os
from pathlib import Path
from threading import Thread
from typing import Union

import gradio as gr
import torch
from peft import AutoPeftModelForCausalLM, PeftModelForCausalLM
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    PreTrainedModel,
    PreTrainedTokenizer,
    PreTrainedTokenizerFast,
    StoppingCriteria,
    StoppingCriteriaList,
    TextIteratorStreamer
)

# 定义模型和分词器的类型别名
ModelType = Union[PreTrainedModel, PeftModelForCausalLM]
TokenizerType = Union[PreTrainedTokenizer, PreTrainedTokenizerFast]


# 设置模型和分词器的路径，默认从环境变量获取
MODEL_PATH = os.environ.get('MODEL_PATH', "/Qwen3.5-0.8B")
TOKENIZER_PATH = os.environ.get("TOKENIZER_PATH", MODEL_PATH)


def _resolve_path(path: Union[str, Path]) -> Path:
    """
    解析相对路径并返回绝对路径
    :param path: 输入的路径字符串或Path对象
    :return: 绝对路径的Path对象
    """
    return Path(path).expanduser().resolve()


# 加载预训练模型和分词器的函数
def load_model_and_tokenizer(
        model_dir: Union[str, Path], trust_remote_code: bool = True
) -> tuple[ModelType, TokenizerType]:
    """
    加载预训练模型和分词器
    :param model_dir: 模型目录路径
    :param trust_remote_code: 是否信任远程代码
    :return: 模型和分词器的对象元组
    """
    # 解析模型目录路径
    model_dir = _resolve_path(model_dir)
    # 检查是否存在PEFT适配器配置文件，决定加载PEFT模型还是普通模型
    if (model_dir / 'adapter_config.json').exists():
        # 加载PEFT模型
        model = AutoPeftModelForCausalLM.from_pretrained(
            model_dir, trust_remote_code=trust_remote_code, device_map='auto'
        )
        # 获取基础模型路径
        tokenizer_dir = model.peft_config['default'].base_model_name_or_path
    else:
        # 加载普通模型
        model = AutoModelForCausalLM.from_pretrained(
            model_dir, trust_remote_code=trust_remote_code, device_map='auto'
        )
        # 分词器路径与模型目录相同
        tokenizer_dir = model_dir
    # 加载分词器
    tokenizer = AutoTokenizer.from_pretrained(
        tokenizer_dir, trust_remote_code=trust_remote_code, use_fast=False
    )
    # 返回模型和分词器对象
    return model, tokenizer


# 加载模型和分词器实例
model, tokenizer = load_model_and_tokenizer(MODEL_PATH, trust_remote_code=True)


# 定义一个类，用于在生成文本时停止生成
class StopOnTokens(StoppingCriteria):
    def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor, **kwargs) -> bool:
        # 获取模型配置中的结束标记ID
        stop_ids = model.config.eos_token_id

        if stop_ids is None:
            return False

        # 统一转换为列表格式
        if isinstance(stop_ids, int):
            stop_ids = [stop_ids]

        for stop_id in stop_ids:
            # 如果当前生成的最后一个token是结束标记，则停止生成
            if input_ids[0][-1] == stop_id:
                return True
        # 如果没有遇到结束标记，则继续生成
        return False


# 定义一个函数，用于解析和格式化输出文本
# 这个函数 parse_text 用于将 Markdown 格式的文本转换为 HTML 格式，特别是处理包含代码块的文本。
def parse_text(text):
    # 按行分割文本
    lines = text.split("\n")
    # 过滤掉空行
    lines = [line for line in lines if line != ""]
    count = 0  # 统计输出文本的行数
    # 遍历每一行文本
    for i, line in enumerate(lines):
        # 检查是否包含代码块标记
        # 第一行代码块
        if "```" in line:  # ``` 是代码块的起始和结束
            count += 1
            items = line.split('`')
            # 如果是代码块开始，添加HTML标签
            # 代码块是成对的，所以 count%2==1 表示当前是代码块的开始
            if count % 2 == 1:
                # items[-1] ：计算机语言的标记
                lines[i] = f'<pre><code class="language-{items[-1]}">'
            # 如果是代码块结束，添加HTML标签
            # count % 2 == 0 表示当前是代码块的结束
            else:
                lines[i] = f'<br></code></pre>'
        else:
            # 如果不是第一行，且在代码块中，对特殊字符进行转义
            if i > 0:
                if count % 2 == 1:
                    line = line.replace("`", "\`")
                    line = line.replace("<", "&lt;")
                    line = line.replace(">", "&gt;")
                    line = line.replace(" ", "&nbsp;")
                    line = line.replace("*", "&ast;")
                    line = line.replace("_", "&lowbar;")
                    line = line.replace("-", "&#45;")
                    line = line.replace(".", "&#46;")
                    line = line.replace("!", "&#33;")
                    line = line.replace("(", "&#40;")
                    line = line.replace(")", "&#41;")
                    line = line.replace("$", "&#36;")
                # 添加换行标签
                lines[i] = "<br>" + line
    # 将处理后的文本行合并
    text = "".join(lines)
    # 返回格式化后的文本
    return text


# 定义一个函数，用于生成聊天文本
def predict(history, prompt, max_length, top_p, temperature):
    # 创建一个停止条件实例
    stop = StopOnTokens()
    # 初始化消息列表
    messages = []
    # 如果提供了提示词，将其添加到消息列表中
    if prompt and prompt != "":
       messages.append({"role": "system", "content": prompt})

    # 遍历历史消息
    print(history)
    for idx, msg in enumerate(history):

        role = msg.get("role")
        content = msg.get("content")
        if prompt and idx == 0 and content == prompt:
            continue
        # 如果是最后一条消息且为空，也就说明这条是 AI 回复的 AIMessage
        # 模型还没给出回答，添加当前用户问题，准备直接加入 messages 输入给模型
        if idx == len(history) - 1 and not content:
            continue

        if role == "user":
            messages.append({"role": "user", "content": content})
        elif role == "assistant":
            messages.append({"role": "assistant", "content": content})

    print(messages)
    # 使用分词器将消息列表转换为模型输入
    # tokenizer：它负责将原始文本转换为模型可以理解的格式。
    model_inputs = (tokenizer.apply_chat_template(messages,
                                                  add_generation_prompt=True,
                                                  tokenize=True,
                                                  return_tensors="pt")
                    # next()是因为 model.parameters() 是一个
                    .to(next(model.parameters()).device))
    # 创建一个文本迭代器流
    streamer = TextIteratorStreamer(
        tokenizer,
        timeout=60,  # 超时时间为: 60秒数。流将被终止
        skip_prompt=True,  # 这个参数指示是否跳过生成的初始提示（prompt）。如果设置为 True，则生成的输出将不包含初始提示，只包含模型生成的部分。
        skip_special_tokens=True)  # 跳过特殊 token。特殊 token 包括 [CLS], [SEP], [PAD] 等，这些 token 通常用于模型内部的处理，但在最终输出中没有实际意义。
    # 定义生成文本的参数
    generate_kwargs = {
        "input_ids": model_inputs["input_ids"],
        "streamer": streamer,
        "max_new_tokens": max_length,
        "do_sample": True,
        "top_p": top_p,
        "temperature": temperature,
        "stopping_criteria": StoppingCriteriaList([stop]),
        "repetition_penalty": 1.2,
        "eos_token_id": model.config.eos_token_id,
    }
    # 创建一个线程来生成文本
    t = Thread(target=model.generate, kwargs=generate_kwargs)
    t.start()
    # 遍历生成的文本流
    res = ""
    history.append({"role": "assistant", "content": res})
    for new_token in streamer:
        # 如果有新的token，将其添加到历史消息中
        if new_token:
            res += new_token
            history[-1]['content'] = res

        # 生成并返回更新后的历史消息
        yield history

# 定义一个函数，用于处理用户输入
def user_question(query, history):
    return "", history + [{"role": "user", "content": parse_text(query)}]


# 定义一个函数，用于设置提示词
def set_prompt(prompt_text):
    return [{"role": "system", "content": parse_text(prompt_text)},
                {"role": "assistant", "content": "已设定prompt"}]


# 使用Gradio构建Web界面
with gr.Blocks() as demo:  # gr.Blocks 是 Gradio 的顶级容器，用于创建整个应用的布局。

    # 添加HTML标题
    gr.HTML("""<h1 align="center">七爷私有AI大模型Chatbot</h1>""")

    # 创建一个聊天机器人界面组件
    chatbot = gr.Chatbot()  # 聊天记录的视图组件

    # 创建一个行布局
    with gr.Row():  # 水平布局容器

        # 创建一个列布局
        with gr.Column(scale=3):  # 垂直布局容器
            # 创建一个文本框用于用户输入
            with gr.Column(scale=12):
                user_input = gr.Textbox(show_label=False, placeholder="输入...", lines=10, container=False)
            # 创建一个提交按钮
            with gr.Column(min_width=32, scale=1):
                submitBtn = gr.Button("提交")  # 提交用户问题的 按钮

        # 创建另一个列布局
        with gr.Column(scale=1):
            # 创建一个文本框用于输入提示词
            prompt_input = gr.Textbox(show_label=False, placeholder="提示词", lines=10, container=False)
            # 创建一个按钮用于设置提示词
            pBtn = gr.Button("系统提示词设置")

        # 创建第三个列布局
        with gr.Column(scale=1):
            # 创建一个按钮用于清除聊天记录
            emptyBtn = gr.Button("清除聊天记录")
            # 创建一个滑块用于设置最大长度
            max_length = gr.Slider(0, 32768, value=1024, step=1.0, label="最大长度", interactive=True)
            # 创建一个滑块用于设置Top P值
            top_p = gr.Slider(0, 1, value=0.8, step=0.01, label="Top P", interactive=True)
            # 创建一个滑块用于设置温度
            temperature = gr.Slider(0.01, 1, value=0.6, step=0.01, label="Temperature", interactive=True)


    # 将设置提示词的函数绑定到按钮点击事件
    pBtn.click(set_prompt, inputs=[prompt_input], outputs=chatbot)
    # 将用户输入的函数绑定到提交按钮点击事件
    submitBtn.click(user_question, [user_input, chatbot], [user_input, chatbot], queue=False).then(
        predict, [chatbot, prompt_input, max_length, top_p, temperature], chatbot
    )
    # 将清除聊天记录的函数绑定到按钮点击事件
    emptyBtn.click(lambda: (None, None), None, [chatbot, prompt_input], queue=False)
# 启动Gradio演示
demo.queue()
demo.launch(server_name="127.0.0.1", server_port=6006, inbrowser=True, share=True)
