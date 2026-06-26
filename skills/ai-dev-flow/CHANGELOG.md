# Changelog

## 0.6.0 Unreleased

- Add Intake guide for requirement capture before task creation.
- Add Loop Engineering guide for triage, goal, review-repair, and status loops.
- Add Review Repair Loop guide with bounded repair rounds and escalation rules.
- Add Role Guide for Orchestrator, Planner, Engineer, Reviewer, Verifier, Repairer, and Archivist.
- Add Project Constitution template using MUST / SHOULD / MUST NOT rules.
- Add Memory Guide for durable project knowledge under docs/memory/.
- Add optional GitHub Issues backend design without automatic sync.
- Add Harness Compatibility guide for Codex, Claude Code, Cursor, Gemini CLI, DeepSeek, and generic agents.
- Add Loop State template for loop run summaries.
- Update prompts, task template, workflow, safety rules, and scripts roadmap.

## 0.5.2

- 强化 Parallel Wave 中代码任务的工作区隔离规则。
- 明确并行代码任务默认应使用独立分支或 Worktree。
- 强化 B 级小代码 Batch 的 per-task diff / commit 归属要求。
- 明确 Batch diff 无法按任务拆分时不得强行通过审查。

## 0.5.1

- 泛化开源文档中的具体技术示例。
- 移除偏项目化的宿主程序、嵌入式页面和外部软件名称示例。
- 保留 UA、Batch、Wave 等通用流程规则不变。

## 0.5.0

- 增加批量小任务 Batch 流程。
- 增加批量小任务执行规则。
- 增加批量小任务审查规则。
- 增加 `BATCH` 文件建议格式。
- 增加 Parallel Wave 任务并行流程。
- 增加 Batch 和 Wave 区分。
- 增加文件锁 / 模块锁。
- 增加并行任务准入规则。
- 增加 `WAVE` 文件建议格式。
- 增加 Review Hub 审查 Batch / Wave 的规则。
- 明确 A/B 小任务可批量，C/D 任务默认单独。
- 明确批量执行不是多任务并行写代码。
- 明确并行执行必须用户确认。
- 明确 D 级和 UA5 / UA6 / UA7 任务默认不得进入代码并行。
- 明确 Batch / Wave 审查必须逐任务输出结论。

## 0.4.1

- 明确 UA0 任务默认不自动标记为 `Closed`。
- UA0 任务完成后 agent 只能建议关闭，除非用户明确确认或项目规则已授权。
- 将“无需用户验收”和“允许关闭任务”拆开表达，避免 agent 跳过关闭确认。

## 0.4.0

- 增加用户动作等级 UA0~UA7。
- 明确人工验收不等于人工代码审查。
- 增加是否需要用户实机测试字段。
- 增加验收建议输出格式。
- 明确哪些任务无需用户验收，哪些需要文档验收、证据验收、本地运行、实机业务测试、回归验收或用户决策。

## 0.3.0

- 增加 Git baseline 规则。
- 增加 Git precheck。
- 增加 A/B/C/D 任务分级。
- 增加分支 / Worktree 使用规则。
- 增加 pre-commit diff review 和 post-commit diff review。
- 增加 base commit 记录要求。
- 增加不得盲目 `git add .` 规则。
- 修正 `execute_task` / `review_task` 默认参考文件。
- 修正执行任务提示词，避免小任务被机械升级为分支或 Worktree 任务。

## 0.2.0

- 增加使用模式。
- 增加任务状态机。
- 增加停止条件和权限分级。
- 增加验证指南。
- 增加任务膨胀处理。
- 增加并发冲突规则。
- 增加项目适配模板。
- 增加审查严重等级。
- 增加交接摘要。
