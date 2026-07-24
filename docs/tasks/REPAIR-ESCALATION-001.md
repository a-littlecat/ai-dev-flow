# REPAIR-ESCALATION-001：实现用户授权的超限修复通道

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `REPAIR-ESCALATION-001`
- `task_type`: `code`
- `task_class`: `D`
- `lifecycle`: `Accepted`
- `review_status`: `Passed`
- `ua_level`: `UA2`
- `ua_status`: `Passed`
- `ua_evidence`: `#outcome`
- `acceptance_authority`: `User Confirmed`
- `commit_status`: `Uncommitted`
- `merge_status`: `Unmerged`

## 目标与边界

- 目标：实现可机械验证的 repair chain 计数和用户授权 `EscalatedRepair` 通道。
- 非目标：不取消自主上限，不放松不可逆副作用硬门禁，不修改冻结证据或 CADCat 业务代码。
- 允许修改：本任务计划明确列出的 Skill、测试、说明、任务记录，以及 Review 通过后的现有安装副本/CADCat 冲突规则。
- 禁止修改：冻结 v0.8 原型/评估、历史 TASK、依赖/技术栈、业务实现，以及未授权 delivery 动作。
- 目标（用户明确需求）：修复修改轮数边界含混、换 TASK 重置预算，以及 repair 超限后即使用户授权也拒绝 AI 继续修复的问题。
- 目标（Codex 默认假设）：每次超限后的用户明确授权默认只允许一个有界 `EscalatedRepair` 尝试；用户也可明确授权有限的 N 次。
- 非目标：不取消自动修复上限；不允许无限循环；不自动重试不可逆外部副作用；不修改冻结 v0.8 原型/评估证据；不实施 CADCat 业务修复。
- 允许修改：本任务计划列出的 Skill 入口、policy、按需 references、模板、只读脚本、测试、版本/说明文档、本 TASK/计划/看板；独立 Review 通过后同步已存在的本机 Skill 副本和 CADCat 中直接冲突的流程规则。
- 禁止修改：`evaluations/v0.8/**`、`skills/ai-dev-flow/prototypes/v0.8-lite/**`、历史 TASK、依赖/技术栈、CADCat 业务代码。

## 依赖与授权

- 前置依赖：`SYNC-001` 已完成源同步；本任务 base=`070267326146924f3e05a94b67c16825bc1777de`。
- Base commit：`070267326146924f3e05a94b67c16825bc1777de`
- 已有 authority：用户于 2026-07-24 在审阅复盘与推荐方案后明确回复“可以，实施吧”；允许源 Skill 实施、验证、独立 Review，以及按已说明计划同步现有本机 Skill 副本和 CADCat 流程规则。
- 验收与交付 authority：用户于 2026-07-24 明确回复“验收通过，提交并推送”；UA2 记为 Passed，并授权精确 commit 当前任务 diff、推送 `codex/repair-escalation-001` 分支。
- 未授权动作：merge、tag、Release、删除、历史改写、`Closed`。
- 执行位置：独立 Worktree `D:\open-source\ai-dev-flow-wt\repair-escalation-001`；分支 `codex/repair-escalation-001`。

## 路由与风险

- 路由：`Controlled`
- Policy 输入：D 级；核心治理策略、共享 Skill、外部本机同步；确定性测试可覆盖 policy，但最终工作习惯判断需要 UA2。
- Reviewer 闸门：Required；本机同步前必须完成隔离、只读 Review。
- 停止条件：P0/P1 未关闭；升级通道可无限重复；外部副作用硬门禁被削弱；冻结原型/评估发生变化；同步目标存在无法归属的差异。

## Repair Chain Ledger

