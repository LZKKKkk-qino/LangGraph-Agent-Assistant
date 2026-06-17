# LangGraph Agent Assistant - Claude 项目指南

## 项目概述

这是一个基于 LangGraph 构建的智能 Agent 助手，支持多 LLM 切换、MCP 工具集成、多模态输入和可控的工具调用流程。

## 核心技术栈

- **LangGraph**: 用于构建 Agent 工作流
- **LangChain**: LLM 和工具集成
- **Gradio**: Web UI 界面
- **MCP (Model Context Protocol)**: 工具集成协议
- **vLLM**: 本地 LLM 推理加速

## 项目结构

```
src/agent/
├── __init__.py
├── my_llm.py              # LLM 配置（文本和多模态）
├── graph.py               # LangGraph 模板
├── graph3.py              # 基础 Agent 版本
├── graph4_*.py            # Langgraph Prebuilt ToolNode 版本
├── graph5_*.py            # interrupt_before 实验
├── graph6_*.py            # Command + interrupt 优化
├── graph7_textonly_ui.py  # 文本对话版本（Gradio UI）
├── graph8_mutimodal_ui.py # 多模态版本（支持文本/图片/视频/音频/文件）
└── tools/                 # 本地工具
    └── tool_test1-test9.py # 构建tool的不同方式

employment/scripts/        # 本地 LLM 部署脚本
├── server_run.py          # 启动本地 API 服务
└── model_api_server.py    # OpenAI 兼容 API 服务器

static/                    # 静态资源
├── graph7_gradio_ui.png   # 文本对话界面截图
├── graph8_gradio_ui.png   # 多模态界面截图
└── langsmith_agent_architecture.png  # 架构图
```

## 关键设计决策

### 自定义 ToolNode

项目使用自定义的 `BasicToolsNode` 而非 LangGraph 预置的 `ToolNode`，原因如下：

1. **完全自主控制**：工具执行逻辑完全由用户代码定义，不受预置 API 限制
2. **灵活的错误处理**：可根据不同工具类型实现差异化的错误恢复和重试策略
3. **深度定制**：支持在工具执行前后插入自定义逻辑（如日志记录、权限验证、参数校验）
4. **异步适配**：原生支持同步/异步工具的统一调用接口
5. **易于扩展**：添加新工具类型或修改现有工具行为无需依赖框架更新

### 多模态支持 (Graph 8)

`graph8_mutimodal_ui.py` 提供了完整的多模态支持：

- **输入类型**：文本、图片、视频、音频、文件
- **文件处理**：自动根据文件类型进行不同处理
- **流式/非流式切换**：根据 LLM 配置自动切换输出模式
- **工具结果折叠展示**：通过 metadata 实现 ToolMessage 的可折叠展示

### 流式/非流式切换

- **流式模式**：使用 `stream_mode=['messages','updates']`，逐 token 实时显示
- **非流式模式**：使用 `stream_mode=['values','updates']`，整体输出
- **切换方式**：通过 `multimodal_llm.streaming` 配置

### ToolNode 的优化

- **条件绑定**：只在有工具时才调用 `bind_tools()`，避免模型在没有工具时产生意外的工具调用行为
- **Strict 模式**：使用 `bind_tools(tools, strict=True)` 确保模型严格遵守工具绑定

## MCP 工具配置

项目支持多个 MCP 服务器：

```python
# 搜索工具（智谱 AI）
search_mcp_server_config = {
    "url": f"https://open.bigmodel.cn/api/mcp-broker/proxy/web-search/mcp?Authorization={ZHIPU_API_KEY}",
    "transport": "streamable_http"
}

# 爬虫工具
fetch_mcp_server_config = {
    "url": "https://mcp.api-inference.modelscope.net/1c0fa2fb594140/sse",
    "transport": "sse"
}

# 可视化图表
chart_mcp_server_config = {
    "url": "https://mcp.api-inference.modelscope.net/d28d57421afb4a/sse",
    "transport": "sse"
}
```

## 本地 LLM 部署

通过 `employment/scripts/` 目录中的代码将本地 LLM 部署为符合 OpenAI API 规范的服务：

- **vLLM 引擎**：加速推理
- **FastAPI 服务器**：OpenAI 兼容 API
- **支持模型**：Qwen、GLM-4 等（可自行添加修改）

## 环境变量

主要环境变量配置：

```bash
# 本地 LLM 配置
LOCAL_LLM_BASE_URL=http://127.0.0.1:6006/v1/
LOCAL_LLM_MODEL=Qwen3-8B
LOCAL_LLM_API_KEY=any

# 智谱 API（多模态）
ZHIPU_API_KEY=your-zhipu-api-key

# Google Gemini API
GEMINI_API_KEY=your-gemini-api-key
```

## 工作流程

### 基本流程

```
用户输入 → Agent 节点 → 工具调用判断 → Tools 节点 → 返回结果
             ↓                                      ↓
         LLM (可配置)                           MCP 工具执行
```

### 工具调用确认流程

当 Agent 决定调用敏感工具时，会暂停并询问用户：

```
用户: 帮我搜索最新的人工智能新闻
Assistant: 模型尝试调用工具:webSearchStd,请选择是否调用，调用则回复"y"
用户: y  # 同意调用
Assistant: [返回搜索结果]
```

## 开发指南

### 添加新工具

1. 在 `src/agent/tools/` 目录创建新的工具文件
2. 定义工具函数并使用 `@tool` 装饰器
3. 在相应的 graph 文件中注册工具

### 启动不同版本

```bash
# 文本对话版本
python src/agent/graph7_textonly_ui.py

# 多模态版本
python src/agent/graph8_mutimodal_ui.py

# 启动本地 LLM 服务
cd employment/scripts
python server_run.py
```

### LangSmith 可视化

设置 `LANGSMITH_API_KEY` 环境变量后，可以在 LangGraph Studio 中可视化调试工作流。

## 调试技巧

1. **查看工具列表**：在 `create_graph()` 函数中添加 `print(f"获取到的工具列表: {tools}")`
2. **查看状态**：在 `route_tool_function()` 中添加状态打印
3. **查看 LLM 输入**：在 `chatbot()` 函数中添加状态打印
4. **查看流式输出**：在流式处理函数中添加 chunk 打印

## 注意事项

1. **工具绑定**：只在有工具时才调用 `bind_tools()`，避免模型在没有工具时产生意外的工具调用行为
2. **异步处理**：确保所有工具调用都正确处理同步/异步
3. **错误处理**：在工具执行中添加适当的错误处理
4. **资源清理**：注意清理临时文件和资源

## 版本说明

- **Graph 7**：文本对话版本，使用 Gradio UI
- **Graph 8**：多模态版本，支持流式/非流式切换，工具结果折叠展示