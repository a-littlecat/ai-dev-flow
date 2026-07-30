# DASHBOARD-PORTABLE-001：支持跨项目 Dashboard 与多实例隔离

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `DASHBOARD-PORTABLE-001`
- `task_type`: `code`
- `task_class`: `D`
- `lifecycle`: `Accepted`
- `review_status`: `Passed`
- `ua_level`: `UA6`
- `ua_status`: `Passed`
- `ua_evidence`: `docs/tasks/DASHBOARD-PORTABLE-001.md#dashboard-portable-001-ua6-复验通过-2026-07-30`
- `acceptance_authority`: `User Confirmed`
- `commit_status`: `Committed`
- `merge_status`: `Unmerged`

## Scheduling

- `scheduling_schema`: `ai-dev-flow/scheduling/v1`
- `priority`: `high`
- `depends_on`: `REL-003#commit_status=Committed;REL-003#merge_status=Merged;REL-003#review_status=Passed;REL-003#ua_status=Passed`
- `replaces`: `none`
- `discovered_from`: `DASHBOARD-INTEGRATE-001`
- `parent`: `DASHBOARD-001`
- `conflicts_with`: `none`
- `parallel_intent`: `serial`
- `write_scope`: `dir:dashboard/backend/src/ai_dev_flow_dashboard;dir:dashboard/backend/tests;dir:dashboard/integration;file:dashboard/README.md;dir:skills/ai-dev-flow/dashboard;file:skills/ai-dev-flow/scripts/dashboard.py;file:skills/ai-dev-flow/README.md;file:docs/tasks/DASHBOARD-PORTABLE-001.md;file:docs/TASK_BOARD.md`
- `module_locks`: `dashboard-runtime;dashboard-api;skill-distribution`
- `worktree`: `required`
- `branch_hint`: `codex/dashboard-portable-001`
- `risk_flags`: `architecture;build_or_deploy_config;core_execution_path;historical_p1;public_api;real_environment;security;shared_component;tests_do_not_cover_oracle`

## 目标与边界

- 目标：任意包含 `docs/tasks/` 的本地 Git 项目可通过外部安装的 `ai-dev-flow` Skill 启动只读 Dashboard，不要求项目内复制 Skill，也不要求保留源码仓库、Node.js 或 Vite 开发依赖。
- 目标：Skill 安装包包含启动入口、必要后端运行时与已构建前端；源码仓库旧 launcher 继续兼容。
- 目标：默认自动分配 loopback 端口，并支持显式端口；每次启动使用独立实例 ID、运行目录和状态文件，停止单个实例不影响其他实例。
- 目标：启动前严格检查 Skill `VERSION`、Workflow Contract schema、Scheduling schema 与 Dashboard 支持范围；运行中固定启动快照，检测 Skill 更新后提示重启而不热切换。
- 目标：继续保持无写 API、不修改项目/Skill/Git/Worktree、不授予治理状态 authority、未知事实不猜测。
- 非目标：不发布新版本、不同步或修改本机已安装 Skill、不创建系统级命令、不引入新生产依赖、不改变 Dashboard wire schema 或治理语义。
- 允许修改：仅限 Workflow Contract 路径注入、Dashboard 集成/分发运行时、对应测试与两份启动文档，以及本 TASK/看板投影。
- 禁止修改：Workflow Contract Reader、治理 policy、TASK schema、Scheduling schema、Dashboard wire schema、Git 历史、其他任务和仓库外文件；禁止 commit、merge、push、release、外部同步、删除或 `Closed`。

## 依赖与授权

