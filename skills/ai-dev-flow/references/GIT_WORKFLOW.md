# Git 工作流

Git 在本 Skill 中不是形式化流程，而是任务边界和审查证据的基础。目标是轻量、可追踪、可回滚。

## Git 的作用

- 建立项目基线。
- 支持 diff 审查。
- 隔离任务。
- 支持回滚。
- 支持合并前确认。

## 基本原则

- Git 是必须的，因为没有 Git 就无法稳定 diff 审查。
- 分支不是所有任务都必须使用。
- Worktree 只用于中大型或高风险任务。
- 小任务的关键不是建分支，而是保持 diff 清晰、可回滚、可审查。
- A/B 小任务可以进入 Batch，但必须保持 diff 可按任务拆分。
- Parallel Wave 必须在用户确认后启动，并为每个任务保留独立 base commit、HEAD 和 diff 范围。
- 不得盲目执行 `git add .`。
- 不得自动 merge。
- 不得自动执行破坏性 Git 操作。

## 任务分级

### A 级：文档小任务

示例：

- 更新 `TASK_BOARD`。
- 补任务说明。
- 改 README。
- 整理 `DECISIONS`。
- 更新提示词。

规则：

- 不需要分支。
- 可在主项目直接执行。
- 需要 `git diff` 自查。
- 完成后 commit。
- Merge 状态通常为“不适用”。
- 可进入 A 级文档 Batch；并行时不得和其他任务修改同一核心文档。

### B 级：小代码任务

示例：

- 修文案。
- 改局部样式。
- 补小的空值判断。
- 改一个局部命名。
- 小范围 bug 修复。

规则：

- 不强制分支。
- 可在主项目直接执行。
- 必须记录 base commit。
- 必须审查 `git diff`。
- 改动应少于少量文件。
- 不得涉及架构、核心流程、构建、通信协议。
- 通过自查后 commit。
- Merge 状态通常为“不适用”。
- 可谨慎进入 B 级小代码 Batch 或低风险 Wave；前提是文件不重叠、模块不冲突、diff 可拆分。

### C 级：中等代码任务

示例：

- 新增小功能。
- 修改模块内部流程。
- 调整多个文件。
- 修改接口或数据结构。
- 影响 UI 状态流或业务服务。

规则：

- 建议使用独立分支。
- 分支名建议 `feature/TASK-xxx-short-name` 或 `fix/TASK-xxx-short-name`。
- 记录 base commit。
- 基于 base commit 到 HEAD 做 diff 审查。
- 审查通过后再给出用户动作等级和验收建议。
- 未经用户确认不得合并。
- 默认单独执行；如需和其他代码任务并行，必须使用独立 Worktree、文件不重叠、模块不冲突，并获得用户确认。

### D 级：大任务 / 高风险任务

示例：

- 架构迁移。
- 技术栈迁移。
- 重构。
- 新建子项目。
- 改核心业务流程。
- 改通信机制。
- 改构建或部署流程。

规则：

- 必须使用独立分支或 Worktree。
- 优先 Worktree。
- Worktree 不应放在主项目内部。
- 创建 Worktree 前，主项目中的任务文件和规则应先提交。
- 必须进行独立代码审查。
- 未经用户确认不得合并。
- 默认不得进入 Batch 或代码并行。

## 执行位置选择

| 等级 | 推荐执行位置 | 分支 | Worktree | 审查方式 |
| --- | --- | --- | --- | --- |
| A | 主项目 | 不需要 | 不需要 | pre-commit diff |
| B | 主项目或分支 | 不强制 | 不需要 | pre-commit diff |
| C | 独立分支 | 建议 | 可选 | post-commit diff |
| D | Worktree 或独立分支 | 必须 | 建议/必须 | post-commit diff |

## Batch / Wave Git 规则

- Batch 不等于一个大任务；每个 TASK 仍要记录 base commit、diff 范围和验证结果。
- Wave 不等于共享工作区；每个并行任务应有清晰执行位置，必要时使用独立分支或 Worktree。
- 不得让多个任务共享一个无法拆分的 diff。
- 不得在来源不明的脏工作区启动 Batch 或 Wave。
- Review Hub 审查 Batch / Wave 时，必须逐任务审查 diff。

## Commit 规则

- Commit 前先查看 `git status --short`。
- Commit 前先查看 `git diff --name-only` 和 `git diff --check`。
- 不得盲目执行 `git add .`。
- 优先按文件精确暂存，例如 `git add <file1> <file2>`。
- 如果存在不属于当前任务的改动，不得混入本任务 commit。

## 合并规则

- 未通过审查不得建议合并。
- 未完成用户动作等级对应的验收或决策，不得建议合并。
- 未经用户确认不得自动 merge。
- 工作区混乱、diff 范围不清、base commit 缺失时不得建议合并。