- `repair_chain_id`: `adf-repair-policy-user-escalation`
- `finding_ids`: `ADF-ROUND-BOUNDARY`、`ADF-TASK-RESET`、`ADF-POST-STOP-AUTH`
- `closure_contract_hash`: `093fe917d8446a6d37a00be0b40511b7d14b116ae7e32330adeb78e806f97f2`
- `allowed_files_hash`: `6cc9e20ecb1f56012ecd3c380bff55b05b88648c5a9cfe0147ca5cabff2a77bf`
- `chain_history_verified`: `true`（Trigger Review 与 AR-1 已记录；计数不因 TASK/模型变化清零）
- `auto_attempts_used`: `3`（AR-3 patch 与验证完成；自主 repair 预算已用尽）
- `escalated_attempts_authorized`: `0`
- `escalated_attempts_used`: `0`
- 当前模式：`review_task`

## AR-1 修复输入

- 本轮假设：P1 根因是 evaluator 把调用方结论当事实；改为验证结构化 trigger/review/attempt 收据并从连续历史推导计数，可关闭三个绕过路径。
- 证据：独立只读 Review `Needs Fix`，`REPAIR-ESC-001`～`003` 为 P1，`REPAIR-ESC-004`～`005` 为 P2。
- 拟修改文件：`CORE.md`、`repair_gate.py`、两份专项测试、TASK/模板/工作流说明；不修改冻结原型/评估和 CADCat。
- 验证方式：新增伪报计数、历史缺口/重复/身份变化、结构化 progress、授权跨 chain、缺复审 ER-2、默认一次、异常 policy JSON/exit-code 测试；运行全套 unittest、validator、lint、冻结目录和 diff hygiene，再回到隔离只读 Review。

## AR-2 修复输入

- 本轮假设：P1 根因是 ledger 同时承担“事实”和“证明事实”，且脚本把结构合格直接写成最终 Allowed；分离 trusted context 与 ledger，并把脚本输出降为 `MechanicallyEligible`，可关闭自证循环。
- 证据：AR-1 独立只读复审 `Needs Fix`；`AR1-REV-001` 外部历史锚缺失、`AR1-REV-002` authority/reviewer 上游真实性未进入门禁（P1），`AR1-REV-003` policy schema guard 不完整（P2）。
- 拟修改文件：`CORE.md`、`repair_gate.py`、两份专项测试、模板/工作流/脚本说明和 TASK；不扩大到业务代码、冻结证据或本机同步。
- 验证方式：新增“历史与内部 anchor 同时截断但 external expected head 不变”“缺 trusted context”“未 attested Review/authority”“脚本永不直接返回 Allowed”“严格 policy 嵌套冲突”测试；全套验证后再独立复审。

## AR-3 Progress Gate 与修复输入

- Gate 事实：依赖/authority/根因/Reviewer/Repairer/成本边界冻结；无外部副作用；repair chain、finding 和允许文件范围未变。
- Target progress：AR-2 已关闭 `AR1-REV-001`；开放 P1 从 2 降至 1；无新 P0/P1；测试覆盖从 62 增至 65。
- 无回归：历史截断、缺 context、未 attested Review、最终 Allowed 分层、默认一次、ER2 复审和外部副作用硬门禁均保持 GREEN。
- Evidence coverage：新增 external head/count、未 attested review/authority、policy 嵌套 conflict 测试；`evidence_coverage_increased=true`。
- AR-3 单一目标：关闭 `AR1-REV-002`（候选 authority 未 attested 必须 Blocked），并收口同范围 P2 `AR1-REV-003` / `AR2-REV-001`。
- 决策：`ExtendRound3`；3 是自主 loop 绝对上限，AR-3 后无论结果均不得自动再修。
- 拟修改文件：`repair_gate.py`、`test_repair_gate.py`、计划/TASK/看板；必要的 CORE/测试说明仅做一致性收口。
- 验证方式：新增候选 authority 未 attested→Blocked、固定 2/3/1、未知字段、计划机械资格文案测试；全套验证和独立复审。

## 完成标准与验证

