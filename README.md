# ai-dev-flow

[English](README.en.md)

一个给个人开发者用的 AI 项目工作流。

它想解决的不是“AI 会不会写代码”，而是另一个更日常的问题：

> 当 AI agent 连续帮你改一个真实项目时，你怎么知道它现在在做什么、改了哪里、有没有越界、是否真的完成，以及什么时候该由你确认？

`ai-dev-flow` 把这些容易散在聊天里的东西，变成项目里的 Markdown 文件、Git diff、任务看板、审查记录和验收建议。

它不绑定 Codex、Claude Code、Gemini CLI、Cursor、DeepSeek 或任何特定工具。支持 Skill 的 agent 可以直接加载；不支持 Skill 的 agent 也可以把它当作普通 Markdown 工作流说明读取。

## 为什么需要它

如果只是让 AI 写一个小脚本，流程当然不需要这么多。

但真实项目会慢慢变成这样：

- 你开了好几个 AI 会话，忘了谁在改哪个任务。
- AI 顺手改了无关文件，但聊天里看不出来。
- 任务说“完成了”，其实没有验证证据。
- 审查意见只留在对话里，下一轮 agent 看不到。
- 你不知道自己到底该看摘要、跑程序、做实机测试，还是直接决策。
- 几个任务一起推进时，两个 agent 可能会改到同一块代码。

`ai-dev-flow` 的作用，就是给 AI 一个稳定的工作习惯：先拆任务，再限定范围，基于 Git diff 做审查，验证后再告诉你需要做什么。

## 你会得到什么

一套不依赖特定工具的项目约定：

- 用 `TASK_BOARD` 和每个任务一个 Markdown 文件记录状态。
- 用 Git baseline 和 base commit 锁住任务起点。
- 用 A/B/C/D 区分小文档、小代码、中等任务和高风险任务。
- 小任务不强制分支，大任务再用分支或 Worktree 隔离。
- 代码审查基于 diff，而不是泛泛读文件。
- 审查问题用 `P0 / P1 / P2 / P3` 表达严重程度。
- 任务完成后用 `UA0` 到 `UA7` 告诉你到底需要做什么。
- A/B 小任务可以 Batch 批量处理，互不冲突的任务可以 Parallel Wave 并行推进。
- 支持 Intake、Loop、角色边界、Memory、Project Constitution 和 Harness 兼容说明。

它的默认态度很保守：不自动合并、不自动发布、不自动删除、不提交密钥、不盲目 `git add .`。AI 可以跑快一点，但方向盘仍然在你手里。

## 核心理念

`TASK` 永远是最小责任单位。

Batch、Wave 和 Loop 都只是组织方式：

- `Single Task`：一个执行会话只处理一个任务。
- `Batch`：一个执行会话顺序处理多个低风险 A/B 小任务。
- `Parallel Wave`：多个执行会话同时处理多个互不冲突的任务。
- `Loop`：外层编排已有模式，不替代任务状态。

无论使用 Batch、Wave 还是 Loop，都不能吞掉任务边界。每个任务仍然要独立记录 diff、验证结果、审查结论和用户动作等级。

## 角色不等于会话

v0.6.0 的角色机制用于约束职责，不要求每个角色都单独开一个会话。

默认最小会话模型是：

- 总览会话：Orchestrator / Planner / Archivist。
- 执行会话：Engineer / Verifier / Repairer。
- 审核会话：Reviewer。

同一会话可以在不同阶段切换多个角色，但每一轮都要声明当前角色和当前模式。Reviewer 不直接修复，Engineer / Repairer 不自我批准。

ai-dev-flow 不禁止 harness 或模型自动使用 subagents / 子代理，包括 ultra mode-like 的内部加速能力。subagents 是可选能力，不是默认依赖；不支持 subagents 的 agent 仍可按 Markdown、Git 和 TASK 文件流程稳定运行。

只读 subagents 默认适合审查、验证、状态分拣、文档检查、日志整理和测试结果整理。写代码 subagents 可以受控使用，但必须声明任务边界、修改范围和验证方式；多个写代码 subagents 并行默认需要用户确认、独立分支或 Worktree、文件锁 / 模块锁检查和逐任务 diff 审查。subagents 不得自动 merge、push、release 或 delete。

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

你不需要记住所有模式、角色和 Loop。日常使用时，先记住这四句话就够了：

```text
请使用 ai-dev-flow 初始化当前项目工作流。
```

```text
请使用 ai-dev-flow，把下面需求拆成任务：
<你的需求>
```

```text
请使用 ai-dev-flow，执行 TASK-001。
```

```text
请使用 ai-dev-flow，审查这个任务，并告诉我需要我做什么。
```

初始化后，推荐把精简规则写进项目 `AGENTS.md`。之后在同一个项目里，你可以直接说“拆这个需求”“执行下一个任务”“审查刚才的改动”，让 agent 按项目规则走。

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

v0.6.0 可选结构如下，适合需要 Intake、Loop、Memory 或项目硬规则的长期项目；这些目录不是初始化必需项：

```text
docs/
├── intake/
├── loops/
├── memory/
└── PROJECT_CONSTITUTION.md
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
- A 级文档 Batch 可以一个 commit。
- B 级小代码 Batch 推荐每个 TASK 单独 commit；不单独 commit 时必须记录 per-task diff 归属。
- 多个 B 级任务修改同一文件时，默认拆成单任务或等待用户确认。
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
- 进入 Parallel Wave 的代码任务默认使用独立分支或 Worktree。
- 多个代码执行会话不得默认共享同一工作区。
- Review Hub 可以集中审查 Wave，但必须逐任务输出结论。

## v0.6.0 Unreleased：设计级能力

v0.6.0 增加一组 Markdown-first 的设计级工作流指南：

- Intake：在拆任务前记录需求、成功标准、非目标、模糊点和可逆性。
- Loop Engineering：编排 triage、goal、review-repair、status loop，但 Loop 不替代 TASK 或任务状态。
- Review-Repair Loop：限制修复轮次，Reviewer 不直接修复，Engineer 不自我批准。
- Role Guide：区分 Orchestrator、Planner、Engineer、Reviewer、Verifier、Repairer 和 Archivist。
- Project Constitution：用 MUST / SHOULD / MUST NOT 记录项目硬规则。
- Memory：在 `docs/memory/` 下沉淀长期项目知识。
- GitHub Issues Optional Backend：只提供 TASK 到 Issue 的字段映射设计，不自动同步。
- Harness Compatibility：说明 Codex、Claude Code、Cursor、Gemini CLI、DeepSeek 和通用 agent 的能力边界。

这些能力是文档、模板、提示词和路线图，不表示当前版本具备自动脚本、自动 GitHub 同步、自动 subagent 调度、自动多 agent 调度、自动合并或自动发布。

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
0.5.2
```

`0.6.0` 当前作为 Unreleased 文档升级记录在 `skills/ai-dev-flow/CHANGELOG.md` 中。

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
