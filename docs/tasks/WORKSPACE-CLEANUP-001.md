# WORKSPACE-CLEANUP-001：迁移主工作区前端改动并清理旧工作区

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `WORKSPACE-CLEANUP-001`
- `task_type`: `code`
- `task_class`: `D`
- `lifecycle`: `Review`
- `review_status`: `Passed`
- `ua_level`: `UA5`
- `ua_status`: `Pending`
- `commit_status`: `Committed`
- `merge_status`: `Unmerged`
- `merge_authority`: `None`
- `close_authority`: `None`

## 目标与边界

- 目标：把旧本地 `main@36aae03` 的 8 项用户前端改动迁移到最新 `origin/main@dec2dd3` 的独立分支，只保留新主线尚未覆盖且有测试价值的行为，并形成可独立审查的本地提交。
- 目标：在可恢复备份通过后，删除已被 Goal 替代的 `unattended-run-001`、三个 detached LEAN 评估 Worktree 和两个未合并 `backup/dashboard-be-001-*` 分支；最后把本地 `main` 安全快进到远端主线。
- 非目标：不推送、不创建 PR、不合并迁移候选、不发布、不改写历史；不改变 Dashboard 后端、合同、Skill、依赖或已验收 runtime。
- 允许修改：`dashboard/frontend/src/ui/graph/graphView.ts`、`dashboard/frontend/src/ui/graph/layout.ts`、`dashboard/frontend/src/ui/overlays.ts`、`dashboard/frontend/tests/browser/graph.spec.ts`、`dashboard/frontend/tests/browser/real-scale.spec.ts`、`dashboard/frontend/tests/derive.test.ts`、`dashboard/frontend/tests/parallel-display.test.ts`、`dashboard/frontend/tests/overlays.test.ts`、本 TASK 与 `docs/TASK_BOARD.md`。
- 允许清理：`D:\open-source\ai-dev-flow-wt\unattended-run-001`、`D:\open-source\ai-dev-flow-lean-eval-003-3cf3776\{full,lite,no-skill}`、本地分支 `codex/unattended-run-001` 与两个 `backup/dashboard-be-001-*`；所有待删除内容必须先在 `C:\Users\92336\.codex-backups\ai-dev-flow\cleanup-20260801-002901` 留下可恢复收据。
- 禁止修改：其他业务文件、正式本机 Skill、远端分支、tag、release、deploy；禁止 force push、reset、历史改写或删除未备份内容。

## 依赖与授权

- 前置依赖：页面修复、性能优化和 Goal 已通过 PR #5/#6 合并；四个交付 TASK 已 Closed；清理前备份已创建并通过 bundle verify。
- Base commit：`dec2dd352deb49e31b5d69d204169863fac90ccd`
- 已有 authority：用户于 2026-08-01 在收到“迁移并验证 8 项前端改动、备份后删除 UnattendedRun/LEAN/backup 分支并更新本地 main”的推荐方案后明确回复“自动处理”，授权本地提交和上述精确清理。
- 未授权动作：push、PR、merge、release、tag、deploy、远端写入、Accepted 或 Closed。
- 执行位置：`codex/workspace-cleanup-001` / `D:\open-source\ai-dev-flow-wt\workspace-cleanup-001`。

## 路由与风险

- 路由：`Controlled`
- Policy 输入：D 类；requested actions=`local commit, irreversible cleanup`；risk flags=`shared_component, tests_do_not_cover_oracle, irreversible_action`；用户界面行为需要 UA5，删除必须有可恢复备份。
- Reviewer 闸门：Required；本地提交前执行同 Harness 隔离只读 Review。
- 停止条件：迁移覆盖新主线已验收行为、需要修改八文件清单外业务代码、前端验证失败、备份不可恢复、待删除路径或分支与冻结清单不一致。

## 完成标准与验证

