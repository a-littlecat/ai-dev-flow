# ai-dev-flow

[English](README.en.md)

面向个人开发者的 AI 辅助开发工作流 Skill。

`ai-dev-flow` 是一套 Markdown-first、Git-first 的通用项目工作流，帮助 Codex、Claude Code、Gemini CLI、Cursor、DeepSeek 以及其他 coding agent 在长期软件项目里更稳地工作：拆任务、记录状态、建立 Git 基线、做 diff 审查、沉淀验证证据，并明确用户到底需要如何验收。

它的目标很直接：让 AI 写代码更快，但项目仍然清楚、可审查、可回退，并且始终由你控制。

## 为什么需要它

AI coding agent 很擅长改代码，但长期项目真正麻烦的地方通常不是“能不能改”，而是：

- 当前到底在做哪个任务；
- 这个任务允许改哪些文件；
- 哪些 diff 属于这个任务；
- 任务是真的完成了，还是只是“看起来完成”；
- 审查意见有没有写回项目文件；
- 用户到底需要看摘要、读文档、看证据、运行测试，还是做决策；
- 多个 AI 会话会不会同时改同一模块；
- 什么时候才可以合并。

`ai-dev-flow` 把这些容易散在聊天里的状态，变成项目里的任务文件、看板、审查记录和验收建议。

## 你会得到什么

- 长期项目的需求拆分流程。
- `TASK_BOARD` 和每个任务一个 Markdown 文件。
- Git baseline 和任务前 Git precheck。
- A/B/C/D 任务分级。
- 分支 / Worktree 使用规则，但不强迫每个小任务都建分支。
- 基于 diff 的代码审查，而不是泛泛读文件。
- 审查严重等级：`P0 / P1 / P2 / P3`。
- 用户动作等级：`UA0` 到 `UA7`。
- A/B 小任务批量处理 Batch。
- 多执行会话并行调度 Parallel Wave。
- 合并、发布、删除、密钥、本机配置等安全边界。
- 可复制提示词，不支持 Skill 的 agent 也能按 Markdown 使用。

## 核心理念

`TASK` 永远是最小责任单位。

Batch 和 Wave 只是执行组织方式：

- `Single Task`：一个执行会话只处理一个任务。
- `Batch`：一个执行会话顺序处理多个低风险 A/B 小任务。
- `Parallel Wave`：多个执行会话同时处理多个互不冲突的任务。

无论使用 Batch 还是 Wave，都不能吞掉任务边界。每个任务仍然要独立记录 diff、验证结果、审查结论和用户动作等级。

## 适合谁

适合你，如果你：

- 在真实软件项目里使用 AI agent；
- 希望任务状态不要只留在聊天记录里；
- 希望 AI 的改动可以稳定 diff 审查；
- 不想 AI 顺手做大范围无关重构；
- 希望明确哪些任务需要用户验收，哪些只需要看证据；
- 会同时使用多个 AI 会话，需要避免文件和模块冲突。

它不绑定任何业务领域、语言、框架或特定 agent。

## 不适合什么

如果只是下面这些场景，这套流程可能太重：

- 一次性小脚本；
- 临时 demo；
- 快速试验；
- 只问问题，不修改项目文件；
- 不需要 Git、任务记录和审查的小草稿。

## 安装

本仓库的 Skill 位于：

```text
skills/ai-dev-flow/
```

### Codex

复制 Skill 到 Codex 的 skills 目录：

```text
~/.codex/skills/ai-dev-flow/
```

Windows 通常是：

```text
C:\Users\<you>\.codex\skills\ai-dev-flow\
```

然后对 Codex 说：

```text
请使用 ai-dev-flow，为当前项目初始化 AI 辅助开发工作流。
```

也可以直接使用中文唤醒词：

```text
用 AI开发流程，帮我拆任务。
```

### Claude Code、Gemini CLI、Cursor、DeepSeek 或其他 agent

如果你的 agent 支持 Skill 或自定义指令包，把 `skills/ai-dev-flow/` 复制到对应目录即可。

如果不支持 Skill，让 agent 把下面三个文件当成普通 Markdown 工作流说明读取：

```text
skills/ai-dev-flow/SKILL.md
skills/ai-dev-flow/references/WORKFLOW.md
skills/ai-dev-flow/references/PROMPTS.md
```

## 快速开始

### 1. 初始化项目工作流

