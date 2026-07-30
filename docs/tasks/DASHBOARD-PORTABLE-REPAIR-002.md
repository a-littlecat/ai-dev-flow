# DASHBOARD-PORTABLE-REPAIR-002：修复生产空白页与历史 Scheduling 兼容

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `DASHBOARD-PORTABLE-REPAIR-002`
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
- `depends_on`: `DASHBOARD-PORTABLE-001#lifecycle=Needs Fix;DASHBOARD-PORTABLE-REPAIR-001#review_status=Passed`
- `replaces`: `none`
- `discovered_from`: `DASHBOARD-PORTABLE-001`
- `parent`: `DASHBOARD-PORTABLE-001`
- `conflicts_with`: `none`
- `parallel_intent`: `serial`
- `write_scope`: `file:dashboard/backend/src/ai_dev_flow_dashboard/runtime_compat.py;file:dashboard/backend/tests/be001/test_runtime_compat.py;file:dashboard/frontend/scripts/generate-types.mjs;file:dashboard/frontend/src/api/schema.ts;file:dashboard/frontend/src/generated/contracts.validators.ts;file:dashboard/integration/accepted-artifacts.json;file:dashboard/integration/artifact_guard.py;file:dashboard/integration/build_skill_runtime.py;file:dashboard/integration/launcher.py;file:dashboard/integration/tests/test_artifact_guard.py;file:dashboard/integration/tests/test_build_skill_runtime.py;file:dashboard/integration/tests/test_launcher.py;file:dashboard/integration/vite.config.mjs;dir:skills/ai-dev-flow/dashboard;file:skills/ai-dev-flow/README.md;file:docs/tasks/DASHBOARD-PORTABLE-001.md;file:docs/tasks/DASHBOARD-PORTABLE-REPAIR-002.md;file:docs/TASK_BOARD.md`
- `module_locks`: `dashboard-runtime;dashboard-security;skill-distribution`
- `worktree`: `required`
- `branch_hint`: `codex/dashboard-portable-001`
- `risk_flags`: `core_execution_path;historical_p1;real_environment;security;shared_component;tests_do_not_cover_oracle`

## 目标与边界

- 目标：关闭 `DASHBOARD-PORTABLE-UA6-P1-001`，让已构建前端在保持 `script-src 'self'` 的严格 CSP 下正常渲染，不允许通过增加 `unsafe-eval` 绕过。
- 目标：关闭 `DASHBOARD-PORTABLE-UA6-P1-002`，对明确声明的 Workflow/Scheduling schema 保持严格版本门禁；历史 TASK 未声明对应版本时保留 unknown，不阻断 ai-dev-flow 自身仓库启动。
- 目标：两个真实项目均使用隔离安装 Skill、独立端口/运行目录启动并可见，停止一个不影响另一个，启停不修改项目、Skill 或 Git。
- 非目标：不改变 Dashboard wire schema、Workflow Contract Reader、Scheduling 解析语义、治理 policy 或前端设计；不添加/升级依赖。
- 允许修改：仅限本 TASK `write_scope`，其中 `skills/ai-dev-flow/dashboard/**` 只能由分发生成器同步源码和已构建前端。
- 禁止修改：不得放宽 loopback、CSP、只读 API 或 authority 边界；不得修改 CADCat、本机安装 Skill、其他业务 TASK；不得 commit、merge、push、release、删除或 Closed。

## 依赖与授权

- 前置依赖：`DASHBOARD-PORTABLE-001` 真实 UA6 形成两个开放 P1；`DASHBOARD-PORTABLE-REPAIR-001` 已 Review Passed。
- Base commit：`51d4eaa30dfb7a88dc0a7bb035b31beccabab053`
- 已有 authority：用户于 2026-07-30 明确要求“继续修复直至可验收”，授权在本 TASK 的两个 finding、验收合同和外层 allowlist 内持续修复、测试、真实双项目启停和独立只读 Review。
- 未授权动作：放宽安全边界、新增/升级依赖、修改本机安装 Skill、Accepted、commit、merge、push、tag、release、删除或 Closed。
- 执行位置：独立 Worktree `D:\open-source\ai-dev-flow-wt\dashboard-portable-001`，分支 `codex/dashboard-portable-001`。

