# ADF-V010-PROJECT-CONSOLE-FE：Project Console 默认入口

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `ADF-V010-PROJECT-CONSOLE-FE`
- `task_type`: `code`
- `task_class`: `D`
- `lifecycle`: `Review`
- `review_status`: `Pending`
- `ua_level`: `UA5`
- `ua_status`: `Pending`
- `acceptance_authority`: `None`
- `commit_status`: `Committed`
- `merge_status`: `Unmerged`

## 目标与边界

- 目标：默认入口改为只读 Project Console，首屏准确展示用户待处理、活跃工作、Ready Queue、阻塞、最近变化和数据新鲜度。
- 非目标：不让前端重排队列，不执行命令或写 TASK/Git/runtime，不在用户 UA 前删除 Legacy Action Center。
- 允许修改：总合同第 10.2 节列出的 frontend、console schema/codegen、测试、design QA 与相关 TASK/TASK_BOARD。
- 禁止修改：暂时删除 Action Center、overview、graph 或旧回退测试；新增写接口或 authority 操作。

## 依赖与授权

- 前置依赖：RUNTIME-CONSOLE-BE 阶段完成。
- Base commit：`869a8d3`（普通 merge 吸收当前 RUNTIME-CONSOLE-BE 分支 head；历史 repair base 仅保留在旧收据中）。
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
- [x] 外部 findings 修复后的 `npm run verify`、真实浏览器、集成测试与 same-Harness 内部隔离只读 Review 通过；跨 Harness 完整外部复审仍 Pending。
- [ ] 在真实 CADCat 上完成总合同第 10.11 节用户验收；用户未确认前保持 UA Pending。

## Repair Chain Ledger（仅进入 repair 时填写）

- Round 1：关闭 `ADF-V010-PROJECT-CONSOLE-FE-P1-001/P1-002/P2-001/P2-002`；补齐 Console 事实状态/新鲜度、单飞慢轮询、fixture 明确回退与操作按钮上下文。
- Round 2：继续关闭稳定 finding `ADF-V010-PROJECT-CONSOLE-FE-P1-001`；让 `source_kinds` 在存在 Harness/phase/activity 元数据时仍始终可见。
- 最终独立只读 Review：session=`019fe1b4-e054-7500-b22a-ab233f72fc2c`，`Review Passed`，P0/P1/P2/P3=`0/0/0/0`。
- 外部 P2/P3：刷新改为 visible `2s` / hidden `10s` / failure exponential backoff；展示 `status_summary`；`why_now_codes` 映射为用户可读原因，机器码仅保留在折叠诊断字段；`navigator.clipboard` 不可用或被拒绝时降级到本地选择复制。对应 unit 与真实浏览器回归已补充；上述历史 Passed 收据不可替代当前修复后的新 Review。
- Fresh 验证：backend `204/204`（skip 2）、Skill `119/119`、frontend Vitest `109/109` 与 Playwright `108/108`、typecheck/lint/build/codegen、Runtime bundle `43/43`、workflow lint `0 errors / 0 violations / 1 warning`、diff check 均通过。Python 3.13 full integration 为 `51/52`，唯一失败是冻结 artifact guard，`baseline_preserved=true`；portable、真实 proxy、真实异常 state-matrix 等其余 51 项均通过。
- Review session `019fe259-ae28-7772-a8d8-3bdd29501821` 为 `Needs Fix 0/1/1/0`：`P1-003` 指出 `ACTIVE_RUNTIME_SESSION` 缺用户文案，`P2-003` 指出当前 stacked repair base 落后。修复：补齐活跃会话文案，并由单测直接读取 ConsoleBuilder 源码、覆盖其全部 7 个固定原因码；当前 base/diff 更新为 `ab0f8fd..working-tree`。等待修复后新隔离 Review。
- 修复后新隔离只读 Review session `019fe25f-c7bd-7ad3-8d94-91b42f2b3118` 为 `Passed 0/0/0/0`；`P1-003`、`P2-003` 均 Closed，无开放 finding。Reviewer 复核 7/7 ConsoleBuilder 固定码、ActionEngine 已知原因码、浏览器报告、43/43 Runtime bundle 与当前 stacked ancestry；未代替用户 UA。
- `ADF-V010-EXT-R2-P1-001`：前端 Ready 区改用 `ready_ambiguity`，文案只描述 Ready 最高排名并列，不再把 active/human 写成“唯一主候选”。Ready 卡片收敛为“可以作为下一项开始 / 尚未授权自动执行 / 开始执行任务”，手动按钮只打开任务路由，不安静授予自动执行 authority。
- 本轮 P3：Clipboard API 与 `execCommand` 都失败时，卡片内显示只读、可选择的完整文本，并把焦点恢复到触发按钮；Playwright 使用真实 DOM 回归覆盖最终失败路径。历史 Passed 收据未被用于本轮 diff。
- 本轮 fresh 验证：backend `207/207`（skip 2）、Skill `119/119`、Vitest `109/109`、Playwright `109/109`、Runtime bundle `43/43`、当前 TASK workflow lint `0 errors / 0 violations / 1 warning`（收据提交前 lifecycle 转换历史不可验）。full integration 因新增 `adf.py` 预检回归从历史 `51/52` 增为当前 `52/53`，唯一失败仍是冻结 artifact guard，`baseline_preserved=true`；不误报全绿。
- 本轮新隔离只读 Review session `019fe37b-1090-7241-80be-52c29ee4ab7` 审查 `31ad2f7..6e89697`，结论 `Passed 0/0/0/0`，无开放 finding。当前 `Review Passed / UA5 Pending user_only`；不授予 merge/release/正式 Skill 同步/Legacy Retire/Accepted/Closed。
- `ADF-V010-EXT-R3-P1-001`（状态记录）：旧 TASK/Board 把 same-Harness 内部隔离 Review 写成 `External Repair Review Passed`，可能掩盖用户明确要求的跨 Harness 外部复审门禁。Kimi 定向 spot session `session_3deac4cb-3aaf-437c-8624-621f302f78bb` 报告 `0/0/0/1`，Grok 4.5 定向 spot session `019fe5df-6236-7093-bd06-825728d1af0f` 报告 `0/0/0/0`；两者均基于旧 head `1263f9a` 且未覆盖完整 stack/全部轮询实现，因此只作为诊断证据，不记为完整 External Review Passed。本次纯记录修正关闭错误措辞，不计 repair 轮次；新 head 外部复审仍 Pending。

