# REPAIR-CAMPAIGN-001：实现任务级连续修复授权

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `REPAIR-CAMPAIGN-001`
- `task_type`: `code`
- `task_class`: `D`
- `lifecycle`: `Accepted`
- `review_status`: `Passed`
- `ua_level`: `UA2`
- `ua_status`: `Passed`
- `ua_evidence`: `#outcome`
- `acceptance_authority`: `User Confirmed`
- `commit_status`: `Committed`
- `merge_status`: `Unmerged`

## 目标与边界

- 目标：在保留安全硬门禁和独立 Review 的前提下，让同一 TASK、验收合同和模块范围内的连续诊断与修复不再逐 attempt 打断用户。
- 目标（用户明确需求）：核心产品代码连续 4 次无实质进展才停止；测试工具 / Harness 连续 5 次无实质进展才停止。
- 目标（用户补充需求）：当前 Harness 必须默认调用自身原生、隔离、只读 Reviewer；Kimi Code 使用 Kimi 原生 `Agent` Reviewer，不得自动调用 Codex、Claude、OpenCode 或其他外部 Harness，除非用户明确指定。
- 非目标：不提供无限修复；不放宽测试标准；不把 campaign authority 扩大为 delivery、Accepted 或 Closed authority。
- 允许修改：`skills/ai-dev-flow/` 中与 repair/reviewer policy、只读 gate、测试和直接冲突说明相关的文件；根目录 `README.md` / `README.en.md` 的直接冲突说明；本 TASK、计划和任务板；以及从本机 `cad-dotnet-autotest` 安装副本复制出的隔离候选文件 `C:\Users\92336\.codex\visualizations\2026\07\27\019fa15f-d6c2-7421-ba69-91f55b2196ff\cad-dotnet-autotest-staging\SKILL.md`。
- 禁止修改：`evaluations/v0.8/**`、`skills/ai-dev-flow/prototypes/v0.8-lite/**`、历史 TASK、外部项目、`C:\Users\92336\.agents\skills\**` 等本机正在加载的安装副本、依赖/技术栈。

## 依赖与授权

- 前置依赖：`REPAIR-ESCALATION-001` Accepted / Committed / Pushed；base=`8df7399`。
- Base commit：`8df7399`
- 已有 authority：用户于 2026-07-27 明确回复“可以，按新方案修改吧”，授权实现已讨论的连续修复方案；在 Review Passed、UA2 Pending 后又明确要求 Kimi 默认使用自身独立审核、不得借助其他 Agent/Harness（除非用户指定），并回复“认可，继续”，授权重开本任务、修订 Reviewer 路由和统一 CAD AutoTest 计数。
- 验收 authority：用户在收到同 Harness 原生隔离 Reviewer、核心 4 次 / Harness 5 次阈值、CAD AutoTest 单一计数权及“尚未同步生效”的 UA2 摘要后明确回复“通过”；授权记录 UA2 Passed / Accepted。
- 交付 authority：用户随后明确回复“提交并推送，同时同步本机 Skill”；授权精确提交本任务 diff、推送当前 `codex/repair-campaign-001` 分支，并同步实盘确认存在的本机 `ai-dev-flow` 与 `cad-dotnet-autotest` Skill 副本。
- 未授权动作：merge、tag、Release、删除、创建不存在的安装目录、其他项目或服务的外部同步、Closed。
- 执行位置：独立 Worktree `D:\open-source\ai-dev-flow-wt\repair-campaign-001`；分支 `codex/repair-campaign-001`。

## 路由与风险

- 路由：`Controlled`
- Policy 输入：D 级；修改核心 repair 权限、计数和共享 Skill 行为；risk flags=`architecture, core_execution_path, public_api, shared_component, explicit_independent_review`；确定性测试可覆盖机械语义，用户体验取舍需要 UA2。
- Reviewer 闸门：Required；验收建议前必须完成当前 Harness 自身的上下文和写权限隔离 Review。只有用户明确指定时才能跨 Harness；当前 Codex 实施使用 Codex 自身只读隔离 Reviewer。
- 停止条件：旧单次授权兼容性破坏；4 / 5 阈值可被换 chain/TASK/模型绕过；campaign 越界；硬停止 flag 被延迟；gate 直接授予最终 Allowed；当前 Harness 自动调用外部 Reviewer；缺少原生只读能力时伪装 Review Passed；CAD AutoTest 的旧两次环境失败规则提前覆盖 campaign；冻结评估/原型发生变化。

## 完成标准与验证