## 路由与风险

- 路由：`Controlled`
- Policy 输入：`task_class=D`、`ua_level=UA6`；风险包含真实环境、安全边界、共享核心路径、历史 P1 和测试未覆盖生产 CSP oracle。
- Reviewer 闸门：`Required`；实现和完整验证后必须由当前 Harness 原生隔离、只读 Reviewer 复审，开放 P0/P1 时继续冻结范围内 repair。
- 停止条件：需要加入 `unsafe-eval`、放宽 loopback/只读边界、改变 schema/policy、引入依赖、写入真实项目/Skill、出现 P0/数据风险/不可逆或外部副作用。

## 完成标准与验证

- 完成标准：关闭原始 UA6 P1 与 AR-1 Review 的全部冻结 finding，且既有只读、安全、兼容、制品完整性和多实例隔离行为不回归。
- 验证命令或检查：定向完整性测试、frontend/backend/integration/Skill 全量、bundle build/check、artifact guard、严格 CSP 生产浏览器、双项目真实实例、workflow lint、diff 与进程/端口检查、独立只读 Review。
- [x] 严格 CSP 页面可用：生产/集成页面在 `script-src 'self'` 下渲染任务关系图，浏览器无 CSP/eval 错误，构建资产不包含 Ajv 运行时编译器。
- [x] Schema 兼容门禁：明确声明的错误/重复/畸形版本继续明确失败；历史未声明版本保持 unknown，并可启动当前 ai-dev-flow 仓库。
- [x] 双项目真实验证：CADCat 与 ai-dev-flow 同时可见，端口、实例 ID、运行目录、TASK/Git/Worktree 不串；停止一个后另一个继续。
- [x] 只读验证：启停前后项目/Skill 文件与 Git 状态不因 Dashboard 改变，最终无非预期监听端口或后台进程。
- [x] backend、integration、frontend、Skill、bundle parity、当前 TASK workflow lint 和生产浏览器验证通过。
- [x] `git diff --check` 通过，diff 可归属当前 TASK。

## Repair Chain Ledger

- Repair chain：`repair_chain_id=DASHBOARD-PORTABLE-UA6-RC-001`；`finding_ids=[DASHBOARD-PORTABLE-UA6-P1-001,DASHBOARD-PORTABLE-UA6-P1-002]`；`closure_contract_hash=d2a35651e8c7fdee7867b8b35786e9466bba4e81aef5a4a6a49e47f7ac570fea`；`allowed_files_hash=94c9668ccc7d3743652c04130230ec9847b1d0e8c4ee1bb5036ad32dc165526c`。
- Closure canonical：`strict-csp-page-renders|ajv-runtime-codegen-absent|explicit-schema-mismatch-fails|legacy-undeclared-schema-unknown|ai-dev-flow-self-starts|two-real-projects-visible|no-project-or-skill-writes`。
- Allowed canonical：AR-1 冻结的是当时的 12 项实现/测试/候选收据范围，其中 `skills/ai-dev-flow/dashboard/**` 是唯一前缀项；AR-1 独立复审前发现初始 scope 漏列父任务已授权且完整性 gate 必需的 candidate manifest 及其断言，已作 record-only correction。后续 AR-2/AR-3 各自使用下方新 chain 的显式 canonical，不用当前扩展后的 `write_scope` 反向解释 AR-1 hash。
- Trigger Review 收据：真实 UA6 浏览器控制台 CSP `EvalError` 与 ai-dev-flow launcher Scheduling schema 错误；父 TASK 已记录两个稳定 P1。
- Attempt 收据链：`AR-1` 已关闭两个触发 P1，但独立只读 Review 返回 `Needs Fix`，P0/P1/P2/P3=`0/2/1/0`；新开放 `DASHBOARD-PORTABLE-REPAIR-002-RVW-P1-001/002` 和 P2-001。
- History anchor：原 chain `attempt_count=1`；Review 会话 `019fb1db-4c97-7391-b85b-6be73aa45d78` 为 AR-1 独立只读收据。
- Trusted context：当前 Harness 已确认用户授权、HEAD/base、真实浏览器错误、launcher 错误与允许范围。
- Campaign authority：`campaign_id=DASHBOARD-PORTABLE-UA6-CAMPAIGN-001`；`task_id=DASHBOARD-PORTABLE-REPAIR-002`；profile=`core_product`；用户授权同一验收合同与 scope 内持续修复直至可验收。
- Campaign state：AR-2 Review 后 `attempt_count=2`、`consecutive_no_progress=0/4`、`latest_outcome=two-p1-closed-one-new-p1`；P1 数由 2 降为 1 且证据覆盖增加，streak 重置；无 hard-stop flag。
- 非计数动作：启动诊断、TASK/看板收据同步、测试原样重跑。
- 机械判定：`MechanicallyEligible`；eligible_mode=`AutoRepair`。
- Orchestrator 提升：AR-1 已完成并复审。用户的 task-bound campaign authority 覆盖父任务 integration 外层 scope；冻结新 chain 后提升为 `AutoRepairAllowed / campaign AR-2`。