- 前置依赖：`REL-003` 已 `Accepted / Review Passed / UA7 Passed / Committed / Merged / Released v0.9.0`。
- Base commit：`51d4eaa30dfb7a88dc0a7bb035b31beccabab053`
- 已有 authority：用户提供 P1 缺陷、必须能力和验收标准，授权在本 TASK 精确 allowlist 内实施、运行本地测试、创建临时测试项目/运行目录、启动和停止 loopback 测试实例、执行隔离只读 Review与最多两轮有限 repair。
- 新 repair authority：用户于 2026-07-30 在收到精确范围后回复“授权”，允许创建并执行 `DASHBOARD-PORTABLE-REPAIR-001`，只关闭 `DASHBOARD-PORTABLE-RVW-P1-002`，并在冻结 scope 内持续修复与独立复审直到无开放 P0/P1。
- 新 UA repair authority：用户于 2026-07-30 明确要求“继续修复直至可验收”，允许创建并执行 `DASHBOARD-PORTABLE-REPAIR-002`，在冻结 scope 内关闭 `DASHBOARD-PORTABLE-UA6-P1-001/002`、持续验证与独立复审，并重启双真实项目；不授权放宽安全边界、Accepted 或 delivery。
- UA6 与交付授权：用户于 2026-07-30 观察两个真实项目页面后明确回复“可以了，验收通过，提交并合并，然后同步到本机，最后推送并发版”，据此记录 `UA6 Passed / Accepted / User Confirmed`，并授权本任务提交、本地合并，以及通过独立发布任务执行本机 Skill 同步、`main` push、annotated tag 和正式 GitHub Release。
- README 授权：同一用户消息明确要求重写 GitHub 根 README，介绍新版能力并可删除旧版内容；该文档与版本/发布收据不并入本任务实现 diff，而由后续独立发布任务冻结范围并验证。
- 仍未授权动作：新增/升级生产依赖、放宽安全边界、删除分支/Worktree、强制推送、历史改写或 `Closed`。
- 执行位置：独立 Worktree `D:\open-source\ai-dev-flow-wt\dashboard-portable-001`，分支 `codex/dashboard-portable-001`。

## 路由与风险

- 路由：`Controlled`
- Policy 输入：`task_class=D`、`ua_level=UA6`；风险包含 architecture、build/deploy config、core execution path、historical P1、public API、real environment、security、shared component 和 tests-do-not-cover-oracle。
- Reviewer 闸门：`Required`；自动验证完成后必须由当前 Harness 的隔离只读 Reviewer 检查，开放 P0/P1 时不得请求 UA6。
- 主要风险：外部 Reader 与项目冻结输入混用、动态端口存在 TOCTOU、分发副本与源码漂移、多实例状态串用、静态前端绕过既有安全头、Skill 更新导致运行中模块混载。
- 停止条件：需要修改治理 schema/policy、引入未授权生产依赖、写入项目或 Skill、放宽 loopback/只读边界、无法形成确定性 bundle parity 或实例清理证据。

## 完成标准与验证

- 完成标准：外部 Skill、安装运行时、双实例隔离、版本门禁、只读安全和向后兼容验收项全部形成确定性证据。
- 验证命令或检查：运行 backend、integration、frontend、Skill 全量测试，真实 CADCat 启停，bundle parity、artifact guard、workflow lint、Git/diff 和端口/进程清理检查。
- [x] 外部 Skill：CADCat 类普通 Git 项目不含项目内 Skill 时，可通过显式 `--skill-root` 与已安装 Skill 自动发现启动并读取 TASK/TASK_BOARD。
- [x] 独立运行时：从隔离复制的 Skill 安装目录启动成功，PATH 不要求 Node/Vite，且不引用源码仓库路径。
- [x] 单项目实时性：TASK 保存后 SSE revision 更新；Git dirty、branch、HEAD 和 Worktree 变化刷新。
- [x] 多项目隔离：两个项目并行启动均可访问，端口、实例 ID、运行目录、状态、TASK/Git/Worktree 不串；停止一个后另一个继续。
- [x] 版本门禁：兼容版本和两个 schema 通过；已声明区块中的不兼容/缺失/重复/格式错误值明确失败；运行中 Skill 与完整 bundle 改变只提示重启且不热加载。
- [x] 只读门禁：项目与 Skill 文件哈希、Git status 启停前后一致，无写 API、无残留监听端口或后台进程。
- [x] 向后兼容：源码仓库旧命令可启动；现有 Contract、snapshot、SSE schema 与全部既有测试不回归。
- [x] 分发一致性：生成器可重复构建 Skill runtime，校验源代码/静态前端与 bundle manifest 一致，禁止手工漂移。
- [x] `git diff --check` 通过，diff 可归属当前 TASK。

## DASHBOARD-PORTABLE-001 UA6 2026-07-30

