# RepoMind 设计文档

日期：2026-07-20
状态：已批准（brainstorm 结论）

## 一句话

面向 Linux 开发者的本地 CLI 工具：自动理解代码库、维护项目记忆文档，为 AI 编程助手（Codex / Claude Code / Cursor / Aider）生成稳定上下文。

## 背景与动机

2026 年 AI Agent 生态的共同瓶颈是项目上下文：每个 Agent 每次进入项目都要重新理解结构、启动方式与历史决策。参考项目：agent0ai/dox（AGENTS.md 自维护）、lazycodex（项目记忆+计划+验证）、comet（skill harness）、omnigent（编排与沙箱）。

RepoMind 把这层"项目记忆"做成独立、轻量、可本地运行的 CLI。

## 目标用户

- 使用 AI 编程工具的个人开发者（Linux 为主）
- 多项目切换、上下文经常丢失的人

## 核心命令

```bash
repomind init      # 初始化 .repomind/ 与配置
repomind scan      # 扫描项目结构，写入索引与快照
repomind update    # 增量更新 AGENTS.md / PROJECT_MEMORY.md
repomind ask "..." # 基于项目知识回答问题（LLM 可选，v0.2）
repomind doctor    # 检查配置、依赖、LLM 连接（v0.2）
```

## 生成文件

```text
AGENTS.md            # AI 助手入口文档：项目是什么、怎么跑、约定
PROJECT_MEMORY.md    # 变更历史摘要、上次进度
ARCHITECTURE.md      # 结构与模块说明（LLM 生成，可选）
.repomind/
  config.toml        # LLM endpoint、忽略规则
  index.sqlite       # 文件树、语言统计、哈希
  snapshots/         # 每次 scan 的快照 JSON
```

## 架构（三层，可独立测试）

1. **scanner**（无 LLM）：walk 文件树、忽略规则、语言/框架识别（package.json / pyproject.toml / Cargo.toml / go.mod）、抽取 README 与脚本命令，产出结构化 `ProjectFacts`。
2. **memory**（无 LLM）：SQLite 索引 + 快照 diff，回答"这次扫描相比上次改了什么"。
3. **writer**（LLM 可选）：把 ProjectFacts + diff 渲染成 Markdown。无 LLM 时用 Jinja2 模板纯规则生成；有 LLM 时增强总结质量。LLM 支持 OpenAI-compatible API 与 Ollama。

数据流：`scan -> facts -> index/snapshot -> diff -> render docs`。

## MVP 范围（v0.1）

- init / scan / update 三个命令
- Python + Node + Rust 三种技术栈识别
- 无 LLM 也能产出可用的 AGENTS.md（模板模式）
- ask 和 doctor 在 v0.2

## 非目标

- 不做代码修改，不做 Agent 执行
- 不做多仓库联合索引
- 不上传任何代码内容到远端（LLM 调用可选、可本地）

## 技术栈

Python 3.10+，typer、jinja2、sqlite3（标准库）、tomllib/tomli-w、httpx（LLM 调用）。

## 错误处理

- 非 git 目录也可运行，git 信息仅作增强
- LLM 不可用时降级为模板模式并提示
- 所有写文件操作先写临时文件再原子替换

## 测试

- scanner：fixture 项目目录（py/node/rust 各一）断言 facts
- memory：两次扫描 diff 断言
- writer：模板模式渲染快照测试
