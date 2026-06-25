# 任务看板模板

> 使用方式：复制到 `docs/TASK_BOARD.md`，按项目需要增删字段。任务详情放在 `docs/tasks/`，看板只保留索引和状态。

## 状态说明

- `Draft`：草稿，需求或边界尚未确认。
- `Ready`：可以执行，目标、非目标、完成标准和验证方式已明确。
- `In Progress`：执行中。
- `Blocked`：被阻塞，需要信息、权限、依赖或用户确认。
- `Review`：等待审查。
- `Needs Fix`：审查后需要修复。
- `Accepted`：按用户动作等级完成必要验收或决策，结果可接受。
- `Closed`：已关闭。关闭动作已由用户确认或项目规则授权；UA0 默认也只能建议关闭。
- `Deferred`：延期。
- `Cancelled`：取消。

## 轻量看板推荐字段

日常维护建议只保留：

| 任务编号 | 任务名称 | 等级 | 状态 | 批次 | Wave | 可批量 | 可并行 | 执行位置 | Review 状态 | UA 等级 | 是否需实机 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TASK-000 | 示例任务 | A / B / C / D | Draft / Ready / In Progress / Blocked / Review / Needs Fix / Accepted / Closed / Deferred / Cancelled | BATCH-000 / 无 | WAVE-000 / 无 | 是 / 否 / 待确认 | 是 / 否 / 待确认 | 主项目 / Worktree / 分支 | 未审查 | UA0 / UA1 / UA2 / UA3 / UA4 / UA5 / UA6 / UA7 / 待确认 | 是 / 否 / 待确认 | 任务文件：`docs/tasks/TASK-000.md` |

如果看板过宽，`批次`、`Wave`、`可批量`、`可并行`、`锁定模块` 均为可选字段。详细批次信息写入 `docs/batches/BATCH-xxx.md` 或任务文件；详细并行信息写入 `docs/waves/WAVE-xxx.md` 或任务文件。

详细信息应放入对应任务文件，例如：

- 分支
- Base commit
- 当前 HEAD
- Diff 范围
- Worktree
- Commit 状态
- Merge 状态
- 验证记录
- 审查结论
- 具体用户动作
- 不验收的风险
- 批次 / Wave
- 可批量 / 可并行
- 锁定模块

## 完整看板模板

| 任务编号 | 任务名称 | 模式 | 任务类型 | 等级 | 状态 | 优先级 | 风险等级 | 批次 | Wave | 可批量 | 可并行 | 锁定模块 | 执行位置 | 分支 | Base commit | 当前 HEAD | Diff 范围 | Worktree | 依赖 | 冲突 | Review 状态 | 验收状态 | 关闭状态 | Commit 状态 | Merge 状态 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TASK-000 | 示例任务 | execute_task | 文档 / 方案 / 代码 / 审查 / 修复 / 测试 | A / B / C / D | Draft / Ready / In Progress / Blocked / Review / Needs Fix / Accepted / Closed / Deferred / Cancelled | 高 / 中 / 低 / 待确认 | 低 / 中 / 高 | BATCH-000 / 无 | WAVE-000 / 无 | 是 / 否 / 待确认 | 是 / 否 / 待确认 | 待填写 | 主项目 / Worktree / 分支 | main | 待填写 | 待填写 | 待填写 | 不适用 | 无 | 无 | 未审查 | 未验收 | 未关闭 | 未提交 | 不适用 | 任务文件：`docs/tasks/TASK-000.md` |

## 字段说明

| 字段 | 说明 |
| --- | --- |
| 任务编号 | 稳定编号，例如 `TASK-001`。 |
| 任务名称 | 简短标题。 |
| 模式 | init_project、create_task、plan_task、execute_task、review_task、repair_task、close_task 或 status_report。 |
| 任务类型 | 文档、方案、代码、审查、修复或测试。 |
| 等级 | A 文档小任务、B 小代码任务、C 中等代码任务、D 大任务或高风险任务。 |
| 状态 | 使用上方状态说明。 |
| 优先级 | 高、中、低或待确认；只用于排期，不使用 P0/P1/P2/P3。 |
| 风险等级 | 低、中、高或待确认。 |
| 批次 | 所属 `BATCH-xxx`；无批次写“无”。 |
| Wave | 所属 `WAVE-xxx`；无并行波次写“无”。 |
| 可批量 | 是否允许进入 Batch。C/D 默认否。 |
| 可并行 | 是否允许进入 Parallel Wave；并行必须先做冲突检查并获得用户确认。 |
| 锁定模块 | 并行时预计影响模块或锁定模块；不适用时写“不适用”。 |
| 执行位置 | 主项目、Worktree 或分支。 |
| 分支 | 当前任务使用的分支；不使用分支时写当前主分支。 |
| Base commit | 任务开始前记录的 commit。 |
| 当前 HEAD | 当前执行位置的 HEAD。 |
| Diff 范围 | pre-commit diff 或 `<base_commit>..HEAD`。 |
| Worktree | Worktree 路径；不适用时写“不适用”。 |
| 依赖 | 前置任务或外部依赖。 |
| 冲突 | 与当前任务冲突的任务编号；无冲突写“无”。 |
| Review 状态 | 未审查、审查中、通过、需要修改、不建议合并。 |
| 验收状态 | 简短写用户动作等级或结果，例如 UA0、UA3、UA5、通过、未通过、暂缓；具体用户动作写入任务文件。 |
| 关闭状态 | 未关闭、可关闭、已关闭、暂缓关闭。 |
| Commit 状态 | 未提交、已提交、不适用。 |
| Merge 状态 | 不适用、未合并、用户已确认待合并、已合并、暂不合并。 |
| 备注 | 任务文件路径、风险或其他简短说明。 |
