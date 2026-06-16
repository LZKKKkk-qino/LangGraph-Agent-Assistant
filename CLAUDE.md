# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Language Preference

**All responses should be in Chinese (中文)**. Use Chinese when answering questions, explaining code, or providing guidance to the user.

## Project Overview

这是一个基于 LangGraph 构建的智能 Agent 助手项目，支持多 LLM 切换、MCP 工具集成和可控的工具调用流程。项目包含本地私有化部署方案，可将本地 LLM 部署为符合 OpenAI API 规范的服务。

## Architecture

### Graph 版本

项目包含多个 Graph 版本，用于不同场景和实验：

| 文件名 | 说明 | 状态 |
|--------|------|------|
| `graph.py` | LangGraph 原始模板 | 模板参考 |
| `graph2.py` | StateGraph 实验版本 | 实验 |
| `graph3.py` | 基础 Agent 版本，使用自定义 BasicToolsNode | 备用 |
| `graph4_prebuild_node.py` | 使用 LangGraph 预构建 ToolNode 的版本 | 备用 |
| `graph5_*.py` | 使用 `interrupt_before` + 手动状态管理 | 实验 |
| `graph6_*.py` | 使用 `Command` + `interrupt` 优化版 | 备用 |
| `graph7_ui.py` | **主版本**，集成 Gradio UI + 工具调用确认 | **生产** |

### 核心架构（graph7_ui.py）

```
START → chatbot 节点 → 路由判断 → tools 节点 → chatbot 节点 → END
                          ↓         ↓
                      无工具调用  工具调用确认
                                  ↓
                            MCP 工具执行
```

### 组件说明

- **Chatbot 节点**：接收消息，通过 `llm.bind_tools(tools)` 绑定工具后调用 LLM
- **Tools 节点**：自定义 `BasicToolsNode` 类，执行工具调用，支持同步/异步适配
- **MCP Client**：使用 `MultiServerMCPClient` 连接多个 MCP 服务器（搜索、爬虫、可视化等）
- **路由函数**：`route_tool_function()` 判断 LLM 输出是否包含工具调用请求
- **中断机制**：使用 LangGraph 的 `interrupt()` 对敏感工具调用进行用户确认

### Function Calling 实现

项目通过 LangChain 的标准模式实现 Function Calling：

```python
# 1. 获取 MCP 工具
tools = await mcp_lient.get_tools()

# 2. 绑定工具到 LLM
llm_with_tools = llm.bind_tools(tools)

# 3. LLM 输出包含 tool_calls 时，路由到 tools 节点
# 4. Tools 节点解析并执行工具调用
```

`bind_tools()` 方法将工具定义序列化为 LLM API 的 Function Calling 格式（OpenAI 兼容）。

### 本地 LLM 部署（employment/）

`employment/scripts/` 目录包含本地私有化部署方案：

| 文件 | 说明 |
|------|------|
| `model_api_server.py` | FastAPI 服务器，提供符合 OpenAI API 规范的接口 |
| `server_run.py` | 启动脚本 |

本地 API 特性：
- 完全兼容 OpenAI API 格式（`/v1/chat/completions`）
- 支持 SSE 流式输出
- 支持 Function Calling
- 基于 vLLM 引擎加速推理

## Development Commands

### 运行服务

```bash
# 启动 LangGraph Server
langgraph dev

# 启动 Gradio UI（主版本）
python src/agent/graph7_ui.py

# 启动本地 LLM API 服务
cd employment/scripts && python server_run.py
```

### 测试

```bash
# 运行单元测试
make test

# 运行集成测试
make integration_tests

# 运行特定测试文件
make test TEST_FILE=tests/unit_tests/test_configuration.py

# 监听模式
make test_watch
```

### 代码质量

```bash
# 格式化代码
make format

# 代码检查（ruff + mypy）
make lint

# 仅检查不修改
ruff check . --diff && mypy --strict src/ --diff
```

### 安装依赖

```bash
# 使用 pip
pip install -e . "langgraph-cli[inmem]"

# 使用 uv（CI 环境）
uv venv
uv pip install -r pyproject.toml
```

## Configuration

### langgraph.json

定义要加载的 graph 和环境文件位置：

```json
{
  "graphs": {
    "agent": "./src/agent/graph4_prebuild_node.py:graph"
  },
  "env": ".env"
}
```

注意：主版本实际使用 `graph7_ui.py`，但 `langgraph.json` 仍指向 `graph4_prebuild_node.py`。

### 环境变量 (.env)

```bash
# 本地 LLM 配置
LOCAL_LLM_BASE_URL=http://127.0.0.1:6006/v1/
LOCAL_LLM_MODEL=Qwen3-8B
LOCAL_LLM_API_KEY=any

# 云端 LLM 配置
ZHIPU_API_KEY=your-zhipu-api-key
GEMINI_API_KEY=your-gemini-api-key

# 可选：LangSmith 追踪
LANGSMITH_API_KEY=lsv2...
```

环境变量通过 `get_env.py` 加载（使用 `python-dotenv`）。

### MCP 服务器配置

在 graph 文件中配置：

```python
mcp_lient = MultiServerMCPClient({
    "search_mcp_server_config": {
        "url": f"https://open.bigmodel.cn/api/mcp-broker/proxy/web-search/mcp?Authorization={ZHIPU_API_KEY}",
        "transport": "streamable_http"
    },
    "fetch_mcp_server_config": {...},
    "chart_mcp_server_config": {...},
    # ...
})
```

## Code Structure

```
GIT/
├── src/agent/
│   ├── __init__.py
│   ├── my_llm.py              # LLM 配置（智谱/本地 Qwen）
│   ├── graph*.py              # 多个 Graph 版本
│   ├── build.py               # 结构化输出示例
│   └── tools/                 # 本地工具
│       ├── tool_test1-test9.py
│       └── __init__.py
├── employment/scripts/        # 本地 LLM 部署
│   ├── model_api_server.py    # OpenAI 兼容 API 服务器
│   └── server_run.py          # 启动脚本
├── static/                    # 静态资源（截图等）
│   ├── langsmith_agent_architecture.png
│   └── graph7_gradio_ui.png
├── tests/
├── langgraph.json
└── .env
```

## Important Notes

1. **Graph 初始化时机**：Graph 在模块加载时异步创建 (`graph = asyncio.run(create_graph())`)，MCP 工具在导入时获取一次
2. **工具调用确认**：`graph7_ui.py` 中对敏感工具（webSearchStd、webSearchSogou）调用时使用 `interrupt()` 进行用户确认
3. **自定义 Tools 节点**：`BasicToolsNode` 类支持同步/异步工具调用，使用 `asyncio.gather()` 并发执行
4. **MCP 配置**：多个 MCP 服务器配置在各 graph 文件中被注释，按需取消注释启用
5. **本地 LLM**：本地 Qwen 模型需要先通过 `employment/scripts/server_run.py` 启动 API 服务
6. **测试要求**：集成测试每日通过 cron 运行，需要 `ANTHROPIC_API_KEY` 和 `LANGSMITH_API_KEY` secrets

## GitHub Repository

- Repository: https://github.com/LZKKKkk-qino/LangGraph-Agent-Assistant
- Main Branch: main