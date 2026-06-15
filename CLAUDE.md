# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Language Preference

**All responses should be in Chinese (中文)**. Use Chinese when answering questions, explaining code, or providing guidance to the user.

## Project Overview

This is a LangGraph-based agent application that orchestrates tools via MCP (Model Context Protocol) clients. The graph definition is in `src/agent/graph4_prebuild_node.py` (configured in `langgraph.json`), not the template's `graph.py`.

## Architecture

- **Graph Definition**: `src/agent/graph4_prebuild_node.py` defines the main graph using `StateGraph` with `MessagesState`
- **MCP Integration**: Uses `MultiServerMCPClient` from `langchain_mcp_adapters` to connect to multiple MCP servers (local search, web search, chart visualization, 12306, etc.)
- **LLM Configuration**: `src/agent/my_llm.py` configures the LLM (supports Zhipu GLM-4.5-flash or local Qwen3-8B via OpenAI-compatible API)
- **State Management**: Uses `MessagesState` for the graph state, with an agent node that calls the LLM and a conditional edge to ToolNode

The graph follows the standard LangGraph pattern: `START → agent → (tools_condition) → tools → agent → END`

## Development Commands

### Running the LangGraph Server
```bash
langgraph dev
```

### Testing
- Run all unit tests: `make test` or `python -m pytest tests/unit_tests`
- Run integration tests: `make integration_tests` or `python -m pytest tests/integration_tests`
- Run specific test file: `make test TEST_FILE=tests/unit_tests/test_configuration.py`
- Watch mode: `make test_watch`

### Linting and Formatting
- Format code: `make format` or `ruff format . && ruff check --select I --fix .`
- Lint (ruff + mypy): `make lint` or `ruff check . && mypy --strict src/`
- Check only: `ruff check . --diff && mypy --strict src/ --diff`

### Installation
```bash
pip install -e . "langgraph-cli[inmem]"
```
Or using uv (as in CI):
```bash
uv venv
uv pip install -r pyproject.toml
```

## Configuration

- `langgraph.json`: Defines which graph to load and environment file location
- `.env`: Contains API keys (`ZHIPU_API_KEY`, `GEMINI_API_KEY`) and optionally `LANGSMITH_API_KEY` for tracing
- Environment variables are loaded via `python-dotenv` in `get_env.py`

## Important Notes

- The graph is created asynchronously at module load time (`graph = asyncio.run(create_graph())`) - the MCP tools are fetched once at import
- Multiple MCP server configurations are commented out in `graph4_prebuild_node.py` - uncomment as needed
- Integration tests run daily via cron in GitHub Actions and require `ANTHROPIC_API_KEY` and `LANGSMITH_API_KEY` secrets