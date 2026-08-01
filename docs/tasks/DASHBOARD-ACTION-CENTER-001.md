# DASHBOARD-ACTION-CENTER-001：将默认关系图改为聚焦的任务执行工作台

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `DASHBOARD-ACTION-CENTER-001`
- `task_type`: `code`
- `task_class`: `D`
- `lifecycle`: `Accepted`
- `review_status`: `Passed`
- `ua_level`: `UA6`
- `ua_status`: `Passed`
- `ua_evidence`: `#dashboard-action-center-001-ua6-2026-08-01`
- `acceptance_authority`: `Designated Acceptor Confirmed`
- `commit_status`: `Committed`
- `merge_status`: `Unmerged`
- `merge_authority`: `User Authorized`
- `close_authority`: `None`

## 目标与边界

- 目标：把 Dashboard 默认入口从高密度完整关系图改为聚焦的任务执行工作台，首屏依次呈现一个当前行动、最多两个并行建议、最多两个同时进行任务和最多两个等待/串行关系；保留任务上下游路线与完整关系图作为按需入口。
- 目标：并行建议只投影后端 `parallel_assessments` 中的 `candidate` 事实，明确“候选不等于授权”；真实数据没有候选时显示明确空状态，不推测或伪造建议。
- 目标：用户从当前行动、并行建议、同时进行或等待项进入任务上下文后，可以查看详情、正式上下游关系和完整网络，并能返回执行总览。
- 非目标：不修改后端关系、动作或并行判断算法，不修改 Contract/schema，不增加依赖，不把 Dashboard 变成写入器，不执行 release/deploy/Closed。
- 允许修改：`dashboard/frontend/src/**`、`dashboard/frontend/tests/**`、`dashboard/frontend/index.html`（仅在确有必要时）、`design-qa.md`、本 TASK、`docs/tasks/DASHBOARD-FOCUS-ASSESSMENT-001.md`、`docs/TASK_BOARD.md`。
- 禁止修改：`dashboard/backend/**`、`dashboard/contracts/**`、`skills/**`、依赖/构建配置、其他既有 TASK 的事实、认证/权限、安全边界和发布配置。

## 依赖与授权

- 前置依赖：用户已确认最终视觉方向；承接 `DASHBOARD-FOCUS-ASSESSMENT-001` 在 base `7e9ad6418b516ea419ea3ba429de4d260d7a8597` 上的已知未提交前端改动和验证证据。
- 视觉目标：本地 ImageGen 结果 `C:/Users/92336/.codex/generated_images/019fbba3-2c0b-7643-8451-80fc36b32deb/exec-e4cd637f-4a57-4dc4-9a0f-ddbca9a22a38.png`；允许根据真实只读数据为空或未知的事实使用清晰空状态，不照抄示意任务。
- Base commit：`7e9ad6418b516ea419ea3ba429de4d260d7a8597`。
- 已有 authority：用户于 2026-08-01 明确触发“自动落地我们确定的方案”；允许在冻结范围内持续实现、测试、独立复审、修复、精确暂存、commit、与 `main` 集成、push、创建/更新 PR、处理 CI，并在仓库规则允许时 merge。
- 未授权动作：tag、release、deploy、删除、数据迁移、密钥或认证/授权修改、强制推送、历史改写、外部 Skill 同步和 `Closed`。
- 执行位置：分支 `codex/dashboard-action-center-001`，当前工作区承接上述已知相关 diff。

## 路由与风险

- 路由：`Controlled`。
- Policy 输入：D 级；请求 delivery/merge；风险包含 `delivery`、`shared_component`、`real_environment`；动作 authority 为 Allowed；自动测试和真实浏览器可覆盖机器可确定验收，用户已选择视觉目标。
- Reviewer 闸门：交付前必须执行同 Harness、隔离、只读 Review；P0/P1 必须关闭，P2 必须修复或形成明确后续处置。
- Designated Acceptor：Codex 仅对冻结视觉目标、DOM/交互、响应式、碰撞和自动化测试等机器可确定指标执行 UA6；不替代新的主观审美或风险取舍。
- 停止条件：越出允许文件、需要后端/schema/大型依赖或安全边界变化、来源不明且重叠的用户修改、必需浏览器证据不可获得、出现 P0/数据/不可逆风险。

## 完成标准与验证

