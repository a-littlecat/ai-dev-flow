# Tracked / Controlled TASK 模板（v0.10）

> 其他 Tracked 与全部 Controlled 任务使用本完整模板。Lite 的结果是 `DoNotUseSkill`，不创建 TASK；符合任务形状条件的 Tracked 可用 `TASK_TEMPLATE_BRIEF.md`。模型名称不参与模板选择。旧 v0.7 TASK 保持原格式与语义，不批量迁移。

```markdown
# <TASK-ID>：<任务标题>

## Workflow Contract

- `schema_version`: `adf/v0.10.0`
- `task_id`: `<TASK-ID>`
- `task_type`: `<document|plan|code|review|repair|test>`
- `task_class`: `<A|B|C|D>`
- `lifecycle`: `<Draft|Ready|In Progress|Blocked|Review|Needs Fix|Accepted|Closed|Deferred|Cancelled>`
- `review_requirement`: `<Required|Not Required>`
- `review_status`: `<Not Run|In Review|Passed|Needs Fix|Blocked>`
- `ua_level`: `<UA0|UA1|UA2|UA3|UA4|UA5|UA6|UA7|TBD>`
- `ua_status`: `<Not Required|Pending|Passed|Failed|Deferred|TBD>`
- `commit_status`: `<Uncommitted|Committed|Not Applicable>`
- `merge_status`: `<Not Applicable|Unmerged|Merged|Deferred>`

## 目标与边界

- 目标：<可观察结果>
- 非目标：<明确不做什么>
- 允许修改：<文件/模块>
- 禁止修改：<文件/模块/动作>

## 依赖与授权

- 前置依赖：<无或 TASK/commit>
- Base commit：<hash>
- 已有 authority：<允许动作>
- 未授权动作：<merge/push/release/delete/external sync/Closed 等>
- 执行位置：<当前分支/独立分支/Worktree>

## 路由与风险

- 路由：<Tracked|Controlled>
- Policy 输入：<task class、UA、request action、risk flags、验证覆盖、用户观察/真实环境>
- Reviewer 闸门：<Skipped by policy|Triggered|Required|Blocked>
- 停止条件：<范围、权限、风险、证据或验证变化>

## 完成标准与验证

- [ ] <完成标准 1>：<验证命令/人工步骤/证据>
- [ ] <完成标准 2>：<验证命令/人工步骤/证据>
- [ ] `git diff --check` 通过，diff 可归属当前 TASK。

## Repair Ledger（仅进入 Repair 时填写）

- Stable finding：<finding_id、severity、closure contract>
- Attempt：<AR-1/AR-2/AR-3 或显式授权 attempt；patch 范围>
- RED / GREEN / SIGNAL：<修复前失败、修复后通过、证据来源>
- Review：<隔离/只读 Recipe、结论、finding 状态>
- Strict campaign：<Not Enabled | `REPAIR_CAMPAIGN.md` 要求的外部 receipt/ledger reference>

## Outcome

- Base / Diff：<base..HEAD 或工作区范围>
- 修改文件：<路径和作用>
- 验证证据：<命令、退出码、关键结果>
- Review findings：<稳定 ID、严重度、状态；Not Required + Not Run 且无自愿 Review 时写 none>
- UA 动作与结果：<等级、用户需做什么、Pending/Passed/Failed>
- 状态边界：<未执行或未授权的 commit/merge/release/Closed>
- 剩余风险：<无或明确列出>
- 下一步：<可执行动作或所需用户决定>
```

## 写回规则

- `review_requirement` 必须由 `policy/core.json` 路由结果派生，不得由执行者自由选择；Controlled 或命中 Tracked Review trigger 时必须为 `Required`。
- 执行者更新 Outcome、验证和实际状态，不自批 Review。
- `Not Required + Not Run` 不等于 `Passed`，只是当前完成门禁不强制 Review；`Required` 在 Accepted/Closed 前必须 `Passed`。
- 自愿 Review 的 `In Review / Needs Fix / Blocked` 是真实事实，必须处理，不能因 requirement 为 Not Required 而删除。
- Reviewer 只写 review 状态与 findings，不修改业务代码。
- Repairer 只处理冻结 finding ID，并追加验证结果。
- 同一 finding / closure contract 的新 TASK 继承原 `repair_chain_id` 和计数；更换 TASK 或模型不重置。
- 严格 receipt chain、trusted context、EscalatedRepair 与 Campaign 的完整结构只在 `REPAIR_CAMPAIGN.md` 维护；TASK 只保存引用，不复制协议。
- TASK 先更新，TASK_BOARD 后同步；不得用看板反向覆盖 TASK。
- 旧 TASK 保持原格式，不为统一模板而批量迁移。
