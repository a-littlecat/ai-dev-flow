# WORKSPACE-CLEANUP-001：迁移主工作区前端改动并清理旧工作区

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `WORKSPACE-CLEANUP-001`
- `task_type`: `code`
- `task_class`: `D`
- `lifecycle`: `Closed`
- `review_status`: `Passed`
- `ua_level`: `UA5`
- `ua_status`: `Passed`
- `ua_evidence`: `docs/tasks/WORKSPACE-CLEANUP-001.md#workspace-cleanup-001-ua5-2026-08-01`
- `acceptance_authority`: `User Confirmed`
- `commit_status`: `Committed`
- `merge_status`: `Merged`
- `merge_authority`: `User Authorized`
- `close_authority`: `User Authorized`

## 目标与边界

- 目标：把旧本地 `main@36aae03` 的 8 项用户前端改动迁移到最新 `origin/main@dec2dd3` 的独立分支，只保留新主线尚未覆盖且有测试价值的行为，并形成可独立审查的本地提交。
- 目标：在可恢复备份通过后，删除已被 Goal 替代的 `unattended-run-001`、三个 detached LEAN 评估 Worktree 和两个未合并 `backup/dashboard-be-001-*` 分支；最后把本地 `main` 安全快进到远端主线。
- 非目标：不推送、不创建 PR、不合并迁移候选、不发布、不改写历史；不改变 Dashboard 后端、合同、Skill、依赖或已验收 runtime。
- 允许修改：`dashboard/frontend/src/ui/graph/graphView.ts`、`dashboard/frontend/src/ui/graph/layout.ts`、`dashboard/frontend/src/ui/overlays.ts`、`dashboard/frontend/tests/browser/graph.spec.ts`、`dashboard/frontend/tests/browser/real-scale.spec.ts`、`dashboard/frontend/tests/derive.test.ts`、`dashboard/frontend/tests/parallel-display.test.ts`、`dashboard/frontend/tests/overlays.test.ts`、本 TASK 与 `docs/TASK_BOARD.md`。
- 允许清理：`D:\open-source\ai-dev-flow-wt\unattended-run-001`、`D:\open-source\ai-dev-flow-lean-eval-003-3cf3776\{full,lite,no-skill}`、本地分支 `codex/unattended-run-001` 与两个 `backup/dashboard-be-001-*`；所有待删除内容必须先在 `C:\Users\92336\.codex-backups\ai-dev-flow\cleanup-20260801-002901` 留下可恢复收据。
- 本轮交付清理只允许删除下方“本轮交付清理精确清单”逐项列出的 4 个分支引用和 18 个 Worktree；清单外对象一律不删。
- 禁止修改：其他业务文件、正式本机 Skill、清单外远端分支、tag、release、deploy；禁止 force push、reset、历史改写或删除未备份内容。

## 依赖与授权

- 前置依赖：页面修复、性能优化和 Goal 已通过 PR #5/#6 合并；四个交付 TASK 已 Closed；清理前备份已创建并通过 bundle verify。
- Base commit：`dec2dd352deb49e31b5d69d204169863fac90ccd`
- 已有 authority：用户于 2026-08-01 在收到“迁移并验证 8 项前端改动、备份后删除 UnattendedRun/LEAN/backup 分支并更新本地 main”的推荐方案后明确回复“自动处理”，授权本地提交和上述精确清理。
- 后续交付授权：用户于 2026-08-01 在明确获知“推送候选分支 → 创建并合并 PR → 写回 Closed → 删除候选分支和可清理 Worktree”的范围后回复“进行彻底交付”，授权 push、PR、merge、Closed 及上述精确 Git 清理。
- 仍未授权动作：release、tag、deploy、历史改写、正式本机 Skill/runtime 变更。
- 执行位置：`codex/workspace-cleanup-001` / `D:\open-source\ai-dev-flow-wt\workspace-cleanup-001`。

## 路由与风险

- 路由：`Controlled`
- Policy 输入：D 类；requested actions=`local commit, irreversible cleanup`；risk flags=`shared_component, tests_do_not_cover_oracle, irreversible_action`；用户界面行为需要 UA5，删除必须有可恢复备份。
- Reviewer 闸门：Required；本地提交前执行同 Harness 隔离只读 Review。
- 停止条件：迁移覆盖新主线已验收行为、需要修改八文件清单外业务代码、前端验证失败、备份不可恢复、待删除路径或分支与冻结清单不一致。

## 本轮交付清理精确清单