### Repair chain：DASHBOARD-PORTABLE-INTEGRITY-RC-001

- Finding IDs：`DASHBOARD-PORTABLE-REPAIR-002-RVW-P1-001`、`DASHBOARD-PORTABLE-REPAIR-002-RVW-P1-002`、`DASHBOARD-PORTABLE-REPAIR-002-RVW-P2-001`。
- Closure canonical：`candidate-index-base-or-candidate-only|untracked-or-candidate-index-only|bundle-build-codegen-gated|bundle-check-codegen-gated|diff-check-green|all-regressions-green`。
- `closure_contract_hash=04e3732821b5335ba6314927a31797f9f636fc6437950a1ea4fe87b48745e7fd`；AR-2 record-only 规范化后的 `allowed_files_hash=1d15ff0896534a6d6dde1055a845a2c8d2a8eb5c76bf342be3f07625f81b618d`。
- Allowed canonical：14 个 `file:` 项和 1 个 `dir:` 项，即 AR-2 时本 TASK `write_scope` 从 `runtime_compat.py` 至 `vite.config.mjs` 的 11 个 dashboard 文件、`dir:skills/ai-dev-flow/dashboard`、父 TASK、本 TASK 与看板；按包含 `file:`/`dir:` 前缀的完整字符串升序，以单个 LF 连接且末尾无 LF 计算 SHA-256。原记录的 `a845...` 缺少可复现序列说明，本次只校正收据表达，不扩大 AR-2 authority。
- AR-2 目标：index blob 只能是 base/candidate 合法状态；bundle build/check 必须先通过 `codegen:check`；`git diff --check` GREEN；完整回归与独立复审无开放 P0/P1。

### Repair chain：DASHBOARD-PORTABLE-PROVENANCE-RC-001

