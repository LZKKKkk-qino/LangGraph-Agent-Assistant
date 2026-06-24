# LangGraph Agent Assistant

基于 LangGraph 的企业级智能 Agent 框架，支持多 LLM 切换、MCP 工具集成、多模态输入和可控的工具调用流程。

## 技术栈

- **LangGraph**: Agent 工作流构建
- **LangChain**: LLM 和工具集成
- **Gradio**: Web UI 界面
- **MCP**: 工具集成协议
- **vLLM**: 本地 LLM 推理加速

## 项目结构

```
src/agent/
├── my_llm.py              # LLM 配置（文本/多模态）
├── graph7_textonly_ui.py  # 文本对话版本
├── graph8_mutimodal_ui.py # 多模态版本（文本/图片/视频/音频/文件）
└── tools/                 # 本地工具

employment/scripts/        # 本地 LLM 部署
static/                    # 静态资源
```

## 关键设计

### 自定义 ToolNode

使用 `BasicToolsNode` 替代 LangGraph 预置 `ToolNode`：
- 完全自主控制工具执行逻辑
- 支持同步/异步工具统一接口
- 灵活的错误处理和重试策略
- 工具执行前后可插入自定义逻辑

### 多模态支持 (Graph 8)

- **输入类型**：文本、图片、视频、音频、文件
- **流式/非流式切换**：通过 `multimodal_llm.streaming` 配置
- **工具结果折叠展示**：通过 metadata 实现

### 流式输出模式

- **流式模式**：`stream_mode=['messages','updates']`，逐 token 实时显示
- **非流式模式**：`stream_mode=['values','updates']`，整体输出

### ToolNode 优化

- **条件绑定**：只在有工具时才调用 `bind_tools()`
- **Strict 模式**：使用 `bind_tools(tools, strict=True)`

## 环境变量

```bash
# 本地 LLM
LOCAL_LLM_BASE_URL=http://127.0.0.1:6006/v1/
LOCAL_LLM_MODEL=Qwen3-8B
LOCAL_LLM_API_KEY=any

# 云端 API
ZHIPU_API_KEY=your-zhipu-api-key
GEMINI_API_KEY=your-gemini-api-key

# LangSmith
LANGSMITH_API_KEY=lsv2...
LANGSMITH_PROJECT_NAME=langgraph-agent-assistant
```

## 启动命令

```bash
# 文本对话版本
python src/agent/graph7_textonly_ui.py

# 多模态版本
python src/agent/graph8_mutimodal_ui.py

# 本地 LLM 服务
cd employment/scripts
python server_run.py

# LangGraph Server
langgraph dev
```

## 核心函数

### 消息处理

- `submit_messages_stream()` - 流式异步生成器
- `submit_messages_not_stream()` - 非流式异步生成器
- `add_message()` - 前端消息输入处理
- `get_all_latest_user_message()` - 用户输入聚合

### 文件处理

- `transcribe_audio()` - 音频 Base64 编码
- `transcribe_image()` - 图片 Base64 编码
- `transcribe_video()` - 视频路径处理
- `read_file()` - 文件内容读取

## 工作流程

```
用户输入 → Agent 节点 → 工具调用判断 → Tools 节点 → 返回结果
             ↓                                      ↓
         LLM (可配置)                           MCP 工具执行
```

## 调试技巧

1. 在 `create_graph()` 中添加 `print(f"工具列表: {tools}")`
2. 在 `route_tool_function()` 中添加状态打印
3. 在流式处理函数中添加 chunk 打印

## 注意事项

1. **工具绑定**：只在有工具时才调用 `bind_tools()`
2. **异步处理**：确保同步/异步工具正确处理
3. **错误处理**：工具执行中添加适当错误处理
4. **资源清理**：注意清理临时文件和资源

## 版本说明

- **Graph 7**：文本对话版本
- **Graph 8**：多模态版本，支持流式/非流式切换，工具结果折叠展示