- 完成标准：可选 campaign authority 在不削弱旧单次授权、安全硬门禁、独立 Review 和交付隔离的前提下，按核心 4 次、Harness 5 次连续无实质进展阈值工作。
- 验证命令或检查：定向与全套 unittest、Skill validator、workflow lint、policy digest、冻结目录零差异和 `git diff --check`。
- [x] 新增可选 `RepairCampaignAuthority`；非 campaign ledger 可用原 `rc2` policy 继续验证旧单次 `EscalatedRepair` receipt，campaign 与新 receipt 使用 `rc3` policy。
- [x] 核心产品连续无进展阈值为 4，Harness 为 5；有实质进展清零。
- [x] 新 chain、TASK、模型或 finding 改名不能清零 campaign streak。
- [x] P0、安全、数据、越界、不可逆、外部副作用、oracle 放宽和未授权依赖立即硬停止。
- [x] campaign scope 能机械证明当前 chain 实际文件位于授权外层范围。
- [x] trusted context 锚定 campaign history 与 hard-stop snapshot；ledger 不能自证或伪造计数。
- [x] gate 只返回机械资格；merge、push、release、Accepted、Closed 保持独立。
- [x] 当前 Harness 默认只调用自身原生、隔离、只读 Reviewer；Kimi 默认 Kimi，不自动调用 Codex 等外部 Harness。
- [x] 原生 Reviewer 不可用时返回 `Blocked/Pending`；只有用户明确指定外部 Reviewer 才允许跨 Harness。
- [x] `cad-dotnet-autotest` 与 `ai-dev-flow` 同时启用时不再维护独立的“两次环境失败”停止计数，统一采用 core 4 / Harness 5 campaign。
- [x] 定向与全套测试、Skill validator、workflow lint 和版本/链接检查通过。
- [x] 新需求独立只读 Review 无开放 P0/P1/P2/P3。
- [x] `git diff --check` 通过，diff 可归属当前 TASK。

## Repair Chain Ledger