- 完成标准：默认总览聚焦一个当前行动，并以真实证据区分并行、同时进行、等待/串行；任务路线与完整关系图仍可按需进入。
- 验证命令或检查：前端 `npm run verify`、目标 workflow lint、`git diff --check`、真实 in-app Browser 桌面/移动端 Design QA 与独立只读 Review。
- [x] 默认页是执行工作台而非完整关系图，首屏只有一个主操作，最多展示七个任务，默认不出现交叉关系线。
- [x] 当前行动来自快照动作事实；并行建议只来自 `candidate` 评估且显示依据/待确认边界；同时进行只来自明确任务状态；等待与串行只来自明确阻塞或 `must_serial` 证据。
- [x] `完整关系图` 可进入现有高级网络；从工作台任务项可进入任务上下游/详情上下文并返回总览。
- [x] 1440×900 下核心文字清晰且无首屏溢出；390×844 下使用纵向列表，不把完整网络缩成默认缩略图。
- [x] 搜索、键盘焦点、实时快照刷新、空状态、错误/诊断入口保持可用，不通过颜色单独表达状态。
- [x] 定向 Vitest/Playwright、`npm run verify`、目标 workflow lint 和生产构建通过。
- [x] `design-qa.md` 对同尺寸参考图与真实页面完成比较，最终写明 `final result: passed`。
- [x] 独立只读 Review 为 `Passed`，无开放 P0/P1/P2。
- [x] `git diff --check` 通过，diff 可归属本 TASK 与承接的 `DASHBOARD-FOCUS-ASSESSMENT-001`。

## Repair Chain Ledger（仅进入 repair 时填写）

- Repair chain：Round 3。Round 1 源于独立只读 Review `019fbc79-84ad-7143-a449-80e8d5abf12b` 的两个 P1；Round 1 复审发现一个仍开放 P1 和一个证据一致性 P2；Round 2 复审关闭全部历史 finding 后发现两个新 P1。前两轮均关闭稳定 finding、增加回归并保持完整验证通过，满足第 3 轮 progress gate。
- `DASHBOARD-ACTION-CENTER-001-RVW-P1-001`：已修复。无 `blocking_task_ids` 的 blocked action 现在显示“动作受阻 + 真实 reason”，不再伪造“未知任务阻塞”；新增派生单测和浏览器语义回归。
- `DASHBOARD-ACTION-CENTER-001-RVW-P1-002`：Round 2 修复。控件同时保存精确操作 key 与稳定任务 ID；SSE 更新后先恢复同一操作，再恢复跨栏目的同一任务，任务真正消失时才移动到首个可用操作并通过 live region 说明。浏览器回归分别覆盖同栏刷新、跨栏目移动、确定性 fallback 和公告。
- `DASHBOARD-ACTION-CENTER-001-RVW-R1-P2-001`：已修复。`design-qa.md` 明确区分视觉修订时的 `92/92`、Round 1 的 `94/94` 与 Round 2 当前 fresh 结果。
- Round 1 复审：隔离只读 session `019fbcfa-2b15-7202-8c4d-ec61402aa98e` 为 `Needs Fix`，P0/P1/P2/P3=`0/1/1/0`；P1-001 Closed，P1-002 仍开放并补充跨栏目/消失边界，新增证据记录 P2。
- Round 2 验证：定向 Vitest `3/3`、overview Playwright `7/7`、fresh `npm run verify` 全部通过（Vitest `94/94`、Playwright `96/96`）；等待独立复审。
- Round 2 复审：隔离只读 session `019fbc95-2bbb-78d1-ad79-bf69d45388d9` 为 `Needs Fix`，P0/P1/P2/P3=`0/2/0/0`；全部历史 finding Closed，新发现前端私排当前行动与重复进入同一任务路线详情永久 loading 两个 P1。
- `DASHBOARD-ACTION-CENTER-001-RVW-R2-P1-001`：已修复。当前行动严格采用服务端 wire 顺序中的首个非 `none` 动作，不再按用户决定或 eligibility 私排；新增正序/反序镜像单测。
- `DASHBOARD-ACTION-CENTER-001-RVW-R2-P1-002`：已修复。详情进入 `loading` 即触发加载，不再只依赖 selected task ID 变化；浏览器回归覆盖“打开 A → 返回 → 再次打开 A → 详情 ready”。
- Round 3 验证：定向 Vitest `4/4`、overview Playwright `7/7`、fresh `npm run verify` 全部通过（Vitest `95/95`、Playwright `96/96`）；等待独立复审。
- 非计数动作：任务冻结、诊断、测试、Design QA、Review 和记录同步本身不计 repair round。

