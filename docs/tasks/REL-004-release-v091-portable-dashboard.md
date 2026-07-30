# REL-004：发布 v0.9.1 跨项目 Dashboard

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `REL-004`
- `task_type`: `document`
- `task_class`: `D`
- `lifecycle`: `Accepted`
- `review_status`: `Passed`
- `ua_level`: `UA7`
- `ua_status`: `Passed`
- `ua_evidence`: `docs/tasks/DASHBOARD-PORTABLE-001.md#dashboard-portable-001-ua6-复验通过-2026-07-30`
- `acceptance_authority`: `User Confirmed`
- `commit_status`: `Committed`
- `merge_status`: `Merged`
- `merge_authority`: `User Authorized`

## Scheduling

- `scheduling_schema`: `ai-dev-flow/scheduling/v1`
- `priority`: `high`
- `depends_on`: `DASHBOARD-PORTABLE-001#commit_status=Committed;DASHBOARD-PORTABLE-001#merge_status=Merged;DASHBOARD-PORTABLE-001#review_status=Passed;DASHBOARD-PORTABLE-001#ua_status=Passed`
- `replaces`: `none`
- `discovered_from`: `DASHBOARD-PORTABLE-001`
- `parent`: `DASHBOARD-001`
- `conflicts_with`: `none`
- `parallel_intent`: `serial`
- `write_scope`: `file:README.md;file:README.en.md;file:dashboard/README.md;file:skills/ai-dev-flow/VERSION;file:skills/ai-dev-flow/CHANGELOG.md;file:skills/ai-dev-flow/README.md;file:skills/ai-dev-flow/references/TASK_TEMPLATE.md;file:skills/ai-dev-flow/references/TASK_TEMPLATE_BRIEF.md;file:skills/ai-dev-flow/references/V0.8_MIGRATION.md;file:skills/ai-dev-flow/tests/test_compact_writer_routing.py;dir:skills/ai-dev-flow/dashboard;file:docs/tasks/REL-004-release-v091-portable-dashboard.md;file:docs/TASK_BOARD.md`
- `module_locks`: `release-identity;skill-distribution;github-release`
- `worktree`: `required`
- `branch_hint`: `codex/rel-004-v091-portable-dashboard`
- `risk_flags`: `external_side_effect;release;shared_component;real_environment`

## 目标与边界

- 目标：把已合并的跨项目 Dashboard 作为 `v0.9.1` 正式发布，重写中英文 GitHub README，使新版安装、启动、多实例隔离、版本门禁与只读边界成为首页主要内容。
- 目标：升级 Skill 版本和发行文档，重新生成内置 Dashboard runtime，并验证仓库源码、发行 bundle 和本机安装 Skill 内容一致。
- 目标：推送 `main`，创建并推送 annotated tag `v0.9.1`，创建非 draft、非 prerelease 的正式 GitHub Release。
- 非目标：不改变治理 policy、Workflow/Scheduling schema、Dashboard wire schema、功能实现或依赖；不删除分支/Worktree，不改写历史，不写 `Closed`。
- 允许修改：仅限本 TASK `write_scope`；本机同步只覆盖已存在且经物理路径审计确认的 `ai-dev-flow` Skill 安装目标。
- 禁止修改：不得写入 CADCat 或其他业务项目，不得强制推送、移动旧 tag、删除目标特有文件、创建未知 Harness 安装目录或放宽安全边界。

## 依赖、授权与发布顺序

- Base commit：`34c79ea`；功能 merge commit=`17ab9be39da028ac08dab8ced267125498db0f56`。
- 用户于 2026-07-30 明确回复“可以了，验收通过，提交并合并，然后同步到本机，最后推送并发版”，并要求重写 GitHub README、介绍新版特性、允许移除旧版内容。
- 该指令分别授权：发布候选 commit、本地 merge、本机已存在 Skill 同步、`main` push、annotated tag `v0.9.1`、tag push 和正式 GitHub Release；不授权 `Closed`、删除或历史改写。
- 固定顺序：版本与文档候选 → 发布前自动回归（由 Codex 执行，无需用户重新 UA）→ 独立只读 Review → commit/本地 merge → 本机 Skill parity → push main → tag/Release → 远端收据。
- 路由：`Controlled`；Reviewer 闸门 `Required`。

## 完成标准与验证

本节的“验证”是发布前自动回归：用于确认 README、版本号、内置 Dashboard runtime 和发布包在交付前仍然一致，由 Codex 自动执行；它不重复、不撤销，也不替代用户已经通过的 UA。