- 已合并交付分支引用：本地 `codex/workspace-cleanup-001`、本地 `codex/workspace-cleanup-close-001`、远端 `origin/codex/workspace-cleanup-001`、远端 `origin/codex/workspace-cleanup-close-001`。
- 当前交付 Worktree：`D:\open-source\ai-dev-flow-wt\workspace-cleanup-001`。
- 干净 detached Worktree：
  - `D:\open-source\ai-dev-flow-wt\dashboard-be-001`
  - `D:\open-source\ai-dev-flow-wt\dashboard-be-001-repair-001`
  - `D:\open-source\ai-dev-flow-wt\dashboard-be-002`
  - `D:\open-source\ai-dev-flow-wt\dashboard-edge-label-001`
  - `D:\open-source\ai-dev-flow-wt\dashboard-edge-perf-close-001`
  - `D:\open-source\ai-dev-flow-wt\dashboard-edge-perf-integrate-001`
  - `D:\open-source\ai-dev-flow-wt\dashboard-fe-001`
  - `D:\open-source\ai-dev-flow-wt\dashboard-fe-001-repair-001`
  - `D:\open-source\ai-dev-flow-wt\dashboard-fe-001-repair-002`
  - `D:\open-source\ai-dev-flow-wt\dashboard-idle-perf-001`
  - `D:\open-source\ai-dev-flow-wt\dashboard-integrate-001`
  - `D:\open-source\ai-dev-flow-wt\dashboard-portable-001`
  - `D:\open-source\ai-dev-flow-wt\goal-usage-001`
  - `D:\open-source\ai-dev-flow-wt\rel-003-v090-dashboard`
  - `D:\open-source\ai-dev-flow-wt\rel-004-v091-portable-dashboard`
  - `D:\open-source\ai-dev-flow-wt\repair-campaign-001`
  - `D:\open-source\ai-dev-flow-wt\repair-escalation-001`
- 每个 Worktree 删除前必须重新确认：绝对路径与清单完全一致、`git status --porcelain` 为空；旧快照必须仍为 detached 且 HEAD=`dec2dd352deb49e31b5d69d204169863fac90ccd`，并确认该提交是最终 `origin/main` 的 ancestor；交付 Worktree 必须等 Closed 回执 PR 合并、分支为最终 `origin/main` ancestor 后再删除。
- 每个分支删除前必须重新确认：对应 PR 已 Merged、分支 tip 是最终 `origin/main` 的 ancestor、没有 Worktree 正在占用；仅使用普通删除，不使用 force。远端不存在时视为已清理，不把失败重试为强制操作。
- 恢复依据：旧 detached Worktree 的 HEAD=`dec2dd3` 已由 `origin/main` 保留；两个交付分支的全部提交由 PR #7 与 Closed 回执 PR 的 `main` 历史保留；因此删除的是额外 checkout/ref，不删除唯一提交。清理后执行 `git worktree prune` 并复核只剩主 Worktree。

## 完成标准与验证

- 完成标准：有效前端残留在最新主线上形成范围精确、验证通过、独立 Review Passed 的本地候选提交；其余冻结残留可恢复地清理，本地 `main` 快进且干净。
- 验证命令或检查：frontend `npm run verify`、定向浏览器/单元测试、Workflow Contract lint、`git diff --check`、独立只读 Review、备份 hash/bundle、最终全 Worktree/branch 状态盘点。
- [x] 八项旧改动完成三方迁移；已被新主线覆盖的 hunk 不重复引入，保留行为有明确回归测试。
- [x] UA5 文案修复后 frontend `npm run verify` 全部通过，运行时/Skill 不发生变化。
- [x] UA5 文案修复完成独立只读 Review Passed，无开放 P0/P1/P2。
- [x] UA5 文案修复形成本地精确提交；状态保持 Unmerged / Not Pushed / Not Released / Not Closed。
- [x] 所有清理对象均有可恢复备份；指定 Worktree/分支删除，本地 `main` 快进且干净。
- [x] `git diff --check` 通过，diff 可归属当前 TASK。
- [x] 候选分支通过 PR #7 合并到 `main`，merge commit=`55ce8af849cc6e415122edab7fcfab8d149ae6a0`。
- [x] 用户明确授权彻底交付与 Closed；本回执合并后任务生命周期关闭。

## Repair Chain Ledger（仅进入 repair 时填写）

- Repair chain：Round 1；`WORKSPACE-CLEANUP-RVW-P2-001`（旧格式成功推断被误报为可能缺失，且漏掉真正的 `E_LEGACY_CONFLICT`）与 `WORKSPACE-CLEANUP-RVW-P2-002`（overlay 语义覆盖不足、title 空数组可假通过）；P0/P1/P2/P3=`0/0/2/0`；本轮只在原 allowlist 内修复并复审。
- Repair chain：Round 2；`WORKSPACE-CLEANUP-UA5-P2-001`（顶部总错误为 90、提示只显示 89 条 ingestion error，未明确统计口径）；RED=`90 与 89 看似矛盾`；GREEN=`同一提示明确总错误数与其中 ingestion error 数`；SIGNAL=`CADCat 真实快照 + overlay 单元测试`；只修改原 allowlist 内提示、测试与任务记录。

