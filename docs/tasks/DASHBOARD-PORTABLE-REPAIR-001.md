# DASHBOARD-PORTABLE-REPAIR-001：阻止未登记 Python 字节码绕过运行时校验

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `DASHBOARD-PORTABLE-REPAIR-001`
- `task_type`: `repair`
- `task_class`: `D`
- `lifecycle`: `Accepted`
- `review_status`: `Passed`
- `ua_level`: `UA6`
- `ua_status`: `Passed`
- `ua_evidence`: `docs/tasks/DASHBOARD-PORTABLE-001.md#dashboard-portable-001-ua6-复验通过-2026-07-30`
- `acceptance_authority`: `User Confirmed`
- `commit_status`: `Uncommitted`
- `merge_status`: `Unmerged`

## Scheduling

- `scheduling_schema`: `ai-dev-flow/scheduling/v1`
- `priority`: `high`
- `depends_on`: `DASHBOARD-PORTABLE-001#lifecycle=Needs Fix;DASHBOARD-PORTABLE-001#review_status=Needs Fix`
- `replaces`: `none`
- `discovered_from`: `DASHBOARD-PORTABLE-001`
- `parent`: `DASHBOARD-PORTABLE-001`
- `conflicts_with`: `none`
- `parallel_intent`: `serial`
- `write_scope`: `file:dashboard/backend/src/ai_dev_flow_dashboard/runtime_compat.py;file:dashboard/backend/tests/be001/test_runtime_compat.py;file:dashboard/integration/accepted-artifacts.json;file:dashboard/integration/build_skill_runtime.py;file:dashboard/integration/tests/test_build_skill_runtime.py;file:dashboard/integration/tests/test_portable_runtime.py;file:skills/ai-dev-flow/scripts/dashboard.py;dir:skills/ai-dev-flow/dashboard;file:docs/tasks/DASHBOARD-PORTABLE-REPAIR-001.md;file:docs/tasks/DASHBOARD-PORTABLE-001.md;file:docs/TASK_BOARD.md`
- `module_locks`: `dashboard-runtime;skill-distribution`
- `worktree`: `required`
- `branch_hint`: `codex/dashboard-portable-001`
- `risk_flags`: `build_or_deploy_config;core_execution_path;historical_p1;security;shared_component;tests_do_not_cover_oracle`

## 目标与边界

- 目标：关闭独立 Review 的唯一阻断项 `DASHBOARD-PORTABLE-RVW-P1-002`，使运行时完整性校验、持续指纹和生成器检查都把 `.pyc` 与 `__pycache__` 内文件视为实际 bundle 文件。
- 目标：安装入口必须在把 bundle backend 加入 `sys.path`、导入 bundle 模块之前，仅用可信入口与 Python 标准库完成完整文件集合及内容哈希预检。
- 目标：启动前存在未登记字节码时明确失败；运行中出现字节码时只设置 `restart_required=true`，不热加载、不改变已服务的 snapshot/static 内容。
- 非目标：不改变 Dashboard wire schema、治理 schema/policy、Contract Reader、依赖、端口/实例模型或既有只读权限边界。
- 允许修改：仅限 `write_scope` 列出的 10 个精确文件及生成的 `skills/ai-dev-flow/dashboard/**`；其中 `accepted-artifacts.json` 只能更新 candidate overlay，frozen accepted baseline 不得改变。
- 禁止修改：其他业务代码、依赖与版本文件、本机安装 Skill、其他项目；禁止放宽 manifest、测试判据或 loopback/只读边界；禁止 commit、merge、push、release、外部同步、Accepted 或 `Closed`。

## 依赖与授权

- 前置依赖：`DASHBOARD-PORTABLE-001` 最终独立 Review `Needs Fix`，唯一开放 P1 为 `DASHBOARD-PORTABLE-RVW-P1-002`。
- Base commit：`51d4eaa30dfb7a88dc0a7bb035b31beccabab053`；候选实现沿用父 TASK 的同一未提交 Worktree。
- 已有 authority：用户于 2026-07-30 在收到“创建本 repair TASK、只修 `.pyc/__pycache__` 导入前校验缺口、补测试、完整验证并独立 Review，持续到无 P0/P1”的明确范围后回复“授权”。该消息授权 scope-bound `RepairCampaignAuthority`，profile=`harness`。
- 未授权动作：新增/升级依赖，修改 schema/policy/Reader，本机 Skill 同步，commit、merge、push、tag、Release、部署、删除、外部同步、UA6 代验收、Accepted 或 `Closed`。
- 执行位置：独立 Worktree `D:\open-source\ai-dev-flow-wt\dashboard-portable-001`，分支 `codex/dashboard-portable-001`。

