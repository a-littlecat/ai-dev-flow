# Tracked / Controlled TASK 模板

> Skill 包 `0.8.2` 开发线中，其他 Tracked 与全部 Controlled 任务使用本完整模板。Lite 的结果是 `DoNotUseSkill`，不创建 TASK；符合单会话条件的 Tracked 可改用 `TASK_TEMPLATE_BRIEF.md`。`adf/v0.7.0` Contract schema 保持兼容，不随 Skill 包版本变化。

```markdown
# <TASK-ID>：<任务标题>

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `<TASK-ID>`
- `task_type`: `<document|plan|code|review|repair|test>`
- `task_class`: `<A|B|C|D>`
- `lifecycle`: `<Draft|Ready|In Progress|Blocked|Review|Needs Fix|Accepted|Closed|Deferred|Cancelled>`
- `review_status`: `<Pending|In Review|Passed|Needs Fix|Do Not Merge>`
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

## Repair Chain Ledger（仅进入 repair 时填写）

- Repair chain：<repair_chain_id、finding_ids、closure_contract_hash、allowed_files_hash>
- Trigger Review 收据：<隔离/只读、chain/policy/finding 绑定、receipt_hash>
- Attempt 收据链：<AR-*/ER-*、patch hash、前一收据 hash、独立复审与 receipt_hash；计数由此推导>
- History anchor：<TASK 中的 attempt_count、head_receipt_hash、source_ref/source_text_sha256>
- Trusted context：<由 harness/当前对话/只读项目快照独立确认的 expected head/count 与 Review/authority receipt hashes>
- 第 3 轮 progress：<写入 AR-2 独立 Review 收据的 closure/blocking/severity/evidence before/after>
- Escalated authority：<用户消息来源、chain/scope/target、默认一次或显式 attempt IDs、receipt_hash>
- 非计数动作：<review/UA/诊断/测试重跑/收据同步/记录纠错>
- 机械判定：<MechanicallyEligible|Stop|Blocked>；eligible_mode：<AutoRepair|ExtendRound3|EscalatedRepair>
- Orchestrator 提升：<持有真实上游证据后记录 *Allowed；否则 Blocked>

## Outcome

- Base / Diff：<base..HEAD 或工作区范围>
- 修改文件：<路径和作用>
- 验证命令与结果：<命令、退出码、关键结果>
- Review findings：<稳定 ID、严重度、状态；或 Outcome 中记录 Skipped by policy，Contract 仍保持 Pending>
- UA 动作与结果：<等级、用户需做什么、Pending/Passed/Failed>
- 状态边界：<未执行或未授权的 commit/merge/release/Closed>
- 剩余风险：<无或明确列出>
- 下一步：<可执行动作或所需用户决定>
```

## 写回规则

- 执行者更新 Outcome、验证和实际状态，不自批 Review。
- `Skipped by policy` 不等于 `Passed`；没有真实只读 Review 时，`review_status` 保持 `Pending`。
- Reviewer 只写 review 状态与 findings，不修改业务代码。
- Repairer 只处理冻结 finding ID，并追加验证结果。
- 同一 finding / closure contract 的新 TASK 继承原 `repair_chain_id` 和计数；更换 TASK 或模型不重置。
- `Stop` 后用户可明确授权有界 `EscalatedRepair`；授权默认只消费一次，失败回到 `Stop`，不要求用户必须亲自写代码。
- `repair_gate.py` 把 ledger 视为不可信，只验证其与独立 trusted context 的结构/连续性；最终 Allowed 必须由持有真实上游证据的 Orchestrator 提升。
- TASK 先更新，TASK_BOARD 后同步；不得用看板反向覆盖 TASK。
- 旧 TASK 保持原格式，不为统一模板而批量迁移。
