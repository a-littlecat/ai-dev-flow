# ADF-V010-PROJECT-CONSOLE-FE：Project Console 默认入口

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `ADF-V010-PROJECT-CONSOLE-FE`
- `task_type`: `code`
- `task_class`: `D`
- `lifecycle`: `Review`
- `review_status`: `Passed`
- `ua_level`: `UA5`
- `ua_status`: `Pending`
- `acceptance_authority`: `None`
- `commit_status`: `Committed da82235 + receipt cd728eb`
- `merge_status`: `Unmerged`

## 目标与边界

- 目标：默认入口改为只读 Project Console，首屏准确展示用户待处理、活跃工作、Ready Queue、阻塞、最近变化和数据新鲜度。
- 非目标：不让前端重排队列，不执行命令或写 TASK/Git/runtime，不在用户 UA 前删除 Legacy Action Center。
- 允许修改：总合同第 10.2 节列出的 frontend、console schema/codegen、测试、design QA 与相关 TASK/TASK_BOARD。
- 禁止修改：暂时删除 Action Center、overview、graph 或旧回退测试；新增写接口或 authority 操作。

## 依赖与授权

- 前置依赖：RUNTIME-CONSOLE-BE 阶段完成。
- Base commit：`95bc31d5ebc188bc9acf369c63bde087898953d0`（RUNTIME-CONSOLE-BE delivery head）。
- 已有 authority：依赖满足后的实现、自动验证、真实浏览器检查、只读 Review、commit、push、Draft PR。
- 验收合同：`requires_user_observation=true`；`acceptance_authority=user_only`；`designated_acceptor_allowed=false`。这些是 v0.10 阶段合同要求，在当前 v0.7 Contract 中以正文冻结，不能伪写成当前已获得的 authority。
- 未授权动作：代替用户 UA、Accepted、Closed、Legacy 删除、merge、release、正式 Skill 同步。
- 执行位置：stacked branch `codex/v010-project-console-fe`；Worktree `D:/open-source/ai-dev-flow-wt/v010-project-console-fe`。

## 路由与风险

- 路由：`Controlled`。
- Policy 输入：D 级；公共 UI、真实用户观察、shared component、delivery 风险。
- Reviewer 闸门：Required；自动化最多推进到 `Review Passed / UA Pending / Candidate Ready`。
- 停止条件：无法保留 Legacy 回退、真实项目事实被伪造、需要用户体验判断或用户未授权删除旧入口。

## 完成标准与验证

- 完成标准：总合同第 10.12 节自动化与 Review 条件满足，并严格停在 `Review Passed / UA5 Pending / Candidate Ready`。
- 验证命令或检查：frontend `npm run verify`、真实浏览器 CLI、integration 相关测试、runtime bundle check、workflow lint、diff check 与隔离只读 Review。
- [x] 默认 console；network 与 legacy 保持可用。
- [x] human attention 优先，live/declared/stale 明确区分，多候选不伪造唯一行动。
- [x] 数据来源、新鲜度、错误/stale 状态有可访问文本；前端不重新排序。
- [x] `npm run verify`、真实浏览器、集成测试与独立只读 Review通过。
- [ ] 在真实 CADCat 上完成总合同第 10.11 节用户验收；用户未确认前保持 UA Pending。

## Repair Chain Ledger（仅进入 repair 时填写）

- Round 1：关闭 `ADF-V010-PROJECT-CONSOLE-FE-P1-001/P1-002/P2-001/P2-002`；补齐 Console 事实状态/新鲜度、单飞慢轮询、fixture 明确回退与操作按钮上下文。
- Round 2：继续关闭稳定 finding `ADF-V010-PROJECT-CONSOLE-FE-P1-001`；让 `source_kinds` 在存在 Harness/phase/activity 元数据时仍始终可见。
- 最终独立只读 Review：session=`019fe1b4-e054-7500-b22a-ab233f72fc2c`，`Review Passed`，P0/P1/P2/P3=`0/0/0/0`。

## Outcome

- Base / Diff：base=95bc31d5ebc188bc9acf369c63bde087898953d0;diff=95bc31d..da82235。
- 隔离位置：`codex/v010-project-console-fe` / `D:/open-source/ai-dev-flow-wt/v010-project-console-fe`。
- 回滚方式：提交前丢弃本阶段精确 diff；提交后 revert 本阶段 commit，不改写 RUNTIME-CONSOLE-BE 历史。
- 修改文件：新增 console API/state/view、默认 Console 与 network/legacy 三视图路由、合同 codegen、前端/浏览器测试及 43 文件规范 Runtime bundle；Legacy 文件保留。
- 验证证据：backend `202/202`（skip 2）、Skill `113/113`；frontend codegen/typecheck/lint/build、Vitest `102/102`、Playwright `106/106`；真实便携 Dashboard health=`ready/ready/fresh` 且三视图真实浏览器往返通过；Runtime bundle `43/43`；真实状态矩阵通过。integration 完整套件 `51/52`，唯一失败为 Stage 0 冻结 artifact guard，报告 `baseline_preserved=true`，拒绝当前 stacked 重构差异；无运行态失败。workflow lint `errors=0/violations=0/warnings=1`，唯一 warning 为提交前 lifecycle 历史不可验证。
- Review findings：Round 1 `0/2/2/0`，Round 2 `0/1/0/0`，两轮 AutoRepair 后最终 Review `Passed 0/0/0/0`。
- 状态边界：Candidate Ready / Review Passed / UA5 Pending user_only / Committed da82235 + receipt cd728eb / Pushed / Draft PR #17 / Unmerged / Not Released / Not Closed。
- 剩余风险：自动化、真实浏览器 Design QA 和独立 Review 不能替代用户用 CADCat 与两个真实 Harness 任务完成日常入口体验验收。
- 下一步：停止自动推进，等待真实用户 UA；不得提前执行 LEGACY-RETIRE。