## 路由与风险

- 路由：`Controlled`
- Policy 输入：`task_class=D`、`ua_level=UA6`；命中 build/deploy config、core execution path、historical P1、security、shared component 与 tests-do-not-cover-oracle。
- Reviewer 闸门：`Required`；每次意图关闭 finding 的 patch 后，由当前 Codex Harness 建立隔离只读 Reviewer；无开放 P0/P1 才可结束 repair loop。
- 主要风险：预检自身意外从 bundle 导入模块；文件集合仍遗漏字节码；运行中把更新热切换进旧实例；生成器 build/check 对污染处理不一致。
- 停止条件：出现 P0、安全边界变化、数据完整性风险、越出 scope、不可逆/外部副作用、放宽测试 oracle、未授权依赖或缺少必要证据；Harness 连续 5 次无实质进展也返回用户裁决。

## 完成标准与验证

- 完成标准：关闭 `DASHBOARD-PORTABLE-RVW-P1-002` 的全部冻结标准，且既有只读、安全、兼容性和隔离行为不回归。
- 验证命令或检查：定向字节码测试、backend/integration/frontend/Skill 全量、bundle build/check、artifact guard、真实外部项目启停、workflow lint、diff/AST/进程与端口清理检查、独立只读 Review。
- [x] 可信入口在修改 `sys.path` 和导入 bundle 前完成 manifest 身份、完整文件集合与逐文件 SHA-256 校验。
- [x] `verify_runtime_bundle`、`runtime_bundle_fingerprint` 和生成器 `--check` 均不忽略 `.pyc` 或 `__pycache__`。
- [x] 启动前污染测试覆盖未登记 `.pyc/__pycache__`，证明失败发生于 bundle 导入前且不创建运行状态。
- [x] 运行中污染测试覆盖 `restart_required=true`、snapshot/static 不热切换、两个实例仍独立停止。
- [x] 生成器测试证明 `--check` 拒绝 cache 污染，重新 build 可确定性清除污染并恢复 parity。
- [x] 父 TASK 的 backend、integration、frontend、Skill、bundle parity、真实项目只读与清理证据不回归。
- [x] 独立只读 Review 无开放 P0/P1。
- [x] `git diff --check` 通过，diff 可归属本 TASK 与父 TASK allowlist。

## Repair Chain Ledger

- Repair chain：`repair_chain_id=DASHBOARD-PORTABLE-BYTECODE-RC-001`；`finding_ids=[DASHBOARD-PORTABLE-RVW-P1-002]`；`closure_contract_hash=c5563529e138b578a07ca7d4fea78afecbefa69c0281a0984757ab60128bcca5`；`allowed_files_hash=49773fa4f83e6d48138b461feed4e170295259c23ff889c236632a72e5483dd8`。
- Closure canonical：`startup-preflight-before-bundle-import|all-dashboard-files-in-exact-set-including-pyc-cache|fingerprint-detects-pyc-cache|generator-check-rejects-cache-pollution|running-instance-restart-required-no-hot-switch|existing-tests-green`。
- Scope canonical：10 个精确文件按相对路径升序并以 LF 连接，另含 path prefix `skills/ai-dev-flow/dashboard/`；均绑定本 TASK 的 `write_scope`。`accepted-artifacts.json` 是父 TASK 原 allowlist 中的验证收据，因全量测试首次指出 candidate overlay 哈希过期而在业务 patch 后、写入前补录；不改变 closure、实现范围或 accepted baseline。
- Trigger Review 收据：Codex 原生隔离只读 Review，结论 `Needs Fix`，P0/P1/P2/P3=`0/1/0/0`；receipt SHA256=`a4ca07a976631b42406e2c9b0771d379177ac005fbd023f077c48565316c5c8b`；唯一开放 finding 为 `DASHBOARD-PORTABLE-RVW-P1-002`。
- Attempt 收据链：`AR-1` candidate implementation scope SHA256=`02a2cdcb3a20f064a901035a19457df3067bd4061e58fa09b65f2147fdc0801c`（43 files：7 个实现/测试/候选收据文件 + 完整生成 bundle 36 files）；最终独立复审 session=`019fb1a1-6836-7042-bd02-eebe7f198f31`，receipt SHA256=`82ec6187e70a7db948c0362166ad23b01c8b09e2a88c9c3200b382859232952e`，结论 `Passed`，P0/P1/P2/P3=`0/0/0/0`，原 P1-002 Closed。
- History anchor：父 chain 的两轮有限 repair 已用满；本新 chain 不重置历史，source=`docs/tasks/DASHBOARD-PORTABLE-001.md#Outcome` 与上述 Trigger Review。
- Trusted context：当前用户授权消息、父 TASK、当前 Worktree/base 只读快照和 Trigger Review 原始收据。
- Escalated authority：不使用单次 ER；用户授权的是冻结 TASK/验收合同/外层 scope 的连续修复。
- Campaign authority：`campaign_id=DASHBOARD-PORTABLE-P1-002-CAMPAIGN-001`；task=`DASHBOARD-PORTABLE-REPAIR-001`；profile=`harness`；只允许上述 closure 与 scope，直到独立 Review 无 P0/P1。
- Campaign state：`attempt_count=1`；`consecutive_no_progress=0/5`；`latest_outcome=review-passed`；相对 Trigger Review 的六项 closure 信号均由 RED 变 GREEN，未见 GREEN 变 RED；无新 blocking finding，hard-stop snapshot 均为 false，campaign repair loop 结束。
- 非计数动作：本 TASK/看板授权收据同步、只读诊断、无 patch 测试重跑与独立 Review 本身；前两次独立 Review 进程各在 10 分钟外层上限后未生成结论/收据，遗留的首个进程树已核对并清理，均不计 repair attempt；第三次纯净只读 Review 形成有效收据。
- 机械判定：父任务自动修复预算已 Stop；当前显式 campaign authority、冻结 finding/closure/scope 与可信上下文齐备。
- Orchestrator 提升：`RepairCampaignAuthority` 已由当前用户消息明确授予；仅提升本修复范围，不产生 delivery、Acceptance 或 Closed authority。