- Stacked update：普通 merge 吸收 #16 implementation，包含真实 In Progress `continue + needs_authority → active_work` 修复及双入口 preflight 集成。合并后 fresh 验证为 frontend codegen/typecheck/lint/build、Vitest `109/109`、隔离重跑 Playwright `109/109`、Skill `121/121`、Runtime bundle `43/43`；Codex bundled Python 3.12 full integration `52/53`，唯一失败仍为冻结 artifact guard 且 `baseline_preserved=true`。backend full `204 passed / 2 skipped / 1 known baseline failed`，唯一失败仍为未触及的 Windows non-recursive native event。
- Grok fresh 外部只读复审 session `019fe700-4986-7d00-a0b0-035a7455ac71` 绑定 implementation `3fbdf9d` 与 docs receipt head `3a8f137`，终局为 `Passed 0/0/0/0`；九项 closure matrix 全部 Closed，并明确 UA5 Pending。用户现已取消 Kimi 当前复审要求，改由 GPT Pro 作为第二外部 Reviewer；GPT Pro 必须绑定治理更新后的冻结远端完整 head，固定版本确认失败不计 Review。

## Outcome

- Base / Diff：base=869a8d3;diff=869a8d3..3fbdf9d
- 隔离位置：`codex/v010-project-console-fe` / `D:/open-source/ai-dev-flow-wt/v010-project-console-fe`。
- 回滚方式：提交前丢弃本阶段精确 diff；提交后 revert 本阶段 commit，不改写 RUNTIME-CONSOLE-BE 历史。
- 修改文件：新增 console API/state/view、默认 Console 与 network/legacy 三视图路由、合同 codegen、前端/浏览器测试及 43 文件规范 Runtime bundle；Legacy 文件保留。
- 验证证据：backend `204 passed / 2 skipped / 1 known baseline failed`，唯一失败为 Windows non-recursive native event 基线；Skill `121/121`；frontend codegen/typecheck/lint/build、Vitest `109/109`、Playwright `109/109`；visible/hidden 轮询、Clipboard 最终失败、Ready 语义、status/why-now 文案、真实便携 Dashboard 与真实异常 state-matrix 均通过；Runtime bundle `43/43`。Python 3.12 integration 当前为 `52/53`，唯一失败为 Stage 0 冻结 artifact guard，报告 `baseline_preserved=true`，无运行态失败。
- Review findings：same-Harness 内部隔离 session `019fe37b-1090-7241-80be-52c29ee4ab7` 为 `Passed 0/0/0/0`；Grok fresh 外部 session `019fe700-4986-7d00-a0b0-035a7455ac71` 为 `Passed 0/0/0/0`；GPT Pro 尚无绑定最终冻结 head 的终局 receipt，故整体外部复审仍 Pending。
- Delivery：本轮 current implementation head=`3fbdf9d`，branch `codex/v010-project-console-fe` 已推送且远端对齐；Draft PR [#17](https://github.com/a-littlecat/ai-dev-flow/pull/17)，base=`codex/v010-runtime-console-be`。当前外部复审尚未形成完整双 Harness receipt，不称 reviewed head。
- 状态边界：Grok External Re-review Passed / GPT Pro Re-review Pending / Overall External Re-review Pending / UA5 Pending user_only / Draft PR #17 / Unmerged / Not Released / Not Synced / Not Accepted / Not Closed / Legacy Retire Not Started。
- 剩余风险：自动化、真实浏览器 Design QA 和独立 Review 不能替代用户用 CADCat 与两个真实 Harness 任务完成日常入口体验验收。
- 下一步：由 GPT Pro 对 #16/#17 最终冻结远端完整 head 完成外部只读复审；与既有 Grok Passed 共同满足门禁后，才建议用户开始真实 CADCat 与两个 Harness 任务的 UA5。不得提前执行 LEGACY-RETIRE。
