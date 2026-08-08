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
- `commit_status`: `Uncommitted`
- `merge_status`: `Unmerged`

## 目标与边界

- 目标：默认入口改为只读 Project Console，首屏准确展示用户待处理、活跃工作、Ready Queue、阻塞、最近变化和数据新鲜度。
- 非目标：不让前端重排队列，不执行命令或写 TASK/Git/runtime，不在用户 UA 前删除 Legacy Action Center。
- 允许修改：总合同第 10.2 节列出的 frontend、console schema/codegen、测试、design QA 与相关 TASK/TASK_BOARD。
- 禁止修改：暂时删除 Action Center、overview、graph 或旧回退测试；新增写接口或 authority 操作。

## 依赖与授权

- 前置依赖：RUNTIME-CONSOLE-BE 阶段完成。
- Base commit：`ab0f8fd`（普通 merge 吸收 RUNTIME-CONSOLE-BE follow-up `626e65d` 后的当前 stacked repair base；原始 #17 实现基线 `95bc31d` 保留在历史收据）。
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
- [x] 外部复审修复后的 `npm run verify`、真实浏览器、集成测试与新独立只读 Review 通过。
- [ ] 在真实 CADCat 上完成总合同第 10.11 节用户验收；用户未确认前保持 UA Pending。

## Repair Chain Ledger（仅进入 repair 时填写）

- Round 1：关闭 `ADF-V010-PROJECT-CONSOLE-FE-P1-001/P1-002/P2-001/P2-002`；补齐 Console 事实状态/新鲜度、单飞慢轮询、fixture 明确回退与操作按钮上下文。
- Round 2：继续关闭稳定 finding `ADF-V010-PROJECT-CONSOLE-FE-P1-001`；让 `source_kinds` 在存在 Harness/phase/activity 元数据时仍始终可见。
- 最终独立只读 Review：session=`019fe1b4-e054-7500-b22a-ab233f72fc2c`，`Review Passed`，P0/P1/P2/P3=`0/0/0/0`。
- 外部 P2/P3：刷新改为 visible `2s` / hidden `10s` / failure exponential backoff；展示 `status_summary`；`why_now_codes` 映射为用户可读原因，机器码仅保留在折叠诊断字段；`navigator.clipboard` 不可用或被拒绝时降级到本地选择复制。对应 unit 与真实浏览器回归已补充；上述历史 Passed 收据不可替代当前修复后的新 Review。
- Fresh 验证：backend `204/204`（skip 2）、Skill `119/119`、frontend Vitest `109/109` 与 Playwright `108/108`、typecheck/lint/build/codegen、Runtime bundle `43/43`、workflow lint `0 errors / 0 violations / 1 warning`、diff check 均通过。Python 3.13 full integration 为 `51/52`，唯一失败是冻结 artifact guard，`baseline_preserved=true`；portable、真实 proxy、真实异常 state-matrix 等其余 51 项均通过。
- Review session `019fe259-ae28-7772-a8d8-3bdd29501821` 为 `Needs Fix 0/1/1/0`：`P1-003` 指出 `ACTIVE_RUNTIME_SESSION` 缺用户文案，`P2-003` 指出当前 stacked repair base 落后。修复：补齐活跃会话文案，并由单测直接读取 ConsoleBuilder 源码、覆盖其全部 7 个固定原因码；当前 base/diff 更新为 `ab0f8fd..working-tree`。等待修复后新隔离 Review。
- 修复后新隔离只读 Review session `019fe25f-c7bd-7ad3-8d94-91b42f2b3118` 为 `Passed 0/0/0/0`；`P1-003`、`P2-003` 均 Closed，无开放 finding。Reviewer 复核 7/7 ConsoleBuilder 固定码、ActionEngine 已知原因码、浏览器报告、43/43 Runtime bundle 与当前 stacked ancestry；未代替用户 UA。

## Outcome

- Base / Diff：base=ab0f8fd;diff=ab0f8fd..working-tree。
- 隔离位置：`codex/v010-project-console-fe` / `D:/open-source/ai-dev-flow-wt/v010-project-console-fe`。
- 回滚方式：提交前丢弃本阶段精确 diff；提交后 revert 本阶段 commit，不改写 RUNTIME-CONSOLE-BE 历史。
- 修改文件：新增 console API/state/view、默认 Console 与 network/legacy 三视图路由、合同 codegen、前端/浏览器测试及 43 文件规范 Runtime bundle；Legacy 文件保留。
- 验证证据：backend `204/204`（skip 2）、Skill `119/119`；frontend codegen/typecheck/lint/build、Vitest `109/109`、Playwright `108/108`；visible/hidden 轮询、Clipboard 降级、status/why-now 文案、真实便携 Dashboard 与真实异常 state-matrix 均通过；Runtime bundle `43/43`。Python 3.13 integration 完整套件 `51/52`，唯一失败为 Stage 0 冻结 artifact guard，报告 `baseline_preserved=true`，拒绝当前 stacked 重构差异；无运行态失败。workflow lint `errors=0/violations=0/warnings=1`，唯一 warning 为提交前 lifecycle 历史不可验证。
- Review findings：外部修复首轮 session `019fe259-ae28-7772-a8d8-3bdd29501821` 为 `Needs Fix 0/1/1/0`；修复后 session `019fe25f-c7bd-7ad3-8d94-91b42f2b3118` 为 `Passed 0/0/0/0`，全部稳定 finding Closed。
- 状态边界：External Repair Review Passed / UA5 Pending user_only / Current Repair Uncommitted / Draft PR #17 / Unmerged / Not Released / Not Synced / Not Accepted / Not Closed / Legacy Retire Not Started。
- 剩余风险：自动化、真实浏览器 Design QA 和独立 Review 不能替代用户用 CADCat 与两个真实 Harness 任务完成日常入口体验验收。
- 下一步：仅提交/push #17，并停在 `UA5 Pending user_only`，等待用户在真实 CADCat 与两个真实 Harness 任务上主动开始验收；不得提前执行 LEGACY-RETIRE。