- Repair chain：`adf-repair-campaign-authority`；findings=`ADF-CAMPAIGN-INTERRUPTIONS,ADF-NO-PROGRESS-THRESHOLD,ADF-CAMPAIGN-SCOPE`。
- Trigger Review 收据：用户反馈 `CAD-CONTEXT-SCHEDULER-001` 多次修复授权造成持续打断；当前 `rc2` 默认单次 ER authority 已由源码和任务记录确认。
- Trigger Review `RCAMPAIGN-RVW-001`：只读 Reviewer 会话 `019fa19e-7fbf-7f83-9197-9a117d23fe54` 返回 Needs Fix，冻结 `P1/P1/P2` 三项：campaign state 可落后于当前 chain 最新 attempt/review、旧 rc2 单次 ledger 缺少兼容验证路径、未跟踪计划未进入 whitespace 检查。
- Attempt `ER-1`：仅处理上述三项；state receipt 新增 latest campaign attempt/review 一致性校验，rc2 非 campaign 兼容路径及 CLI 回归测试已补齐，计划文件尾部空白已修复；42 / 42 定向测试、77 / 77 全套测试及质量门禁已通过，待 `RCAMPAIGN-RVW-002`。
- Trigger Review `RCAMPAIGN-RVW-002`：只读 Reviewer 会话 `019fa1bb-6b7f-7940-9369-f2150bdfc172` 返回 Needs Fix，冻结 `P1/P1/P2/P2` 四项：TASK 漏写根目录 README 权限、旧 state 可跨 chain 重放、campaign limit 遮蔽最新 Review 终态、TASK/看板验证状态矛盾。
- Attempt `ER-2`：仅处理上述四项；补齐已批准计划中的 README 允许范围，trusted context 改为唯一 expected campaign state receipt hash 并补跨-chain replay 回归，`Blocked/Passed` Review 终态先于 campaign limit，统一验证状态记录；44 / 44 定向测试、79 / 79 全套测试及质量门禁已通过，待 `RCAMPAIGN-RVW-003`。
- Trigger Review `RCAMPAIGN-RVW-003`：只读 Reviewer 会话 `019fa1ca-3201-7582-bc1d-d0aa0e21c428` 返回 Needs Fix，冻结 `P1/P2` 两项：trusted context 未独立锚定当前 TASK/验收合同、Outcome 留有“尚待验证”旧句。
- Attempt `ER-3`：仅处理上述两项；campaign trusted context 强制核对 `expected_task_id` 与 `expected_acceptance_contract_hash`，补跨 TASK/合同 replay 回归，并统一 Outcome 状态；45 / 45 定向测试、80 / 80 全套测试及质量门禁已通过，待 `RCAMPAIGN-RVW-004`。
- Trigger Review `RCAMPAIGN-RVW-004`：只读 Reviewer 会话 `019fa1d6-e486-7ef3-9626-5289ac6b9f07` 返回 Needs Fix，冻结 `P1/P2` 两项：后续新 chain 的 AutoRepair 未推进 campaign state、Outcome 仍有一处“尚待验证”旧句。
- Attempt `ER-4`：仅处理上述两项；campaign authority 新增生效 chain/history head，授权前同-chain patch 不计数，后续新 chain 的 AR/ER 均进入 freshness 校验，并清理旧状态句；45 / 45 定向测试、80 / 80 全套测试及质量门禁已通过，待 `RCAMPAIGN-RVW-005`。
- Trigger Review `RCAMPAIGN-RVW-005`：只读 Reviewer 会话 `019fa1e7-f08f-7bc3-8bf2-5b433e7389ef` 返回 Needs Fix（P0=0 / P1=0 / P2=1 / P3=0）；代码与关键门禁通过，冻结唯一 P2：Outcome 把已经完成的 ER-4 全套验证误写为仍未完成。
- Attempt `ER-5`：仅修正上述事实状态矛盾；不改 policy、判定器、测试或验收边界，TASK lint 与 tracked/untracked whitespace 检查已通过，待 `RCAMPAIGN-RVW-006`。
- Trigger Review `RCAMPAIGN-RVW-006`：只读 Reviewer 会话 `019fa1f8-2f3c-7b93-9a3f-600b9009c838` 返回 Passed（P0=0 / P1=0 / P2=0 / P3=0）；确认 `RVW-005-P2-001` 已关闭，完整 campaign 语义与质量门禁无开放 finding，允许进入 UA2。
- Contract Revision `UCR-1`：用户在 UA2 前补充“当前 Harness 自身独立审核、禁止自动跨 Harness、统一 CAD AutoTest 计数”要求并明确“认可，继续”。该动作是需求/验收合同修订，不计 repair attempt；`RCAMPAIGN-RVW-006` 仍是旧范围有效收据，但不能覆盖新需求，当前 Review 重新置为 Pending。
- Implementation `UCR-1`：新增 `reviewer_selection` policy 并由 `repair_gate.py` 校验；Kimi/Codex/OpenCode 映射改为当前 Harness 原生优先，缺原生能力即 `Blocked/Pending`，外部 Reviewer 仅限用户明确指定；Workflow、AGENTS 兼容规则、README、CHANGELOG 与回归测试已同步。`cad-dotnet-autotest` 因无源码仓库，仅在隔离暂存区形成单一计数权/分类候选，未修改本机安装副本。定向 46 / 46、全套 81 / 81、两个 Skill validator、TASK/project lint、policy digest、399 行预算、冻结目录和 tracked/untracked/候选 diff check 已通过，待 `RCAMPAIGN-RVW-007`。
- Trigger Review `RCAMPAIGN-RVW-007-A`：当前 Codex Harness 自身的隔离只读 Reviewer 完成静态审查且无 P0～P3 finding，但因全局只读沙箱不能创建测试临时目录返回 `Blocked`；该环境诊断不计 repair。
- Trigger Review `RCAMPAIGN-RVW-007-B`：在 176 / 176 文件一致的一次性审核快照中复现定向 46 / 46、全套 81 / 81 后返回 Needs Fix（P0=0 / P1=1 / P2=0 / P3=0），冻结 `RVW-007-F01`：CAD 候选标准执行顺序仍无条件写“最多 3 轮”，可能早于 campaign 的 4 / 5 阈值停止。
- Attempt `ER-6`：仅关闭 `RVW-007-F01`；把 CAD 候选标准执行顺序改为 ai-dev-flow 激活时由 campaign 单独决定计数、继续或 Stop，仅 CAD Skill 单独运行时最多 3 轮；候选 validator 通过，安装原件 SHA256 保持 `132A73168C219987FB36CDDE15F58639C4FFC2846EBF70814C423D2033C0FF09`。
- Trigger Review `RCAMPAIGN-RVW-007`：当前 Codex Harness 自身的隔离 Reviewer 在禁用 multi-agent、未调用其他 Harness 的条件下返回 Passed（P0=0 / P1=0 / P2=0 / P3=0）；确认 `RVW-007-F01` 已关闭，候选中所有本地 3 轮 / 2 次失败限制仅适用于 CAD Skill 单独运行。复审实际通过定向 46 / 46、全套 81 / 81、CAD validator 和 176 / 176 文件对照；候选 SHA256=`35D70272179A57183CF1B2BCD9FB301E65C5404BE078C6D81A98E8E7FA911E88`，允许进入 UA2。
- UA2 receipt：用户于 2026-07-27 在收到明确的规则摘要、验证结果和“尚未同步生效”边界后回复“通过”；确认同 Harness 原生隔离 Reviewer、核心 4 次 / Harness 5 次阈值和 CAD AutoTest 单一计数权符合预期。该无 patch 验收与记录同步不计 repair attempt，也不授权 commit、push、merge、Release、本机同步或 Closed。
- Delivery receipt：实现与验收提交 `0e2c5fbd98efad0c13f6ceaec97f8e6d229e7e48` 已推送到 `origin/codex/repair-campaign-001`，首次远端核对 `LOCAL=REMOTE`。实盘确认存在的 4 个 `ai-dev-flow` 目标（`.agents`、`.codex`、OpenCode、cc-switch）已由仓库源同步为 `VERSION=0.8.3`，每处 92 / 92、Missing / Extra / Changed=`0 / 0 / 0`，policy digest 均为 `ec3ff867bb72d1a6dcb763b653d528018fc79ece1121e95638071d70da72f2fe`。
- CAD Skill receipt：同一 4 个目标中的 `cad-dotnet-autotest/SKILL.md` 已同步为复审通过候选，SHA256 均为 `35D70272179A57183CF1B2BCD9FB301E65C5404BE078C6D81A98E8E7FA911E88`；每处其余 12 个资产相对同步前备份均未变化。8 个安装目标的 Skill validator 全部通过；备份位于 `C:\Users\92336\.codex\visualizations\2026\07\27\019fa15f-d6c2-7421-ba69-91f55b2196ff\skill-sync-backup-20260727-153300`。
- History anchor：base=`8df7399`；source_ref=`task:docs/tasks/REPAIR-CAMPAIGN-001.md#repair-chain-ledger`。
- Trusted context：当前对话、`REPAIR-ESCALATION-001` Accepted 事实源、当前 Git/Worktree 只读快照。
- Escalated authority：不适用；本 TASK 是新功能执行，不消费下游项目 repair campaign。
- 非计数动作：基线测试、只读源码/任务核对、计划和 TASK 初始化。
- 机械判定：不适用；本任务实现 gate 本身。
- Orchestrator 提升：当前用户 authority 已覆盖实现、验证、UA2 Accepted、当前任务精确 commit/branch push 和现有本机 Skill 同步；不包含 merge、Release、其他外部同步或 Closed。