## Outcome

<a id="dashboard-action-center-001-ua6-2026-08-01"></a>
### UA6 机器可确定验收证据（2026-08-01）

- 冻结判据：选定视觉目标的同尺寸桌面对照、移动端单列与无横向溢出、默认总览/任务路线/完整关系图核心交互、只读事实语义、键盘焦点与完整自动回归全部通过；独立 Review 无开放 P0/P1/P2。
- 结果：Round 3 fresh `npm run verify` 通过，Vitest `95/95`、Playwright `96/96`；真实 in-app Browser 桌面/移动端、核心往返和 console error=`0`；`design-qa.md` final result=`passed`；Round 3 独立只读 Review session `019fbc9f-8f7e-7571-b58b-90f5343b184d` 为 `Passed`，P0/P1/P2/P3=`0/0/0/0`。记录 `UA6 Passed / Designated Acceptor Confirmed / Accepted`。
- authority 边界：仅确认冻结方案达到机器可确定验收并可进入用户已授权的 commit/push/PR/merge；不授权 tag、release、deploy、外部 Skill 同步、删除或 `Closed`。

- Base / Diff：base=7e9ad6418b516ea419ea3ba429de4d260d7a8597;diff=b2098f8fee44eda34d7bf18d547b04bc69e2758c
- 隔离位置：`codex/dashboard-action-center-001` 分支上的当前 Worktree。
- 回滚方式：在合并前丢弃本 TASK 的精确 diff；合并后通过 revert 本 TASK 的交付 commit 回滚，不改写历史。
- 修改文件：新增 `overview.ts` 与 `actionCenter.ts` 实现事实约束的默认工作台；`store.ts` / `main.ts` / `statusBar.ts` / `toolbar.ts` / `graphView.ts` / `detailPanel.ts` 完成视图分层、任务路线和简化状态栏；`styles.css` 落地桌面/移动视觉；新增并更新 Vitest/Playwright 回归；同步两份 TASK、看板和 `design-qa.md`。
- 验证证据：Round 3 fresh `npm run verify` exit `0`，codegen/typecheck/ESLint/production build 通过，Vitest `95/95`、Playwright `96/96`；目标 workflow lint `errors=0 / violations=0 / warnings=1`（未跟踪 TASK 的 lifecycle 历史不可验证）；`git diff --check` 通过；真实 in-app Browser 桌面 `1536×1024`、移动 `390×844`、核心页面切换和 console error=`0`；`design-qa.md` final result=`passed`。
- Review findings：首轮独立只读 Review `019fbc79-84ad-7143-a449-80e8d5abf12b` 为 `Needs Fix`，P0/P1/P2/P3=`0/2/0/0`；Round 1 复审 `019fbcfa-2b15-7202-8c4d-ec61402aa98e` 为 `Needs Fix`，P0/P1/P2/P3=`0/1/1/0`；Round 2 复审 `019fbc95-2bbb-78d1-ad79-bf69d45388d9` 为 `Needs Fix`，P0/P1/P2/P3=`0/2/0/0`；Round 3 复审 `019fbc9f-8f7e-7571-b58b-90f5343b184d` 为 `Passed`，P0/P1/P2/P3=`0/0/0/0`，全部历史 finding Closed。
- UA 动作与结果：用户已选择视觉方向；同尺寸视觉、DOM/交互、响应式、无溢出、只读事实语义和浏览器运行证据全部满足冻结 UA6 判据；Designated Acceptor 于 2026-08-01 记录 `UA6 Passed / Accepted`。
- Commit 证据：功能、回归、Design QA 与两份 TASK 已精确提交为 `b2098f8fee44eda34d7bf18d547b04bc69e2758c`；提交后仅本 TASK/看板收据待提交。
- 状态边界：Goal Active；release/deploy/Closed 未授权。
- 剩余风险：真实数据当前可能没有并行候选，必须用真实空状态验证，不得以示意数据冒充可并行建议。
- 下一步：精确提交并进入已授权的远端 PR/CI/merge 流程。
