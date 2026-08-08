# ADF-V010-CAPABILITY-REVIEW：能力驱动的独立 Review 与新 Contract

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `ADF-V010-CAPABILITY-REVIEW`
- `task_type`: `code`
- `task_class`: `D`
- `lifecycle`: `Review`
- `review_status`: `Passed`
- `ua_level`: `UA3`
- `ua_status`: `Pending`
- `commit_status`: `Committed`
- `merge_status`: `Unmerged`

## 目标与边界

- 目标：建立 Harness-neutral 能力要求、Review Recipe、薄 Adapter 与 `adf/v0.10.0` Workflow Contract，使新任务可合法表达 `Review Not Required`。
- 非目标：不批量迁移历史 v0.7 TASK，不重做 Dashboard UI，不把具体 Harness 命令写入核心 policy。
- 允许修改：总合同第 8.2 节列出的 Skill、Contract、Adapter、测试和最小 Dashboard 兼容范围，以及相关 TASK/TASK_BOARD。
- 禁止修改：Runtime Session、Project Console 产品实现、Legacy 删除、release/安装同步。

## 依赖与授权

- 前置依赖：CORE-SPLIT 阶段验证、Review、commit 完成。
- Base commit：`9a8642acb7b2f2372e8610594686bd38a9d7fc19`（CORE-SPLIT delivery head）。
- 已有 authority：依赖满足后的阶段实现、验证、只读 Review、commit、push、Draft PR。
- 未授权动作：merge、release、正式 Skill 同步、自动 Accepted/Closed。
- 执行位置：stacked branch `codex/v010-capability-review`；Worktree `D:/open-source/ai-dev-flow-wt/v010-capability-review`。

## 路由与风险

- 路由：`Controlled`。
- Policy 输入：D 级；公共合同、兼容、核心 Review 语义和 shared component 风险。
- Reviewer 闸门：Required；当前采用 R2（独立 Codex 进程 + read-only sandbox），必须隔离且只读，无开放 P0/P1。
- 停止条件：前置阶段未完成、需破坏旧 Contract、需让 Adapter 授予核心 authority。

## 完成标准与验证

- 完成标准：第 8.9 节 Adapter、双版本 Contract、模板、Dashboard 兼容与独立 Review 门禁全部满足。
- 验证命令或检查：Skill/backend/frontend 全量相关测试、Workflow Schema 正反组合、workflow lint、browser、diff check 与 R2 独立 Review。
- [x] 新 Adapter 接入无需修改核心，generic/codex/kimi-code/opencode/zcode 初版可用。
- [x] v0.7 TASK 继续解析且不改义；v0.10 TASK 支持 `Required` / `Not Required`。
- [x] Not Required 可合法完成；Required 在 Accepted/Closed 前仍需 Passed。
- [x] Brief/Full 选择不依赖模型名；Dashboard 合同、codegen 与兼容测试通过。
- [x] 全量相关测试、workflow lint、`git diff --check` 和独立只读 Review通过。

## Repair Chain Ledger（仅进入 repair 时填写）