- 完成标准：policy、只读判定器、文档、测试、独立 Review 和获准同步全部满足本节检查项。
- 验证命令或检查：59 项以上 unittest、target/project lint、Skill validator、链接/版本/冻结目录/diff hygiene、独立只读 Review、逐文件 SHA256。
- [x] `3` 被定义为自主 `AutoRepair` 上限，不再被解释成用户授权后 AI 也不得编码。
- [x] 修复轮次、chain identity、非计数动作和换 TASK/模型不重置语义明确且一致。
- [x] 用户裁决可授权有界 `EscalatedRepair`；默认 1 次，失败返回 `Stop`，外部副作用保持阻断。
- [x] 第 3 轮以单 finding closure/progress 判定，不依赖原始 P0/P1 总数必须严格下降。
- [x] 只读判定器与测试覆盖上述边界，全部验证通过。
- [x] 独立只读 Review 无开放 P0/P1 后，现有本机 Skill 副本和 CADCat 直接冲突规则同步并验证一致。
- [x] `git diff --check` 通过，diff 可归属当前 TASK；冻结原型和评估证据零 diff。

## Outcome

- Base / Diff：base=070267326146924f3e05a94b67c16825bc1777de;diff=working-tree-ar3
- 隔离位置：Worktree `D:\open-source\ai-dev-flow-wt\repair-escalation-001`；branch `codex/repair-escalation-001`。
- 回滚方式：恢复本任务未提交 diff；同步后按同步前 SHA256 清单从源版本回填，不使用破坏性 reset。
- 修改文件：两文件运行时 policy、repair gate/测试、模板和按需指南、0.8.2 版本说明、本 TASK/计划/看板；共 25 个当前任务文件。
- 验证证据：AR-3 后 66 / 66 unittest 通过；31 项 repair/运行时针对性测试通过；Skill quick validator 通过；policy digest=`12bdbb91da0f6ca160e0afea76aceb4f7f423aa3c77ebf9ce379f2c7342c8083`；默认运行时 375 行；冻结 prototype/evaluation 零 diff；`git diff --check` 通过。现有 `.agents`、Codex、OpenCode、cc-switch 四个副本均为 0.8.2、92 / 92 文件、SHA256 `Missing=0 / Extra=0 / Changed=0`，四处 validator 通过；不存在的 Trae 目标未创建。
- 验证命令与结果：针对性 unittest exit 0；全套 unittest exit 0；quick validator exit 0；repair gate digest exit 0；冻结目录 diff exit 0；diff check exit 0；当前 TASK targeted lint 为 0 error / 0 violation，仅因未提交历史产生 `W_TRANSITION_UNVERIFIABLE`。CADCat `DOC-020` 定向 lint 为 0 error / 0 violation、业务路径 diff=0、版本/语义/敏感信息/diff 检查通过。
- Review findings：AR-3 隔离只读复审 `Passed`，P0/P1/P2/P3=`0/0/0/0`；`AR1-REV-002`、`AR1-REV-003`、`AR2-REV-001` 全部 Closed，新 finding 为 0。Reviewer 未在只读沙箱重跑 Python，但静态核对完整 base..working-tree（含 4 个 untracked 文件）、冻结目录 diff，并确认审查前后 Git 状态一致。
- CADCat 同步 Review：`DOC-020` 隔离只读 Review `Passed`，P0/P1/P2/P3=`0/0/0/0`；确认不会继续拒绝有效的 chain-bound AI 授权，也不会让策略升级自动恢复现有 PLOT Stop chain。
- UA 动作与结果：UA2 Passed；用户于 2026-07-24 明确回复“验收通过，提交并推送”。
- 状态边界：Accepted / Uncommitted / Unmerged / Unreleased / Not Closed；当前仅取得精确 commit 与分支 push 授权，未取得 merge、tag、Release 或 Closed 授权。
- 剩余风险：receipt 可机械验证结构、连续性和绑定，但不能密码学证明平台用户身份；授权主体真实性仍依赖当前对话、harness 或项目事实源，缺少时必须 Blocked。
- 下一步：执行精确 commit 与 `codex/repair-escalation-001` 分支 push，并写回 Git 收据；不执行 merge、tag、Release、delivery 或 Closed。