```text
请使用 ai-dev-flow 初始化当前项目工作流。
先读取已有 README、AGENTS.md、docs/ 和关键配置。
不要修改业务代码。
```

agent 会创建或建议创建类似结构：

```text
docs/
├── PROJECT_INDEX.md
├── TASK_BOARD.md
├── DECISIONS.md
├── CODE_REVIEW_CHECKLIST.md
├── batches/
├── plans/
├── tasks/
└── waves/
```

### 2. 把需求拆成任务

```text
请使用 ai-dev-flow，把下面需求拆成小任务：
<粘贴需求>
```

任务会带上目标、非目标、完成标准、风险等级、建议执行位置和验证方式。

### 3. 执行单个任务

```text
请使用 ai-dev-flow，执行 docs/tasks/TASK-001.md。
```

agent 应先检查 Git 状态、记录 base commit、遵守任务边界，完成后更新任务文件并提供验证证据。

### 4. 基于 diff 审查

```text
请使用 ai-dev-flow，基于 diff 审查 docs/tasks/TASK-001.md。
```

审查应基于当前任务 diff，而不是泛泛读一遍文件。

### 5. 明确用户动作等级

每个任务完成后都应给出 `UA` 建议：

- `UA0`：无需用户验收，agent 自证即可。
- `UA1`：用户只看摘要。
- `UA2`：用户读文档或方案。
- `UA3`：用户只看验证证据，不自己运行。
- `UA4`：用户本地运行验收。
- `UA5`：用户在真实业务环境测试。
- `UA6`：用户做回归验收。
- `UA7`：必须用户决策。

agent 不应该只写“需要人工验收”，而要写清楚用户到底要做什么。

## Batch 和 Parallel Wave

### Batch：批量小任务

Batch 用来处理多个低风险小任务。

一个执行会话顺序完成多个 A/B 任务，再由一个审查会话批量审查。

规则：

- 只用于 A/B 小任务。
- C/D 任务仍然单独处理。
- diff 必须能按任务拆分。
- 批量审查必须逐任务输出结论。

### Parallel Wave：并行波次

Parallel Wave 用来安全地并行处理多个互不冲突任务。

并行前必须检查：

- 预计修改文件；
- 影响模块；
- 依赖关系；
- 文件锁；
- 模块锁；
- 任务风险等级；
- 用户动作等级。

规则：

- 并行执行不是默认行为。
- 必须用户确认。
- D 级和 `UA5 / UA6 / UA7` 代码任务默认不进入代码并行。
- Review Hub 可以集中审查 Wave，但必须逐任务输出结论。

## 仓库结构

```text
ai-dev-flow/
├── README.md
├── README.en.md
├── LICENSE
├── skills/
│   └── ai-dev-flow/
│       ├── SKILL.md
│       ├── README.md
│       ├── CHANGELOG.md
│       ├── VERSION
│       ├── references/
│       └── scripts/
└── .gitignore
```

根目录 `README.md` 是开源仓库首页。

Skill 的详细使用手册在：

```text
skills/ai-dev-flow/README.md
```

## 安全默认值

`ai-dev-flow` 默认保守：

- 不自动 merge；
- 不自动 push；
- 不自动 release；
- 不盲目 `git add .`；
- 不自动删除分支；
- 不自动删除 Worktree；
- 不提交密钥、本机配置、构建产物、依赖目录或日志；
- 没有 Git baseline 不开始代码任务；
- 没有明确 diff 不做代码审查；
- 没有验证证据不声称任务完成。

## 当前版本

```text
0.5.1
```

变更记录见：

```text
skills/ai-dev-flow/CHANGELOG.md
```

## License

本项目使用 MIT License。

详见：

```text
LICENSE
```

## 贡献

欢迎提交 issue 和 pull request。

好的贡献应保持这套流程：

- 通用；
- Markdown-first；
- agent-neutral；
- Git-aware；
- 默认安全；
- 清楚区分 AI 验证和用户确认；
- 不写入特定项目业务规则。

## 发布前检查

公开 push 前建议运行：

```text
git status --short
git diff --cached --name-only
```

并确认：

- 已包含 `LICENSE`；
- 没有 `.env` 或密钥；
- 没有本机路径；
- 没有日志、附件、缓存或依赖目录；
- 只提交了预期的 `skills/ai-dev-flow/` 文件和仓库说明文件。