- Attempt AR-1：处理 `ADF-V010-CAP-R001`～`R004`（均 P1）；Reviewer session `019fe100-05e5-7033-83a6-d65aed40c428`，Round 1=`Needs Fix 0/4/0/0`。
- RED：Controlled/高 UA 可声明 Not Required；Review 历史可回退 Not Run；R4 仅凭授权；TASK 未写回最终 backend 全量结果。
- GREEN：policy 可见输入强制 Required，Review 回退产生 `V_REVIEW_REGRESSION`，R4 要求授权+外部能力+调用证据，backend 最终 `179/179`。
- SIGNAL：Skill 全量 `110/110`；Workflow Schema policy guards `7/7`；backend 全量 `179/179`；独立复审待运行。
- Attempt AR-2：Round 2 session `019fe10d-0843-7b90-a30c-fc370f8b2f68` 为 `Needs Fix 0/1/0/0`；`R001/R003/R004` Closed，`R002` 因只检查最近两版仍 Open。
- RED：三段历史 `In Review → Not Run → 普通编辑仍 Not Run` 会遮蔽更早 Review 事实。
- GREEN：历史检查现扫描该 TASK 的完整相关 commit chain；Skill 三段测试与真实 DashboardCore 三段集成测试均通过，Dashboard 返回 `none / CONTRACT_STATE_INVALID`。
- SIGNAL：Skill `110/110`；backend 增至 `180/180`；workflow lint `0/0/62`；Round 3 独立复审待运行。
- Attempt AR-3（`ExtendRound3`）：Round 3 session `019fe11a-c725-7882-8ebf-7f7d97ca4c3b` 为 `Needs Fix 0/1/0/0`；无新增 finding，`R002` 收窄为重命名链缺口。Orchestrator 根据上一轮线性三提交 criterion 已 RED→GREEN、无 GREEN→RED、无新增阻断 finding、严重度不升、测试覆盖增加且目标仍冻结，批准最后一次自主修复。
- RED：任务文件在 Review 开始后被重命名并继续普通编辑时，扫描会保留较新提交却忽略 rename 记录，使重命名前的 Review 事实不可见。
- GREEN：涉及当前 TASK 路径的 rename 历史会标记为歧义，并产生阻断式 `V_REVIEW_HISTORY_AMBIGUOUS`；不以不可阻断的 warning 代替保护。
- SIGNAL：新增 Skill 与真实 DashboardCore 重命名历史回归测试；Skill `111/111`、backend `181/181`。
- Round 4：session `019fe122-bf37-70b0-892d-7d61b6ea3a84` 为 `Needs Fix 0/1/0/0`；`R002` 仍 Open。普通 copy 的源文件未同时修改时，`--find-copies` 不保证纳入候选，需要 `--find-copies-harder` 或等价的可靠机制，并补普通 copy 与同目录无关 rename/copy 隔离测试。
- Stop：已用满 3 次自主 repair；当前为 `UserDecisionRequired`。未经用户提供 chain-bound 单次 `EscalatedRepair` 或 `RepairCampaignAuthority`，禁止继续 patch，也不得进入下一阶段。
- Attempt ER-1（`EscalatedRepair`）：用户于 2026-08-08 明确授权“继续，直到可验收状态”；本次升级修复仅绑定 `R002`、当前 allowed scope 与普通 copy closure，不授予 merge/release/同步/Accepted/Closed。
- RED：未修改来源的普通 copy 可能被 Git 记录为 `A`，无法触发历史歧义阻断；同父目录扩展扫描还需证明不会误伤无关 sibling。
- GREEN：历史命令启用 `--find-copies-harder`；新增未修改来源 copy 的 Skill/Dashboard 回归测试，以及同父目录无关 rename 隔离测试。
- SIGNAL：定向与全量验证、ER-1 后独立复审待运行。
- ER-1 Review：session `019fe130-43df-7551-b44c-659b67ba9fe6`，`Passed 0/0/0/0`；`R002` Closed，无新增 finding。

## Outcome

- Base / Diff：base=9a8642acb7b2f2372e8610594686bd38a9d7fc19;implementation=`384f96f`。
- 隔离位置：`codex/v010-capability-review` / `D:/open-source/ai-dev-flow-wt/v010-capability-review`。
- 回滚方式：提交前丢弃本阶段精确 diff；提交后 revert 本阶段 commit，不改写 CORE-SPLIT 历史。
- 修改文件：新增 capability/recipe 文档、五个薄 Adapter 与 loader；Workflow Contract reader/validator/schema 双读 v0.7/v0.10；Full/Brief 模板升级 v0.10，Compact 保留 v0.7；Dashboard 仅增加兼容字段、动作判定与详情展示；补齐相关测试和生成类型。
- 范围适配：`policy_loader.py` 与 `schemas/workflow-contract.schema.json` 未列在最初允许清单，但分别是 CORE-SPLIT 新增严格 loader 与现有 RuntimeCompatibility 的直接事实源；为保持 core policy 可加载和双版本 schema 可启动而做最小改动，不扩展到 Runtime/Project Console。
- 验证证据：Skill 最终 `113/113`；backend 最终 `182/182`；Workflow JSON Schema policy/完成门禁组合 `7/7`；frontend codegen/check、typecheck、lint、Vitest `95/95`、build、Playwright `96/96` 与新增详情目标用例通过；integration Python 3.13 为 `49/51`，仅 Stage 0 已登记 artifact guard 与 state-matrix 基线债务；最终 workflow lint 与 `git diff --check` 待提交前重跑。
- Review findings：Round 1 `Needs Fix 0/4/0/0`；Round 2/3/4 依次收敛 `R002`；用户授权 ER-1 后，session `019fe130-43df-7551-b44c-659b67ba9fe6` 为 `Passed 0/0/0/0`，`R001`～`R004` 全部 Closed。
- 状态边界：Review / Passed / UA3 Pending / Committed (`384f96f`) / Unmerged / Not Released / Not Closed。
- 剩余风险：生产依赖树存在基线 `fast-uri` high advisory，`package-lock.json` 本阶段未改；正式发布前应在 RELEASE 阶段单独评估兼容升级。集成套件两项历史债务仍未在本阶段修复。
- 下一步：推送当前 stacked branch 并创建 Draft PR，然后按第 18 节进入 RUNTIME-CONSOLE-BE。