- 完成标准：有效前端残留在最新主线上形成范围精确、验证通过、独立 Review Passed 的本地候选提交；其余冻结残留可恢复地清理，本地 `main` 快进且干净。
- 验证命令或检查：frontend `npm run verify`、定向浏览器/单元测试、Workflow Contract lint、`git diff --check`、独立只读 Review、备份 hash/bundle、最终全 Worktree/branch 状态盘点。
- [x] 八项旧改动完成三方迁移；已被新主线覆盖的 hunk 不重复引入，保留行为有明确回归测试。
- [x] frontend `npm run verify` 全部通过，运行时/Skill 不发生变化。
- [x] 独立只读 Review Passed，无开放 P0/P1/P2。
- [x] 形成本地精确提交；状态保持 Unmerged / Not Pushed / Not Released / Not Closed。
- [x] 所有清理对象均有可恢复备份；指定 Worktree/分支删除，本地 `main` 快进且干净。
- [ ] `git diff --check` 通过，diff 可归属当前 TASK。

## Repair Chain Ledger（仅进入 repair 时填写）

- Repair chain：Round 1；`WORKSPACE-CLEANUP-RVW-P2-001`（旧格式成功推断被误报为可能缺失，且漏掉真正的 `E_LEGACY_CONFLICT`）与 `WORKSPACE-CLEANUP-RVW-P2-002`（overlay 语义覆盖不足、title 空数组可假通过）；P0/P1/P2/P3=`0/0/2/0`；本轮只在原 allowlist 内修复并复审。

## Outcome

- Base / Diff：base=dec2dd352deb49e31b5d69d204169863fac90ccd;diff=dec2dd352deb49e31b5d69d204169863fac90ccd..9ee319ed4584384bd8afce7dec8ec8ae53fbc2a9
- 隔离位置：`D:\open-source\ai-dev-flow-wt\workspace-cleanup-001` / `codex/workspace-cleanup-001`。
- 回滚方式：迁移候选提交前可用备份 patch 重新建立；提交后只使用普通 `git revert`；清理对象从 `C:\Users\92336\.codex-backups\ai-dev-flow\cleanup-20260801-002901` 恢复，不使用 reset 或历史改写。
- 修改文件：保留 `overlays.ts` 的 TASK 解析缺口提示、新增 `overlays.test.ts`，并保留 `derive.test.ts` 的无关系任务网格回归与 `parallel-display.test.ts` 的关系标签显示语义回归；同步本 TASK 与看板。`graphView.ts`、`layout.ts`、`browser/graph.spec.ts`、`browser/real-scale.spec.ts` 的旧改动已由新主线等价或更完整覆盖，未重复引入。
- 验证证据：初始定向 Vitest 3 文件 / 34 tests Passed；Round 1 修复后定向 Vitest 3 文件 / 38 tests Passed；修复后 frontend `npm run verify` Passed（codegen check、typecheck、ESLint、7 文件 / 91 unit tests、build、89/89 Playwright）；依赖审计仍报告既有 10 项（3 moderate、6 high、1 critical），本 TASK 未修改依赖或执行自动升级。
- Review findings：Round 2 Passed，P0/P1/P2/P3=`0/0/0/0`；`WORKSPACE-CLEANUP-RVW-P2-001`、`WORKSPACE-CLEANUP-RVW-P2-002` Closed；staged diff SHA256 前后均为 `a9a33989f88491b6787cc29a9ddbeeead33aeed3de932084065eb92851fe058f`。
- UA 动作与结果：UA5 Pending；本任务只形成本地候选，不以提交替代用户界面验收。
- 状态边界：前端候选已本地提交 `9ee319ed4584384bd8afce7dec8ec8ae53fbc2a9`；本任务收据由当前记录提交固化；Unmerged / Not Pushed / Not Released / Not Closed。
- 清理证据：恢复目录 `C:\Users\92336\.codex-backups\ai-dev-flow\cleanup-20260801-002901` 存在且 bundle verify Passed；Unattended 与 3 个 LEAN Worktree 均已删除；`codex/unattended-run-001` 与两个 `backup/dashboard-be-001-*` 本地分支已删除；本地 `main` 干净并快进至 `origin/main@dec2dd3`；当前只剩 `main` 与 `codex/workspace-cleanup-001` 两条本地分支。
- 剩余风险：用户界面提示仍需 UA5；依赖审计既有 10 项不在本 TASK 授权范围内；候选仅在本机，尚未推送或合并。
- 下一步：等待用户 UA5；如需进入主线，另行明确授权 push / PR / merge。