- UA 动作与结果：真实启动 CADCat 与 ai-dev-flow 自身 Worktree。CADCat 后端实例成功监听 `127.0.0.1:10499` 并生成 13 TASK 快照，但浏览器因生产 CSP 拒绝 Ajv 运行时代码生成而显示空白页；ai-dev-flow 自身 Worktree 在历史 TASK 的 Scheduling schema 兼容检查阶段停止。`UA6 Failed / Not Accepted`。
- 证据：浏览器控制台记录 `EvalError`，说明 `script-src 'self'` 禁止 `new Function`；launcher 记录 `Scheduling schema declaration must appear exactly once in DASHBOARD-FE-001-REPAIR-002.md`。
- 安全边界：CADCat 实例只监听 loopback；本次没有写入 CADCat 项目、外部 Skill 或 Git，也没有授予 acceptance、commit、merge、release 或 Closed authority。

## DASHBOARD-PORTABLE-001 UA6 复验通过 2026-07-30

- 验收环境：用户在本机同时检查 CADCat `127.0.0.1:5084` 与 ai-dev-flow `127.0.0.1:5082` 两个真实项目页面。
- 验收范围：页面正常渲染、两个实例和项目数据保持隔离，并结合实际 CADCat 任务关系展示确认新版跨项目工作方式可用。
- 验收结果：用户明确回复“可以了，验收通过”；记录为 `UA6 Passed / User Confirmed / Accepted`，不重复要求用户验收。
- 交付授权：同一消息另行授权提交、本地合并、本机同步、GitHub push 和正式发版；这些动作仍按独立交付门禁记录，不由 UA 状态自动推导。
- 权限边界：未授权删除分支/Worktree、强制推送、历史改写、放宽只读安全边界或 `Closed`。

## Outcome

- Base / Diff：base=51d4eaa30dfb7a88dc0a7bb035b31beccabab053;diff=base..working-tree-repair-review-1
- 提交事实证据：功能提交 `47548134ad4168850f919f53a4bf5453dc818bde`（`feat(dashboard): support portable multi-project runtime`）。
- 隔离位置：`D:\open-source\ai-dev-flow-wt\dashboard-portable-001`，分支 `codex/dashboard-portable-001`。
- 回滚方式：放弃本 Worktree 未提交 diff；若未来形成提交，只通过新的逆向提交回滚，不改写历史。
- 修改文件：Dashboard backend/runtime、integration launcher/build/tests、Skill 分发 bundle/入口与两份 README、本 TASK 和 TASK_BOARD；未修改 wire schema、治理 policy、依赖或本机安装 Skill。
- 验证证据：backend 140/140、AR-4 integration 50/50、frontend unit 82/82 + Chrome 83/83、Skill 85/85、bundle 35 文件 parity、candidate artifact guard、TASK lint 与 `git diff --check` 均通过。
- 验证证据：隔离双项目真实进程覆盖自动端口、无 Node PATH、入口自动发现、SSE、dirty/HEAD/branch/linked Worktree、独立停止和零残留；CADCat 源码 launcher 得到 fresh snapshot，显示 13 个规范 TASK（含 PROJECT-PLOT-CONFIG-001），启停前后 TASK 哈希和 Git status 不变。
- 验证命令与结果：`python -m unittest` backend/integration/Skill 全量、`npm run verify`、`build_skill_runtime.py --check`、`quick_validate.py`、真实 CADCat/双项目脚本均已运行并通过。
- Review findings：`DASHBOARD-PORTABLE-REPAIR-002` 已关闭生产 CSP 空白页、历史 Scheduling 兼容、候选制品索引、旧 dist 重新合法化和源码 launcher 端口竞态；提交前 `DASHBOARD-PORTABLE-REPAIR-003` 又关闭 Windows LF、schema 启动冻结与实时回退缺口。最终独立只读 Review session=`019fb2af-da14-7e20-b515-d1de3beb6663` 为 `Passed`，P0/P1/P2=`0/0/0`。
- UA 动作与结果：先前真实 UA6 Failed 证据保留在上节；修复后 CADCat 与 ai-dev-flow 两个隔离安装版实例在 `127.0.0.1:5084` / `127.0.0.1:5082` 正常渲染。用户已实际观察并于 2026-07-30 明确宣告“验收通过”，记录为 `UA6 Passed / Accepted / User Confirmed`。
- 状态边界：Accepted / Review Passed / UA6 Passed / Committed / Unmerged / Not Released / Not Closed。
- 剩余风险：当前实现与提交前门禁已通过；发布、本机同步、push 与 Release 仍由独立发布任务记录，不从本任务 Acceptance 自动推导。
- 下一步：按用户授权提交并本地合并；随后在独立发布任务中完成 README 重写、版本升级、本机同步、GitHub push/tag/Release。