## Outcome

- Base / Diff：base=51d4eaa30dfb7a88dc0a7bb035b31beccabab053;diff=working-tree-repair-review-1
- 隔离位置：`D:\open-source\ai-dev-flow-wt\dashboard-portable-001` / `codex/dashboard-portable-001`。
- 回滚方式：当前无提交；只逆向应用本 TASK 的冻结 scope 增量，父 TASK 既有候选 diff 保持不变。任何删除、reset 或 Worktree 清理仍需用户另行授权。
- 修改文件：可信安装入口新增 bundle 预导入校验；runtime 校验/指纹和生成器实际集合不再排除 `.pyc/__pycache__`；backend/integration/generator 测试覆盖启动前 unchecked-hash 字节码、运行中 restart-only 与 `--check` 污染；生成 bundle 与 candidate artifact overlay 同步。
- 验证证据：定向 10/10；backend 139/139；integration 42/42；frontend unit 82/82 + Chrome 83/83；Skill 85/85；bundle build/check 35 manifest files；artifact guard `baseline_preserved=true / candidate_consistent=true / accepted_ok=false`；Skill validator、111 Python AST、`git diff --check` 通过。
- 验证证据：真实 CADCat 外部安装副本启动得到 13 个 TASK（含 `PROJECT-PLOT-CONFIG-001`），loopback/动态端口/实例状态正常；退出后项目 TASK/TASK_BOARD 哈希、Git status、Skill 哈希不变，状态、监听和进程零残留。
- 验证异常记录：首次组合定向命令因测试 `PYTHONPATH` 缺少 `dashboard/backend/tests` 出现 1 个 ImportError，修正调用后 10/10；首次 integration 全量因 candidate overlay 两个哈希过期为 41/42，冻结 accepted baseline 不变并更新 candidate 收据后单测 7/7、全量 42/42。系统 validator 在 `py -3` 缺 PyYAML，改用本机已有 PyYAML 的 `python` 后输出 `Skill is valid!`。
- Workflow lint：本 repair TASK 为 errors=0 / violations=0 / warnings=1，唯一 warning 是未提交状态无法由 Git 历史证明；仓库全量 lint 的 19 个 error 与历史 Legacy TASK 有关，非本次新增且未越界迁移。
- Review findings：独立 Reviewer `Passed`，P0/P1/P2/P3=`0/0/0/0`，原 `DASHBOARD-PORTABLE-RVW-P1-002` Closed，无新 finding。逐项确认完整集合/指纹、预导入标准库校验、unchecked-hash 字节码、运行中 restart-only、生成器污染及 accepted baseline/安全边界全部关闭。
- UA 动作与结果：父任务真实双项目页面已由用户于 2026-07-30 确认验收通过；本 repair 随父任务记录 `UA6 Passed / Accepted / User Confirmed`。
- 状态边界：Accepted / Review Passed / UA6 Passed / Uncommitted / Unmerged / Not Released / Not Closed。
- 剩余风险：提交和合并前仍需对完整候选运行新鲜验证与独立只读 Review。
- 下一步：随父任务完成提交前门禁并提交、本地合并；发布和本机同步由独立发布任务记录。