## 用户验收反馈 / 实机测试反馈

<a id="workspace-cleanup-001-ua5-2026-08-01"></a>

- 2026-08-01 UA5：用户在 CADCat 真实页面指出顶部显示“错误 90”，提示显示“89 条”，询问为何不一致；只读诊断确认第 90 条为 `E_BOARD_PARSE`，不属于可能导致 TASK 未纳入的 ingestion error。用户确认采用“总错误数 + 其中影响 TASK 解析的错误数”同屏表述；UA5 继续 Pending，不把修改授权写成验收通过。
- 2026-08-01 UA5 复验：真实 CADCat 页面显示“当前共检测到 90 条错误，其中 89 条属于 TASK 解析或 Contract 不兼容错误……当前显示 14 个已解析任务”；用户随后明确回复“验收通过”。记录为 UA5 Passed / User Confirmed / Accepted；不扩展 push、PR、merge、release、tag、deploy 或 Closed 权限。

## Outcome

- Base / Diff：base=dec2dd352deb49e31b5d69d204169863fac90ccd;diff=dec2dd352deb49e31b5d69d204169863fac90ccd..50a53b77366d45367ca7e992270e7635cdb6c67f
- 隔离位置：`D:\open-source\ai-dev-flow-wt\workspace-cleanup-001` / `codex/workspace-cleanup-001`。
- 回滚方式：迁移候选提交前可用备份 patch 重新建立；提交后只使用普通 `git revert`；清理对象从 `C:\Users\92336\.codex-backups\ai-dev-flow\cleanup-20260801-002901` 恢复，不使用 reset 或历史改写。
- 修改文件：保留 `overlays.ts` 的 TASK 解析缺口提示、新增 `overlays.test.ts`，并保留 `derive.test.ts` 的无关系任务网格回归与 `parallel-display.test.ts` 的关系标签显示语义回归；同步本 TASK 与看板。`graphView.ts`、`layout.ts`、`browser/graph.spec.ts`、`browser/real-scale.spec.ts` 的旧改动已由新主线等价或更完整覆盖，未重复引入。
- 验证证据：UA5 repair 定向 overlays 6/6 Passed；提交前新鲜 frontend `npm run verify` Passed（codegen check、typecheck、ESLint、unit 91/91、build、Playwright 89/89）；Workflow Contract lint 0 errors / 0 violations；`git diff --check` Passed。依赖审计既有 10 项（3 moderate、6 high、1 critical），本 TASK 未修改依赖或执行自动升级。
- Review findings：Round 3 Passed，`WORKSPACE-CLEANUP-UA5-P2-001` Closed，P0/P1/P2/P3=`0/0/0/0`；staged diff SHA256 前后均为 `da85bded2ff95b4f907e63724d318eb36bfaff85c37593a8dc01ae4d369f1d9b`。
- UA 动作与结果：UA5 Passed；用户在真实 CADCat 页面复验 90 / 89 同屏统计口径后明确回复“验收通过”，acceptance authority=`User Confirmed`。
- 合并目标与事实证据：目标分支=`main`；候选最终提交 `50a53b77366d45367ca7e992270e7635cdb6c67f` 已通过 [PR #7](https://github.com/a-littlecat/ai-dev-flow/pull/7) 合并，GitHub merge commit=`55ce8af849cc6e415122edab7fcfab8d149ae6a0`。
- 状态边界：Review Passed / UA5 Passed / User Confirmed / Committed / PR #7 Merged / Not Released / Closed；本次授权不包含 tag、release、deploy 或正式本机 Skill/runtime 变更。
- 清理证据：恢复目录 `C:\Users\92336\.codex-backups\ai-dev-flow\cleanup-20260801-002901` 存在且 bundle verify Passed；Unattended 与 3 个 LEAN Worktree 均已删除；`codex/unattended-run-001` 与两个 `backup/dashboard-be-001-*` 本地分支已删除；功能合并后本地 `main` 已快进至 `origin/main@55ce8af`。Closed 回执合并后仅执行“本轮交付清理精确清单”，清单外对象一律不删。
- 验收服务：本地 45173/45174 端口及对应 Python/Node 进程已停止，未留下常驻验收服务。
- 剩余风险：依赖审计既有 10 项不在本 TASK 授权范围内；未执行自动依赖升级。该风险不由本 TASK 引入，也不阻塞本次已验收界面修复交付。
- 下一步：无产品交付动作；Closed 回执合并后完成已授权的精确 Git 整理，不执行 tag、release、deploy 或正式本机 Skill/runtime 变更。