- 完成标准：版本、README、CHANGELOG、模板、Skill runtime 与测试身份一致；本机 Skill parity、远端 main、annotated tag 和正式 GitHub Release 均有可复现证据。
- 验证命令或检查：backend/integration/frontend/Skill 全量、bundle build/check、workflow lint、版本引用扫描、README 命令静态检查、Git diff/status、物理安装路径与 SHA256 manifest、远端 main/tag/Release 查询。
- [x] 中英文 README 以 v0.9.1 跨项目 Dashboard 为主线，启动命令和只读边界准确。
- [x] VERSION/CHANGELOG/模板/测试/runtime manifest 均为 `0.9.1`，Workflow Contract 仍为 `adf/v0.7.0`。
- [x] backend、integration、frontend、Skill、bundle parity、workflow lint 与 diff 检查完成并形成准确证据。
- [x] 独立只读 Review 无开放 P0/P1。
- [x] 发布候选已 commit 并合入本地 `main`。
- [x] 本机已存在 Skill 目标与仓库发行源相对 manifest 一致，且不删除目标特有文件。
- [ ] `main`、annotated tag `v0.9.1` 和正式 GitHub Release 已推送/创建并复核。

## Outcome

- Base / Diff：base=34c79ea;diff=0875bb39f051cc931792f9c414286ca8c1760667
- 隔离位置：`D:\open-source\ai-dev-flow-wt\rel-004-v091-portable-dashboard` / `codex/rel-004-v091-portable-dashboard`。
- 回滚方式：候选提交前逆向应用本 TASK scope；发布后只通过新提交和新版本修正，不移动 tag、不改写历史。
- 修改文件：根目录中英文 README、Dashboard README、VERSION、CHANGELOG、Skill README、两份 TASK 模板、v0.8 迁移说明、版本一致性测试、runtime manifest、本 TASK 与 TASK_BOARD；未修改 Dashboard 功能代码、schema、policy、依赖或锁文件。
- 验证证据：backend `144/144`、Skill `85/85`、frontend unit `82/82`、Playwright Chrome `83/83` 通过；typecheck、ESLint、production build、codegen 均通过。
- 验证证据：runtime bundle build/check `35 files / ok=true`；REL-004 lint=`0 error / 0 violation / 2 expected warnings`；`git diff --check` 通过。
- 验证证据：此前合并检出 integration `50/50` 通过；本发布候选全量运行中一次 HEAD watcher 时序断言未及时刷新、目标复跑通过，另一次 50 项功能执行完成后仅临时目录清理触发 `WinError 32`、对应真实状态矩阵目标复跑通过；测试临时目录已清理且无测试端口或进程残留。
- 验证证据：发布候选提交 `0875bb39f051cc931792f9c414286ca8c1760667`，精确包含本 TASK 允许的 13 个发布文件。
- Review findings：首轮只读 Review session `019fb2df-fd06-79d1-9856-47a445a79b98` 为 `Needs Fix / P0-P3=0/1/1/0`；`REL004-RVW-P1-001` 与 `REL004-RVW-P2-002` 均已修复。第二轮只读 Review session `019fb2ea-9ffa-7281-a006-943cb1022bb8` 为 `Passed / P0-P3=0/0/0/0`，无新增 finding。
- UA 动作与结果：用户已观察两个真实项目页面并明确宣告验收通过，同时明确授权提交、合并、本机同步、push 与正式发版；记录 `UA7 Passed / User Confirmed`。
- 合并目标与事实证据：发布分支 `codex/rel-004-v091-portable-dashboard` 通过 merge commit `139864d5f2cc6e613d710c59a05d3aa691de9492` 合入本地 `main`。
- 当前状态：`Accepted / Review Passed / UA7 Passed / Committed / Merged / Local Sync Verified / Not Released / Not Closed`。

## 本机 Skill 同步收据（2026-07-30）

- 实盘入口：`.agents`、`.codex`、OpenCode、cc-switch 共 4 个；其中 `.codex` 与 OpenCode 是指向 `.agents` 的 Junction，因此实际写入 `.agents` 与 `.cc-switch` 两份物理副本。
- 同步方式：仅以仓库 `skills/ai-dev-flow` 覆盖同名源文件，不删除目标专有文件，不创建未知安装目录；同步时两个既有 Dashboard 实例均使用独立临时 Skill 副本，未被停止或热替换。
- parity：4 个入口均为 `VERSION=0.9.1`；相对源包 129 个非缓存文件全部 `Missing=0 / Changed=0 / Extra=0`。
- 固定摘要：`dashboard/runtime-manifest.json` SHA256=`b601fb243014fff4e1d11e3cf78a3a793d40898402981e8156e02297f2709600`；`references/CORE.md` SHA256=`96769de002bf9920e2899daeeea86c078f43103f4e7895fe3762efaa7fbd1eef`。
- 同步前备份：`C:\Users\92336\.codex\visualizations\2026\07\30\019fb109-200a-7a20-989b-e57e306fe230\skill-sync-backup-v0.9.1-20260730-2018`。