## Outcome

- Base / Diff：base=8df7399;diff=working-tree-ucr1
- 隔离位置：`D:\open-source\ai-dev-flow-wt\repair-campaign-001` / `codex/repair-campaign-001`。
- 回滚方式：仅恢复本任务相对 `8df7399` 的未提交 diff，不改写历史、不删除 Worktree。
- 修改文件：原 campaign 实现的 `SKILL.md + CORE.md` policy、`repair_gate.py`、repair/contract tests、Workflow、模板、README、版本与迁移说明、本 TASK、计划和任务板；`UCR-1` 追加 Reviewer policy/Workflow/tests，并在隔离暂存区形成 `cad-dotnet-autotest/SKILL.md` 候选补丁。
- 验证证据：`UCR-1` 后定向 unittest 46 / 46、全套 unittest 81 / 81、仓库 Skill 与 CAD AutoTest 隔离候选的 validator 均通过；policy digest=`ec3ff867bb72d1a6dcb763b653d528018fc79ece1121e95638071d70da72f2fe`，默认运行时 399 / 400 行，冻结目录零差异，tracked/untracked/候选 diff check 均通过；本 TASK lint 为 0 error / 0 violation / 1 warning，项目根 lint 为既有 19 error / 0 violation / 22 warning。
- Review findings：`RCAMPAIGN-RVW-001`～`005` 的 findings 已分别由 `ER-1`～`ER-5` 关闭；`RCAMPAIGN-RVW-006` 对旧范围 Passed。`UCR-1` 的唯一 finding `RVW-007-F01` 已由 `ER-6` 关闭，`RCAMPAIGN-RVW-007` 最终 Passed，P0～P3 全为 0。
- UA 动作与结果：UA2 Passed；用户于 2026-07-27 在收到验收摘要后明确回复“通过”。
- Git / 同步收据：实现与验收提交 `0e2c5fb` 已形成并首次推送；4 个现有 ai-dev-flow 安装目标已达 92 / 92 SHA256 parity，4 个现有 CAD AutoTest 目标已统一到复审候选哈希，8 / 8 validator 通过。
- 状态边界：Accepted / Committed / Branch Pushed / Unmerged / Unreleased / Local Sync Verified / Not Closed。
- 剩余风险：`0.8.3` 仍是未发布开发线且任务分支未合并；已经运行中的 Kimi/Codex 会话可能需要新建任务或重启后才重新加载 Skill。
- 下一步：如需 merge、tag、Release 或 Closed，必须由用户另行授权；当前不自动执行。
