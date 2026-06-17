# LangGraph Agent Assistant

一个基于 LangGraph 构建的智能 Agent 助手，支持多 LLM 切换、MCP 工具集成和可控的工具调用流程。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2.6+-purple.svg)](https://github.com/langchain-ai/langgraph)
[![Gradio](https://img.shields.io/badge/Gradio-WebUI-orange.svg)](https://gradio.app/)
[![LangSmith](https://img.shields.io/badge/LangSmith-Tracking-green.svg)](https://smith.langchain.com/)
[![Qwen](https://img.shields.io/badge/Qwen-Local_LLM-blue.svg)](https://github.com/Qwen/Qwen)
[![智谱AI](https://img.shields.io/badge/智谱AI-Cloud_LLM-blueviolet.svg)](https://open.bigmodel.cn/)
[![MCP](https://img.shields.io/badge/MCP-Protocol-red.svg)](https://modelcontextprotocol.io/)

## ✨ 特性

- 🤖 **多 LLM 支持**：无缝切换本地 LLM 模型与云端 API
- 🔧 **MCP 工具集成**：通过 Model Context Protocol 集成多种工具（搜索、爬虫、可视化等）
- 🎥 **多模态支持**：支持文本、图片、视频、音频、文件等多种输入形式，通过 `graph8_mutimodal_ui.py` 实现多模态大模型 Agent
- 🛠️ **自定义 ToolNode**：不依赖 LangGraph 预置的 ToolNode，用户可通过代码自行定义工具执行逻辑，实现更灵活的工具调用控制
- 🛡️ **工具调用确认**：使用 LangGraph 的 `interrupt` 机制，对敏感工具调用进行用户确认
- 🔄 **流式/非流式切换**：支持流式和非流式两种输出模式，可根据 LLM 配置自动切换，提升用户体验
- 📁 **工具结果折叠展示**：通过 metadata 对 ToolMessage 进行特殊处理，在 UI 中以可折叠卡片形式展示工具调用结果，保持界面整洁
- 🎨 **Gradio 交互界面**：提供友好的 Web UI，支持流式对话
- 📊 **LangSmith 可视化**：支持在 LangGraph Studio 中可视化调试

## 🏗️ 架构

<div align="center">
  <img src="./static/langsmith_agent_architecture.png" alt="Graph Architecture" width="70%" />
</div>

```
用户输入 → Agent 节点 → 工具调用判断 → Tools 节点 → 返回结果
             ↓                                      ↓
         LLM (可配置)                           MCP 工具执行
```

### 核心组件

| 组件             | 说明 |
|----------------|------|
| **Agent 节点**   | 接收消息，调用 LLM 生成回复或工具调用请求 |
| **自定义 Tools 节点**   | 自定义实现而非使用 LangGraph 预置 ToolNode，允许用户完全控制工具执行的逻辑、错误处理和结果处理 |
| **MCP Client** | 连接多个 MCP 服务器，动态获取可用工具 |
| **路由函数**       | 根据 LLM 输出判断是否需要调用工具 |

### 🛠️ 自定义 ToolNode 设计

本项目采用**自定义 ToolNode** 而非 LangGraph 预置的 `ToolNode`，这一设计带来了以下优势：

| 优势 | 说明 |
|------|------|
| **完全自主控制** | 工具执行逻辑完全由用户代码定义，不受预置 API 限制 |
| **灵活的错误处理** | 可根据不同工具类型实现差异化的错误恢复和重试策略 |
| **深度定制** | 支持在工具执行前后插入自定义逻辑（如日志记录、权限验证、参数校验） |
| **异步适配** | 原生支持同步/异步工具的统一调用接口 |
| **易于扩展** | 添加新工具类型或修改现有工具行为无需依赖框架更新 |

#### 自定义 ToolNode 示例

```python
def tool_node(state):
    """
    自定义 ToolNode 实现
    用户可以在此处完全自定义工具执行的逻辑
    """
    tool_calls = state["messages"][-1].tool_calls
    results = []

    for tool_call in tool_calls:
        # 1. 自定义参数校验
        if not validate_tool_args(tool_call):
            results.append(
                {
                    "role": "tool",
                    "content": "参数校验失败",
                    "tool_call_id": tool_call["id"]
                }
            )
            continue

        # 2. 自定义工具执行逻辑
        try:
            tool_output = execute_tool_with_custom_logic(tool_call)
            results.append({
                "role": "tool",
                "content": tool_output,
                "tool_call_id": tool_call["id"]
            })
        except Exception as e:
            # 3. 自定义错误处理
            results.append({
                "role": "tool",
                "content": f"工具执行失败: {str(e)}",
                "tool_call_id": tool_call["id"],
                "is_error": True
            })

    return {"messages": results}
```

用户可以根据实际需求修改上述代码，实现完全个性化的工具调用流程。

## 🚀 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone https://github.com/LZKKKkk-qino/LangGraph-Agent-Assistant
cd langgraph-agent-assistant

# 安装依赖
pip install -e . "langgraph-cli[inmem]"
```

### 2. 配置环境变量

复制 `.env.example` 到 `.env` 并填写配置：

```bash
cp .env.example .env
```

```bash
# .env
# LLM 配置（选择一种）

# 方式一：本地 Qwen 模型（推荐用于私有化部署）
LOCAL_LLM_BASE_URL=http://127.0.0.1:6006/v1/ OR YOUR_LOCAL_LLM_BASE_URL
LOCAL_LLM_MODEL=Qwen3-8B OR ANY_LOCAL_LLM_MODEL
LOCAL_LLM_API_KEY=ANY

# 方式二：智谱云端 API（支持文本对话）
ZHIPU_API_KEY=your-zhipu-api-key

# 方式三：Google Gemini API（多模态支持）
GEMINI_API_KEY=your-gemini-api-key

# 可选：LangSmith 追踪
LANGSMITH_API_KEY=lsv2...
```

> 💡 **多模态支持**：使用 `graph8_mutimodal_ui.py` 启动多模态版本时，需要配置支持多模态的 LLM API（如智谱 GLM-4.5v、Google Gemini Pro Vision 等）。

### 3. 启动服务

```bash
# 启动 LangGraph Server
langgraph dev

# 启动文本对话版本（Gradio UI）
python src/agent/graph7_textonly_ui.py

# 启动多模态版本（支持文本/图片/视频/音频/文件输入）
python src/agent/graph8_mutimodal_ui.py
```

访问 http://localhost:7860 使用 Gradio 界面。

#### 多模态界面 (Graph 8)

<div align="center">
  <img src="./static/graph8_gradio_ui.png" alt="Multimodal Gradio UI" width="70%" />
</div>

#### 文本对话界面 (Graph 7)

<div align="center">
  <img src="./static/graph7_gradio_ui.png" alt="Text-only Gradio UI" width="70%" />
</div>

## 🖥️ 本地 LLM 部署

本项目集成了本地私有化部署方案，可通过 `employment/` 目录中的代码将本地 LLM 部署为符合 OpenAI API 规范的服务。

### 部署架构

```
本地 GPU 服务器
├── vLLM 引擎（加速推理）
├── FastAPI 服务器（OpenAI 兼容 API）
└── 支持模型：Qwen、GLM-4 等(可自行添加修改)
```

### 部署步骤

#### 1. 安装依赖

```bash
pip install fastapi uvicorn vllm transformers pydantic sse-starlette
```

#### 2. 准备模型

下载模型到本地，例如：

```bash
# Qwen3-8B
git clone https://huggingface.co/Qwen/Qwen3-8B
```

#### 3. 配置环境变量

```bash
# 设置模型路径
export MODEL_PATH=/path/to/your/model

# Windows 下（PowerShell）
$env:MODEL_PATH="D:\models\Qwen3-8B"
```

#### 4. 启动本地 API 服务

```bash
# 进入 employment 目录
cd employment/scripts

# 启动服务（端口 6006）
python server_run.py
```

服务将在 `http://127.0.0.1:6006` 启动，提供以下接口：

| 接口 | 说明 |
|------|------|
| `GET /health` | 健康检查 |
| `GET /v1/models` | 获取可用模型列表 |
| `POST /v1/chat/completions` | 聊天补全（支持流式） |

> 💡 想了解更多本地 LLM 部署的详细信息，请访问：[local-llm-server 项目](https://github.com/LZKKKkk-qino/local-llm-server)

#### 5. 连接 LangGraph Agent

在 `.env` 文件中配置本地 LLM：

```bash
# 本地 Qwen 模型
LOCAL_LLM_BASE_URL=http://127.0.0.1:6006/v1/
LOCAL_LLM_MODEL=Qwen3-8B
LOCAL_LLM_API_KEY=any
```

### 本地 API 特性

| 特性 | 说明 |
|------|------|
| **OpenAI 兼容** | 完全兼容 OpenAI API 格式，可直接使用 LangChain 的 `ChatOpenAI` |
| **流式输出** | 支持 SSE 流式返回，提升响应体验 |
| **工具调用** | 支持 Function Calling，可与 LangGraph 无缝集成 |
| **多模态支持** | 支持多模态大模型，通过 `graph8_mutimodal_ui.py` 启用 |
| **多并发** | 基于 vLLM，支持高并发推理 |
| **GPU 优化** | 自动清理显存，支持 float16/bfloat16 |

### 核心代码说明

`employment/scripts/model_api_server.py` 包含以下核心功能：

- **OpenAI 数据模型**：完全兼容的请求/响应结构
- **消息处理**：支持 system/user/assistant/tool 角色转换
- **工具调用解析**：自动识别和格式化 Function Calling
- **流式生成器**：实时返回生成内容

## 📖 使用指南

### 🎥 多模态功能 (Graph 8)

`graph8_mutimodal_ui.py` 提供了完整的多模态支持，允许用户通过多种形式与 Agent 交互：

| 支持的输入类型 | 说明 |
|--------------|------|
| **文本** | 支持常规文本对话输入 |
| **图片** | 支持 PNG、JPEG、JPG、WEBP 格式，可进行图片理解和分析 |
| **音频** | 支持 MP3、WAV、M4A 格式，可进行语音识别和音频理解 |
| **视频** | 支持 MP4、AVI、MOV、MKV 格式，可进行视频内容理解 |
| **文件** | 支持各种文本文件，自动读取文件内容 |

#### 多模态输入示例

```
用户：[上传一张图片] + "这张图片里有什么？"
Agent：[识别图片内容并描述]

用户：[上传一个视频] + "请总结这个视频的主要内容"
Agent：[分析视频并生成摘要]

用户：[上传一份PDF] + "请帮我提取这份文档的关键信息"
Agent：[读取文件并提取关键内容]
```

#### 文件处理逻辑

系统会根据文件类型自动进行不同的处理：

- **图片文件**：转换为 Base64 编码，通过 `image_url` 类型传递给模型
- **音频文件**：转换为 Base64 编码的 WAV 格式，通过 `audio_url` 类型传递
- **视频文件**：直接使用文件路径，通过 `video_url` 类型传递
- **文本文件**：读取文件内容，通过 `text` 类型传递
- **其他文件**：仅显示文件名信息

#### 🔄 流式/非流式切换

Graph 8 支持根据 LLM 配置自动切换流式和非流式输出模式：

| 模式 | 说明 | 适用场景 |
|------|------|---------|
| **流式输出** | 逐 token 实时显示模型回复，使用 `stream_mode=['messages','updates']` | 需要实时查看生成过程 |
| **非流式输出** | 整体输出模型回复，使用 `stream_mode=['values','updates']` | 需要等待完整响应 |

配置方式：
```python
# 在 src/agent/my_llm.py 中设置
multimodal_llm = ChatOpenAI(
    model="glm-4.5v",
    streaming=True  # 设为 True 启用流式，False 使用非流式
)
```

#### 📁 工具结果折叠展示

在流式和非流式模式下，工具调用结果会以可折叠卡片的形式展示：

```python
# 工具消息带有 metadata
chat_history.append({
    "role": "assistant",
    "content": tool_msg_content,
    "metadata": {"title": f'🛠️ 正在使用工具：{message.name}'}
})
```

这样可以将详细的工具执行结果折叠起来，保持界面整洁，用户可点击展开查看详情。

### 工具调用确认流程

当 Agent 决定调用敏感工具（如 webSearchStd、webSearchSogou）时，会暂停并询问用户：

```
用户: 帮我搜索最新的人工智能新闻
Assistant: 模型尝试调用工具:webSearchStd,请选择是否调用，调用则回复"y"
用户: y  # 同意调用
Assistant: [返回搜索结果]
```

### MCP 工具配置

在 `graph7_ui.py` 中配置需要启用的 MCP 服务器：

```python
mcp_lient = MultiServerMCPClient({
    "search_mcp_server_config": search_mcp_server_config,
    "fetch_mcp_server_config": fetch_mcp_server_config,
    "chart_mcp_server_config": chart_mcp_server_config,
    # ... 其他配置
})
```

## 🔧 开发

### 代码结构

```
src/agent/
├── __init__.py
├── my_llm.py              # LLM 配置
├── graph.py               # LangGraph 模板
├── graph3.py              # 基础 Agent 版本
├── graph4_*.py            # Langgraph Prebulid ToolNode 版本
├── graph5_*.py            # interrupt_before 实验
├── graph6_*.py            # Command + interrupt 优化
├── graph7_textonly_ui.py  # 文本对话版本（Gradio UI）
├── graph8_mutimodal_ui.py # 多模态版本（支持文本/图片/视频/音频/文件）
└── tools/                 # 本地工具
    └── tool_test1-test9.py # 构建tool的不同方式

```

### 运行测试

```bash
# 单元测试
make test

# 集成测试
make integration_tests

# 代码格式化
make format

# 代码检查
make lint
```

## 🔐 安全说明 

- `.env` 文件包含敏感信息，已加入 `.gitignore`
- 上传前请确认 `.env` 不被提交
- 生产环境建议使用密钥管理服务

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📮 联系方式

- GitHub: https://github.com/LZKKKkk-qino
-  Gmail: 865476367ss@gmail.com