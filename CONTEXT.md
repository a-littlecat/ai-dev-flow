# ai-dev-flow 项目上下文

> 本文件记录项目当前事实、稳定术语和架构硬约束。它不是发布说明，也不会让 Draft RFC 自动生效。

## 项目目的

`ai-dev-flow` 是面向单人开发者和 AI 编码代理的 Git-first、Markdown-first 开发工作流。它通过 Skill、提示词、模板和参考文档，帮助使用者完成需求摄入、任务规划、受控执行、验证、审查、用户验收与交付收口。

项目的核心价值不是替代项目管理系统，而是让人和不同 harness 中的 agent 对同一份任务边界、状态和证据形成可审计共识。

## 当前真相源

- 仓库内 `skills/ai-dev-flow/` 是 Skill 的开发源；安装到各 harness 的副本属于分发产物，不是反向真相源。
- 在使用本工作流的项目中，TASK 文件是细粒度任务事实源。
- `TASK_BOARD.md` 是任务索引和状态投影；发生冲突时不能覆盖 TASK，也不能静默猜测。
- `STATUS_MACHINE.md` 定义当前 lifecycle 状态与合法流转。
- Review、验证、用户验收和 delivery 是不同维度；任何一个维度的“通过”都不能代替其他维度。
- `docs/plans/` 中的 RFC 即使获批，也只代表方向和任务拆分被确认；只有后续实现、验证并完成相应发布后才成为生效行为。

## 稳定术语

| 术语 | 含义 | 当前地位 |
|---|---|---|
| TASK | 保存单个任务边界、状态、证据和结论的 Markdown 文件 | 已建立 |
| TASK_BOARD | TASK 的索引与投影视图 | 已建立 |
| lifecycle | `Draft` 到 `Closed` 等任务生命周期状态 | 已建立 |
| Review | 独立于 lifecycle 的审查状态和 findings | 已建立，当前存在重复表达 |
| UA | `UA0`–`UA7` 用户动作/验收等级及其结果 | 已建立 |
| RED / GREEN / SIGNAL | 失败信号、通过信号和证据来源 | 已建立 |
| Workflow Contract Module | 归一化 TASK、校验不变量并生成只读报告的深模块 | v0.7 方案已批准，未实现 |
| Contract Interface | 人、agent、校验器和投影 Adapter 共同读取的稳定语义入口 | v0.7 方案已批准，未实现 |
| Overlay | 只在复杂路径触发时增加的约束层，不重定义核心状态 | v0.7 后续范围，未实现 |
| Adapter | 在 Markdown 版本、输出格式或外部系统边界做转换的实现 | v0.7 方案已批准，未实现 |

## 架构硬约束

- 保持 Markdown-first；不要求数据库、守护进程、网络 API 或专用项目管理平台。
- 保持 agent-agnostic；Codex、Claude、Gemini 或其他 harness 只能改变执行能力，不能改变工作流语义。
- 核心规则必须在无 GPT‑5.6、无联网、无 subagent 时仍可执行和验证。
- 模型、Structured Outputs、工具调用和多 agent 只能作为可选 Adapter 或能力 Profile。
- `Can`（具备能力）、`May`（拥有权限）和 `Should`（风险判断）必须分开；Harness Profile 不能授予 merge、push、release 或写入权限。
- 校验器默认只读，只报告缺失、冲突、漂移和违规，不自动改写 TASK、TASK_BOARD 或 Git。
- 新版本采用兼容读取、单一写入；旧 TASK 不批量重写，冲突字段不猜测。
- 验证通过不等于 Review 通过，Review 通过不等于 UA 通过，已 merge 不等于 Accepted 或 Closed。
- 外部写入、危险操作和用户验收必须保留明确授权边界。

## 当前已知张力

- `VERSION` 仍为 `0.5.2`，而 `CHANGELOG.md` 和 README 已包含 `0.6.0 Unreleased` 能力，发布身份尚未收口。
- `TASK_TEMPLATE.md` 同时保存“代码审查 / Diff 审查”以及两组合并状态，容易形成重复真相。
- `TASK_BOARD_TEMPLATE.md` 一方面声明只保留索引和状态，另一方面提供约 30 列完整视图，人工维护成本较高。
- 当前没有确定性的 Contract validator 和回归 fixture；规则一致性主要依赖 agent 阅读长文档。
- 不同 harness 的安装副本可能与仓库源发生版本漂移，需要分发校验，但分发问题不应污染核心 Contract。

## 当前架构方向

v0.7 已批准按一个深的 `Workflow Contract Module` 推进：用单一语义入口读取 TASK、保守兼容旧格式、校验状态不变量，并把 TASK_BOARD 作为只读投影进行对照。正式任务已排期，但尚未开始实现；第一阶段不实现状态写入器、通用插件系统或自动外部同步。

详见 `docs/plans/V0.7_WORKFLOW_CONTRACT_RFC.md`。
