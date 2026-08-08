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
- [x] 外部复审修复后的全量相关测试、workflow lint、`git diff --check` 和新独立只读 Review 通过。

## Repair Chain Ledger（仅进入 repair 时填写）

- `ADF-V010-STACKED-EXT-P2-SKILL-001`：外部复审指出 SKILL 的“最多一份 reference”与能力/Recipe 等必需多文件集合冲突。修复：改为读取当前动作的最小必需集合，并显式标记必需组合。
- `ADF-V010-STACKED-EXT-P2-ADAPTER-001`：外部复审要求 Adapter 显式声明 `runtime_session_bridge`，不能与正式 Skill sync 混用。修复：新增独立枚举轴 `runtime_session_bridge`，并把正式同步说明重命名为 `formal_skill_sync_method`；loader、五份 Adapter、fixture、能力合同与测试同步更新。
- 当前外部修复：已吸收 #14 `56c2aa7`；fresh 全量验证已完成，当前等待 Round 3 定向刷新与新隔离只读 Review。历史 ER-1 Passed 不可替代当前 Review。
- 外部修复 Round 1 Review：session=`019fe21b-8825-75e2-a9ba-fa19b3b2d729`，`Needs Fix 0/1/1/0`。P1 `ADF-V010-REVIEW-P1-001` 证明未验证普通映射可绕过 loader 获得 `R1`；P2 指出 BOARD/MASTER 仍可能误用历史 Passed。Round 2 已让 Recipe 入口重验完整 Adapter 合同，缺字段、未知字段或非法枚举一律 `R5`，并同步状态投影；等待 fresh 验证与新 Review。
- 外部修复 Round 2 Review：session=`019fe221-d8d5-7a81-b7c4-4124794bbd95`，`Needs Fix 0/1/1/0`。P1 `ADF-V010-R2-P1-001` 证明列表/字典等不可哈希枚举会抛 `TypeError`；P2 指出 fresh 验证措辞漂移。Round 3 已先验证枚举值为字符串，并补不可哈希负例；fresh 全量证据已存在，等待定向刷新与新 Review。
- 外部修复 Round 3 Review：session=`019fe225-d887-7640-96de-d704d7f6c6ed`，`Passed 0/0/0/0`；Adapter 入口 `98/98` 内存矩阵、合法 R1-R4、#14 Schema 与双版本 Contract 兼容均通过。Review 不代表 UA、commit、push、merge、release、正式 Skill 同步、Accepted 或 Closed。

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

- Base / Diff：base=d6d6484;diff=d6d6484..83ec457
- 隔离位置：`codex/v010-capability-review` / `D:/open-source/ai-dev-flow-wt/v010-capability-review`。
- 回滚方式：提交前丢弃本阶段精确 diff；提交后 revert 本阶段 commit，不改写 CORE-SPLIT 历史。
- 修改文件：新增 capability/recipe 文档、五个薄 Adapter 与 loader；Workflow Contract reader/validator/schema 双读 v0.7/v0.10；Full/Brief 模板升级 v0.10，Compact 保留 v0.7；Dashboard 仅增加兼容字段、动作判定与详情展示；补齐相关测试和生成类型。
- 范围适配：`policy_loader.py` 与 `schemas/workflow-contract.schema.json` 未列在最初允许清单，但分别是 CORE-SPLIT 新增严格 loader 与现有 RuntimeCompatibility 的直接事实源；为保持 core policy 可加载和双版本 schema 可启动而做最小改动，不扩展到 Runtime/Project Console。
- 验证证据：Round 2 fresh Adapter 定向 `6/6`、Skill `119/119`、backend `182/182`、workflow lint `errors=0 / violations=0 / warnings=1`、`git diff --check` 已通过；Round 1 后 frontend codegen check/typecheck/lint/Vitest `95/95`/build/Playwright `96/96` 已通过，Round 2 未改前端。首次组合 `npm run verify` 仅因工具 124 秒硬超时无终态，随后拆分组件全部通过。stack full integration 已知为 `51/52`，唯一 artifact guard 失败须在上层全部更新后复跑。
- Review findings：Round 1 `Needs Fix 0/4/0/0`；Round 2/3/4 依次收敛 `R002`；用户授权 ER-1 后，session `019fe130-43df-7551-b44c-659b67ba9fe6` 为 `Passed 0/0/0/0`，`R001`～`R004` 全部 Closed。
- 状态边界：External Repair Review Passed / Fresh Verification Passed / Repair Committed `83ec457` / UA3 Pending / Unmerged / Not Released / Not Synced / Not Accepted / Not Closed。
- 剩余风险：生产依赖树存在基线 `fast-uri` high advisory，`package-lock.json` 本阶段未改；正式发布前应在 RELEASE 阶段单独评估兼容升级。集成套件两项历史债务仍未在本阶段修复。
- 下一步：push #15 当前修复，再以普通 merge 更新 #16。禁止提前进入正式 UA。
