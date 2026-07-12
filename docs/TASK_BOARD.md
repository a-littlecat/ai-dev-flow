# ai-dev-flow 任务看板

> - 快照日期：2026-07-12
> - 当前模式：`CONTRACT-004` 第 1 轮修复完成，等待独立复审
> - 当前阶段：24/24 GREEN；复审与 UA4 前不启动 Writer
> - 方案来源：`docs/plans/V0.7_WORKFLOW_CONTRACT_RFC.md`

## 本轮授权边界

用户于 2026-07-11 明确要求“完成 CONTRACT-001~006”，授权按既定串行依赖逐项进入执行、验证、独立 Review 和对应 UA 门禁，并允许为任务建立必要的独立分支 / Worktree 与可追溯 commit。

本轮仍不授权：

- merge、push、发布版本或同步本机 Skill 副本。
- 创建或删除 Git tag、GitHub Release。
- 跳过前置 Accepted、独立 Review 或任务规定的用户动作等级。

任务必须保持逐项可审查 diff；后继任务只有在前置任务满足 Accepted 与祖先关系门禁后才能开始。

## 真相源与状态规则

- 任务详情、边界、验证和验收要求以对应 TASK 文件为细粒度真相源。
- 本看板只保留索引、当前状态和依赖，不复制完整完成门禁。
- TASK 与看板不一致时，先停止状态推进并复核，不静默选择一边。
- Review、UA、Commit、Merge 和 lifecycle 是不同维度；任何一项通过都不自动代表其他项通过。
- 后置任务先保持 `Draft`，待前置任务达到 `Accepted` 且形成可引用 Git baseline 后，按合法流转 `Draft -> Ready`。
- `CONTRACT-005` Accepted 前，本任务集继续使用当前 legacy TASK 记录区块；不得提前用尚未启用的 Compact Writer 自举。
- `Accepted` 不等于前置 commit 已进入后继分支。每个后继任务转为 `Ready` 前，必须用 `git merge-base --is-ancestor <前置 Accepted commit> <当前 Base>` 证明当前 Base 包含前置结果。
- 任务之间可以从前置 Accepted commit 顺序分支，不要求为了传递依赖而提前 merge；任何实际 merge 仍需独立 UA7 用户确认。

## 全局执行前置门禁

在任何任务进入 `In Progress` 前必须满足：

1. 本轮新增的 RFC、CONTEXT、TASK_BOARD 和 TASK 文件已形成清晰 Git baseline。
2. `git status --short` 中没有来源不明或与目标任务无关的改动。
3. 任务文件已更新当前分支、Base commit、HEAD 和 Diff 范围。
4. 后继任务已证明当前 Base 是所有前置 Accepted commit 的 descendant。
5. C/D 任务已按任务文件建立独立分支或 Worktree；没有用户确认时不得启动代码并行。
6. 每个任务单独执行、验证、Review 和 UA，不允许只做一次总 Review 或总验收。

## 串行依赖链

```text
REL-001
  -> CONTRACT-001
  -> CONTRACT-002
  -> CONTRACT-003
  -> CONTRACT-004
  -> CONTRACT-005
  -> CONTRACT-006
```

- 整条链严格串行，不建立 Batch 或 Parallel Wave。
- `CONTRACT-006` 显式依赖 `CONTRACT-004` 和 `CONTRACT-005`；图中因 `005 -> 004` 已隐含前一依赖而简化显示。
- `CONTRACT-007` 及以后不属于本轮任务集。

## 当前任务

| 任务 | 名称 | 等级 | 状态 | 优先级 | 风险 | 前置依赖 | Review | UA | 执行组织 | 任务文件 |
|---|---|---|---|---|---|---|---|---|---|---|
| REL-001 | 收口 v0.6 发布身份 | B | Accepted | 高 | 高 | 无 | 通过 / 无 P0-P3 | UA7 已通过 | Single / 独立分支 | [REL-001](tasks/REL-001-close-v06-release-identity.md) |
| CONTRACT-001 | 固化 Workflow Contract 语义规范 | C | Accepted | 高 | 高 | REL-001 Accepted baseline `752b11f` | 通过 / 无 P0-P3 | UA2 已通过 | Single / 独立分支 `codex/contract-001-semantics` | [CONTRACT-001](tasks/CONTRACT-001-workflow-contract-semantics.md) |
| CONTRACT-002 | 建立 Golden fixtures 与填写量基线 | C | Accepted | 高 | 中 | CONTRACT-001 Accepted `28e74f8` | 通过 / 无 P0-P1（1 类 P2 不阻塞） | UA3 已通过 | Single / 独立分支 `codex/contract-002-golden-fixtures` | [CONTRACT-002](tasks/CONTRACT-002-golden-fixtures.md) |
| CONTRACT-003 | 实现 Legacy / v0.7 只读 Reader | C | Accepted | 高 | 高 | CONTRACT-002 Accepted `f7d870d` | 通过 / 无 P0-P1（1 项 P2） | UA3 已通过 | Single / 独立分支 `codex/contract-003-readonly-readers` | [CONTRACT-003](tasks/CONTRACT-003-readonly-contract-readers.md) |
| CONTRACT-004 | 实现只读 workflow_lint | C | Review | 高 | 高 | CONTRACT-003 Accepted `95ec566` | 第 2 / 2 轮修复完成，待最终复审 | UA4 未进入 | Single / 独立分支 `codex/contract-004-workflow-lint` | [CONTRACT-004](tasks/CONTRACT-004-workflow-lint-cli.md) |
| CONTRACT-005 | 启用 Compact Template 与最小 Writer 路由 | D | Draft | 中 | 高 | CONTRACT-004 Accepted | 未审查 | UA6 | Single / 必须 Worktree | [CONTRACT-005](tasks/CONTRACT-005-compact-template-writer-routing.md) |
| CONTRACT-006 | 增加 TASK_BOARD 只读投影与 drift 检查 | C | Draft | 中 | 高 | CONTRACT-004、005 Accepted | 未审查 | UA6 | Single / 独立分支或 Worktree | [CONTRACT-006](tasks/CONTRACT-006-task-board-projection.md) |

## 下一允许动作

`CONTRACT-003` 已完成两轮有限修复、最终独立复审和 UA3，任务进入 Accepted。形成 Accepted commit 并验证为后继 Base 祖先后允许启动 `CONTRACT-004`；当前仍不允许 merge 或 push。

## 整体停止条件

- v0.6 发布身份仍无法形成单一结论。
- 任一任务要求新增大型依赖、数据库、守护进程、通用插件运行时或外部双向同步。
- Markdown Contract 无法在标准库优先的约束下稳定解析。
- Legacy Reader 需要猜测冲突才能继续。
- Compact Template 会让 C/D、Batch、Wave 或 `real_env_signal` 在 `CONTRACT-007` 前被误路由。
- TASK_BOARD projection 需要写回文件、`--fix` 或以看板覆盖 TASK。
- GPT‑5.6 或任一模型能力变成核心流程必需依赖。

出现上述情况时：尚未启动的 Draft 保持 Draft；Ready、In Progress、Review 仅按状态机允许路径进入 Blocked；已经 Blocked 的任务保持 Blocked；其他状态停止并等待合法流转决定。不得把执行中的任务退回 Draft。
