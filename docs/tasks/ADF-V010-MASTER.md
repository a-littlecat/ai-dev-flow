# ADF-V010-MASTER：ai-dev-flow v0.10.0 整体重构

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `ADF-V010-MASTER`
- `task_type`: `plan`
- `task_class`: `D`
- `lifecycle`: `In Progress`
- `review_status`: `Pending`
- `ua_level`: `UA5`
- `ua_status`: `Pending`
- `commit_status`: `Committed`
- `merge_status`: `Unmerged`

## 目标与边界

- 目标：按《ai-dev-flow v0.10.0 整体重构执行规格》分阶段交付治理核心拆分、能力驱动 Review、Runtime Session、Project Console、Legacy 退役和 v0.10.0 发布。
- 非目标：不把六个阶段压成一个补丁；不新增数据库、云服务、遥测、写 API、插件市场或第二套 TASK/Git/排序引擎。
- 允许修改：仅限各阶段 TASK 明确列出的范围，以及本 TASK 与 `docs/TASK_BOARD.md` 的事实收据。
- 禁止修改：阶段依赖未满足的后续范围；未经真实用户 UA 删除 Legacy；未经显式发布授权执行 tag、Release、正式 Skill 同步或 deploy。

## 依赖与授权

- 前置依赖：总合同 `C:/Users/92336/Downloads/AI_DEV_FLOW_V0.10_CODEX_EXECUTION_SPEC.md`；参考基线 `origin/main@7f2686f1492496adf2a71e2d981772502c7097e9`。
- Base commit：`7f2686f1492496adf2a71e2d981772502c7097e9`。
- 已有 authority：读取、建立阶段分支/Worktree、创建和更新本计划 TASK、阶段内修改与验证、独立只读 Review、本地 commit、push 阶段分支、创建 Draft PR。
- 未授权动作：merge、tag、GitHub Release、deploy、正式 Skill 安装同步、force push、改写历史、删除用户 Worktree、自动 UA、自动 Accepted/Closed。
- 执行位置：首阶段 Worktree `D:/open-source/ai-dev-flow-wt/v010-core-split`；后续采用 stacked branches。

## 路由与风险

- 路由：`Controlled`。
- Policy 输入：D 级；架构、Skill 自修改、公共合同、真实用户观察、delivery/release 风险；确定性验证不能覆盖 Project Console 的最终用户体验。
- Reviewer 闸门：每阶段提交前必须完成隔离、只读 Review，P0/P1 必须关闭。
- 停止条件：范围/authority 扩大、事实源冲突、架构目标冲突、缺少必需外部证据或用户 UA。

## 完成标准与验证

- 完成标准：六个阶段按依赖顺序交付，并严格停在真实用户 UA 与显式发布授权门禁。
- 验证命令或检查：逐阶段执行总合同指定测试、独立只读 Review、diff 检查和生命周期收据核对。
- [ ] CORE-SPLIT、CAPABILITY-REVIEW、RUNTIME-CONSOLE-BE 依序完成阶段验证、Review 和提交边界。
- [ ] PROJECT-CONSOLE-FE 自动化与 Review 通过，并停在真实用户 UA 门禁。
- [ ] 用户真实 UA Passed 且明确同意后，才执行 LEGACY-RETIRE。
- [ ] 用户显式发布授权后，才执行 RELEASE。
- [ ] 每阶段 `git diff --check` 通过，diff 可归属对应 TASK。

## Repair Chain Ledger（仅进入 repair 时填写）

- 未进入 repair。

## Outcome

- Base / Diff：base=7f2686f1492496adf2a71e2d981772502c7097e9
- 修改文件：Stage 0 已建立本 TASK、六份阶段 TASK 与 TASK_BOARD；Stage 1 已完成治理入口、三份 canonical policy、严格 loader、Repair gate、兼容文档与测试，未修改 Dashboard。
- 验证命令与结果：Stage 0 backend `174/174`、Skill `91/91`、frontend Vitest `95/95`、Playwright `96/96`、codegen/typecheck/lint/build 通过；Stage 1 Skill `99/99`、backend `174/174`、workflow lint `0/0/63`、diff/scope 检查通过。Integration 基线 `51` 项为 `1 failure + 1 error`，均为 `origin/main@7f2686f` 的 Dashboard 既有失败。
- Review findings：CORE-SPLIT Round 3 `Passed`，P0/P1/P2/P3=`0/0/0/0`；Master 整体 Review 仍 Pending。
- UA 动作与结果：Project Console 真实 UA 为用户专属，当前 Pending。
- 状态边界：CORE-SPLIT 外部修复 Review Passed、Pushed `56c2aa7`、UA3 Pending；CAPABILITY-REVIEW 外部修复 Review Passed / Fresh Verification Passed / Committed `83ec457` / UA3 Pending。未 merge / release / 正式 Skill 同步 / Accepted / Closed。
- 剩余风险：必须保持 stacked branch 与独立收据，避免后续阶段污染前置阶段。
- 下一步：回写 CAPABILITY-REVIEW 新 Review 收据并提交/push 当前修复，再以普通 merge 更新 Runtime Console stacked branch；不提前进入正式 UA 或 Project Console。
