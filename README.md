# RepoMind

[![CI](https://github.com/lifuheng0271-bit/repomind/actions/workflows/ci.yml/badge.svg)](https://github.com/lifuheng0271-bit/repomind/actions/workflows/ci.yml)

> Repo memory & `AGENTS.md` maintainer CLI for AI coding agents. Linux-first, local-first, LLM-optional.

**RepoMind 是什么？** 一个本地 CLI 工具：自动理解你的代码库，生成并维护 `AGENTS.md` / `PROJECT_MEMORY.md`，让 Codex、Claude Code、Cursor、Aider 等 AI 编程助手每次进入项目时都有稳定、最新的上下文。

## 为什么

2026 年 AI Agent 的共同瓶颈是项目上下文：每个 Agent 每次都要重新理解项目结构、启动方式与历史决策。RepoMind 把这层"项目记忆"做成独立的轻量工具。

## 安装

```bash
pip install -e .
```

## 使用

```bash
cd your-project/
repomind init      # 初始化 .repomind/
repomind scan      # 扫描项目，保存快照
repomind update    # 生成/更新 AGENTS.md 与 PROJECT_MEMORY.md
repomind ask "这个项目怎么运行？"   # LLM 项目问答（需在配置中启用）
repomind doctor                       # 体检：配置/依赖/LLM 连通性
```

### 启用 LLM 问答（可选）

编辑 `.repomind/config.toml`：

```toml
[llm]
enabled = true
endpoint = "http://localhost:11434/v1"   # Ollama 或任意 OpenAI-compatible API
model = "qwen3"
api_format = "chat"                      # "chat"（默认）或 "completions"
api_key_env = "REPOMIND_API_KEY"         # 可选：从该环境变量读 key
```

本地 Ollama 无需 key；云端 API 则 `export REPOMIND_API_KEY=...`。

**api_format 说明：**

- `"chat"`：标准 `/v1/chat/completions` 消息格式（OpenAI、DeepSeek、Ollama、vLLM 等）
- `"completions"`：经典 `/v1/completions` 文本补全格式（llama.cpp server、旧版接口、部分本地推理服务）；RepoMind 会自动把 system+user 拼成单个 prompt，并解析 `choices[0].text`

生成的文件：

```text
AGENTS.md            # AI 助手入口文档：技术栈、启动命令、目录结构
PROJECT_MEMORY.md    # 每次扫描的变更历史（最新在前）
.repomind/
  config.toml        # 配置（LLM 可选）
  snapshots/         # 扫描快照 JSON
```

## 特性

- ✅ 无需 LLM 即可工作（纯模板模式）
- ✅ 支持 Python / Node.js / Rust / Go 技术栈识别
- ✅ 快照 diff：知道两次扫描之间改了什么
- ✅ 原子写入，不会写坏文件
- ✅ `repomind ask`：LLM 项目问答（Ollama / OpenAI-compatible，零依赖 urllib 实现）
- ✅ `repomind doctor`：环境/配置/LLM 连通性体检（`--no-ping` 跳过在线测试）
- 🔜 v0.4: ARCHITECTURE.md 生成（LLM 增强）、PyPI 发布

## 开发

```bash
pip install -e ".[dev]"
pytest
```

## 设计文档

见 [docs/specs/2026-07-20-repomind-design.md](docs/specs/2026-07-20-repomind-design.md)。

## License

MIT