- Finding IDs：`DASHBOARD-PORTABLE-REPAIR-002-RVW-P1-002`、`DASHBOARD-PORTABLE-REPAIR-002-RVW-AR2-P2-001/002/003`、`DASHBOARD-PORTABLE-REPAIR-002-RVW-AR2-P3-001/002`。
- Closure canonical：`production-build-no-skip-dist|source-fingerprint-stable-across-build|stale-dist-cannot-be-reregistered|unmerged-index-test-green|source-launcher-auto-port-retry|scheduling-doc-matches-runtime|board-and-ledger-consistent|all-regressions-green`。
- `closure_contract_hash=df64d64f7acf227eb3addb2c4f490caf3de5782ca03844f8d3b86308c90fc4bb`；`allowed_files_hash=471cbea1a857d0ff42478207ed9e948765a5dc649a6eceed255458535fec0304`。
- Allowed canonical：当前 `write_scope` 的 17 个 `file:` 项和 1 个 `dir:` 项，按完整字符串升序、单个 LF 连接、末尾无 LF 计算 SHA-256。相对 AR-2 仅新增 `launcher.py`、`test_launcher.py` 与 `skills/ai-dev-flow/README.md`，均位于父任务已经授权的 integration/Skill 文档外层范围；不改变 schema、依赖、安全或验收边界。
- AR-3 目标：删除生产 bundle 复用旧 `dist` 的入口并冻结 build 前后 source fingerprint；补真实 unmerged index 测试；源码 launcher 自动端口启动失败有界重试；同步 Scheduling 文档、看板与 ledger；完整回归和新一轮独立 Review 无开放 P0/P1。
- AR-2 Review 收据：session=`019fb1fd-a09e-7ac2-8d75-7adc1e162b26`，结论 `Needs Fix`，P0/P1/P2/P3=`0/1/3/2`；原 UA6 两个 P1、candidate index P1 和 trailing whitespace P2 均 Closed。
- 机械判定：相对 AR-1 Review 的开放 P1 已从 2 降为 1，存在实质进展；campaign profile=`core_product` 未达到连续 4 次无进展阈值，AR-3 `AutoRepairAllowed`。
- AR-3 Review 收据：session=`019fb213-8f91-79d0-b44b-b170594d8a23`，结论 `Passed`，P0/P1/P2/P3=`0/0/1/2`；bundle provenance P1 Closed。剩余 P2 是源码 launcher 的端口可用性检查位于 retry 外，P3 是看板表格与 diff 标识漂移。
- AR-4：不扩 scope、不改变 closure；把自动端口 `_assert_port_available` 纳入同一 3 次有界重试，显式端口仍立即失败；补确定性首轮 `EADDRINUSE` 后换端口成功及显式端口不改号测试，并同步 P3 收据。Review 已 Passed 且 P1=0，AR-4 只关闭已知非阻断 finding。
- AR-4 Review 收据：session=`019fb222-e5e3-7c02-ae55-d8577dca5831`，结论 `Passed`，P0/P1/P2/P3=`0/0/0/1`；端口 P2 与看板 P3 Closed。唯一 P3 是本 TASK 尾部残留“AR-3 待复审”文字，已严格按 Reviewer 的机械关闭标准同步为当前 AR-4 收据，未改变代码、scope、authority 或 Review 结论。

## Outcome

- Base / Diff：base=51d4eaa30dfb7a88dc0a7bb035b31beccabab053;diff=current-working-tree-ar4
- 隔离位置：`D:\open-source\ai-dev-flow-wt\dashboard-portable-001` / `codex/dashboard-portable-001`。
- 回滚方式：当前无提交；只逆向应用本 TASK 冻结 scope 的增量。删除、reset 或 Worktree 清理仍需用户另行授权。
- 修改文件：前端改用构建期 Ajv standalone validators 并保持严格 CSP；runtime compatibility 区分历史未声明 schema 与显式不兼容；artifact guard 校验 Git index blob 只能为 base/candidate；bundle build/check 强制先通过 `codegen:check`；对应测试、候选 manifest 与 Skill 运行时 bundle 已同步。
- 验证证据：frontend codegen/typecheck/lint/build、unit 82/82、Chrome 83/83；backend 140/140；AR-4 launcher 12/12、integration 50/50；Skill 85/85；bundle build/check 35 files；artifact guard `baseline_preserved=true / candidate_consistent=true / candidate_index_mismatches=[]`；当前 TASK workflow lint errors=0/violations=0/warnings=1；`git diff --check`、测试端口清理与生产资产 runtime compiler/CSP marker 检查通过。
- 验证异常记录：首次把 frontend 与 integration 并行运行造成双方争用测试端口 5173，并使一项 Git 刷新时序断言未在窗口内完成；终止该测试专用 Vite 进程后，frontend 与 integration 分别串行重跑为 83/83、44/44，产品动态端口与隔离测试均通过。
- Review findings：原 `DASHBOARD-PORTABLE-UA6-P1-001/002` Closed；AR-4 独立 Review `Passed`，P0/P1/P2/P3=`0/0/0/1`，没有开放 P0/P1/P2。唯一记录 P3 已按 Review 指定文字机械同步，无业务 patch。
- UA 动作与结果：CADCat 与 ai-dev-flow 两个真实安装版实例已由用户观察；用户于 2026-07-30 明确宣告“验收通过”，本 repair 随父任务记录 `UA6 Passed / Accepted / User Confirmed`。
- 状态边界：Accepted / Review Passed / UA6 Passed / Uncommitted / Unmerged / Not Released / Not Closed。
- 剩余风险：提交和合并前仍需对完整候选运行新鲜验证与独立只读 Review。
- 下一步：随父任务完成提交前门禁并提交、本地合并；发布和本机同步由独立发布任务记录。
