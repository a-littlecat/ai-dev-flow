# DASHBOARD-FE-001-REPAIR-001：修复真实任务规模下关系图被并行评估列表挤出首屏

> 当前结论（2026-08-01）：`REL-005` 已核验本任务的实现、Review、UA、提交、主线与后继发布证据，任务现为 `Closed`。下文早期“当前状态/下一步/Not Closed”等措辞均是形成时的历史快照，不再代表当前状态；本说明与顶部 Contract 为唯一最新结论，且不改写原 UA 事实。

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `DASHBOARD-FE-001-REPAIR-001`
- `task_type`: `repair`
- `task_class`: `D`
- `lifecycle`: `Closed`
- `review_status`: `Passed`
- `ua_level`: `UA4`
- `ua_status`: `Passed`
- `ua_evidence`: `docs/tasks/DASHBOARD-FE-001-REPAIR-001.md#dashboard-fe-001-repair-001-ua4-2026-07-29`
- `acceptance_authority`: `User Confirmed`
- `close_authority`: `User Authorized`
- `commit_status`: `Committed`
- `merge_status`: `Merged`
- `merge_authority`: `User Authorized`

## Scheduling

- `scheduling_schema`: `ai-dev-flow/scheduling/v1`
- `priority`: `high`
- `depends_on`: `DASHBOARD-FE-001#commit_status=Committed;DASHBOARD-FE-001#lifecycle=Accepted;DASHBOARD-FE-001#merge_status=Merged;DASHBOARD-FE-001#review_status=Passed;DASHBOARD-FE-001#ua_status=Passed`
- `replaces`: `none`
- `discovered_from`: `DASHBOARD-INTEGRATE-001`
- `parent`: `DASHBOARD-INTEGRATE-001`
- `conflicts_with`: `DASHBOARD-INTEGRATE-001`
- `parallel_intent`: `serial`
- `write_scope`: `file:dashboard/frontend/src/styles.css;file:dashboard/frontend/src/ui/toolbar.ts;file:dashboard/frontend/tests/browser/real-scale.spec.ts;file:docs/TASK_BOARD.md;file:docs/tasks/DASHBOARD-FE-001-REPAIR-001.md`
- `module_locks`: `dashboard-ui`
- `worktree`: `required`
- `branch_hint`: `codex/dashboard-fe-001-repair-001`
- `risk_flags`: `historical_p1;real_environment;shared_component;tests_do_not_cover_oracle`

## 目标与边界

- 目标：关闭 `DASHBOARD-INTEGRATE-P1-001`。真实项目当前有 21 个任务、210 个并行组合；工具栏一次渲染全部组合，导致 1366×768 下关系图主区域被挤出首屏。
- 目标：超过 12 条的真实规模并行评估默认以带统计信息的可访问摘要收起；少量评估保持原有直接展示。展开后使用内部有界滚动，仍可访问全部组合、结果和原因，同时不把 `candidate` 表现为已授权。
- 非目标：不改变后端并行判定、排序、wire schema、任务关系图布局或已有任务状态；不引入依赖，不顺手重构其他前端组件。
- 允许修改：仅限 Scheduling `write_scope` 列出的五个文件。
- 禁止修改：其他 `dashboard/frontend/**`、`dashboard/backend/**`、`dashboard/contracts/**`、`skills/**`、其他 TASK、版本/发布文件和本机 Skill。

## 依赖与授权

- 前置依赖：`DASHBOARD-FE-001` 已 `Accepted / Review Passed / UA4 Passed / Committed / Merged`；本任务是对集成阶段新发现稳定 P1 的独立受控修复，不回写或改写原 FE 验收事实。
- Base commit：`dbbc5e7591a06bc4d381401882c42515a7e05873`。
- 触发证据：`DASHBOARD-INTEGRATE-001` 独立 Worktree 的真实后端/前端联调在 1366×768 复现；snapshot `fresh`、21 tasks、210 parallel assessments、93 diagnostics，关系图区域被无边界的 `.pair-list` 挤出并裁切。
- 已有 authority：用户在收到稳定 P1、根因、建议修复范围和状态边界后明确回复“授权你继续，直至可验收为止”；允许创建本修复 TASK/Worktree，在精确 allowlist 内建立 RED、实施、验证、执行隔离只读 Review，并在同一冻结完成合同内连续修复至 `Review Passed / UA4 Pending`。
- 验收 authority：用户在查看修复结果、验证、独立 Review、截图和非阻断 P2 风险后明确回复“验收通过”；允许记录 `UA4 Passed / User Confirmed / Accepted`。
- 提交与合并 authority：用户在 `UA4 Passed / Accepted` 写回后明确回复“提交并合并”；允许提交本修复分支并合并到本地 `main`，以及写回对应 Git 收据。
- 当前未授权动作：push、release、外部同步、删除 Worktree/分支或 Closed。
- 执行位置：`D:\open-source\ai-dev-flow-wt\dashboard-fe-001-repair-001`，分支 `codex/dashboard-fe-001-repair-001`。

## 路由与风险

- 路由：`Controlled`。
- Policy 输入：`task_class=D`；命中 `historical_p1`、`real_environment`、`shared_component`、`tests_do_not_cover_oracle`；根因已知且存在直接浏览器 oracle。
- Reviewer 闸门：`Required`；进入 UA4 建议前必须完成隔离、ephemeral、read-only 的独立实现 Review，P0/P1 必须为 0。
- 主要风险：收起后用户找不到完整评估；展开后仍挤压图；键盘/读屏无法操作；统计摘要与 wire 结果不一致；候选文案误导为执行授权。
- 停止条件：需要修改后端或共享 schema、需要新增依赖、需要越出 allowlist、需要破坏已有 wire 语义或出现安全/数据完整性风险。

## 冻结完成合同

- `C1`：在 1366×768、1920×1080、2560×1440 下，21-task/210-pair snapshot 初始并行列表收起，关系图区域可见且高度 `>= 240px`。
- `C2`：摘要按钮支持鼠标与键盘；展开后列表使用内部有界滚动，关系图仍可见且高度 `>= 180px`；全部 210 条评估可到达。
- `C3`：`candidate / must_serial / unknown` 数量、reason code 和“候选不等于授权”语义保留，前端不重新判定并行结果。
- `C4`：定向 RED 变 GREEN；前端 codegen、typecheck、lint、unit、build、browser 与只读 dependency audit 完成；不新增依赖，不修改 contract/backend。

## Repair Campaign Authority

- `campaign_id`: `DASHBOARD-INTEGRATE-RCAMPAIGN-001`
- `repair_chain_id`: `DASHBOARD-INTEGRATE-RC-001`
- `finding_ids`: `DASHBOARD-INTEGRATE-P1-001`
- `profile`: `core_product`
- `attempt_count`: `1`
- `consecutive_no_progress`: `0/4`
- `closure_contract_hash`: `0d07d0527ebfc636d310f449fcb1abad3626809c92dce6657a5184d51e55fb61`
- `allowed_files_hash`: `9bc052f4390b1c937d529f3be050f1fef8b11e3be2d1ded8f0adbbad2b0b0408`
- Hash 输入：UTF-8、LF、无尾随换行；完成合同按 `C1` 至 `C4` 英文 canonical 文本连接，allowed files 按路径升序连接。
- 激活条件：依赖、authority、根因、Reviewer/Repairer 能力、成本边界和无外部副作用均已冻结；所有 hard-stop flags 为 false。
- 状态边界：`Accepted / Review Passed / UA4 Passed / User Confirmed / Committed / Merged local main / Not Pushed / Not Released / Not Closed`。

## 完成标准与验证

- 完成标准：冻结完成合同 `C1` 至 `C4` 全部满足，独立只读 Review `Passed` 且 P0/P1 为 0；用户已完成 UA4 并确认验收。
- 验证命令或检查：先运行新增 Playwright 用例形成 RED，再运行 `npm run verify`、只读 `npm audit --audit-level=moderate`、workflow lint、diff allowlist 和独立只读 Review。
- [x] 新增 21-task/210-pair 浏览器级回归用例，并先在旧实现上形成稳定 RED。
- [x] 默认收起、统计摘要、键盘/鼠标展开、内部滚动、完整可达性和候选非授权语义通过。
- [x] 1366/1920/2560 三档关系图和详情区保持可见，无水平溢出。
- [x] `npm run verify` 全部通过。
- [x] `npm audit --audit-level=moderate` 已只读运行并准确记录。
- [x] `python skills/ai-dev-flow/scripts/workflow_lint.py docs/tasks/DASHBOARD-FE-001-REPAIR-001.md --format json` 无 error/violation。
- [x] `git diff --check` 通过，diff 只命中精确 allowlist。
- [x] 独立只读 Review `Passed`，P0/P1 为 0。

## A1 实施与验证候选（2026-07-29）

- RED：旧实现对 1366×768、1920×1080、2560×1440 三档均找不到 disclosure toggle；失败截图同时证明 1366×768 下 210 条评估占满首屏，关系图不可见。结果 `3/3 Failed`。
- 修复：工具栏从 wire assessment 只读统计 `candidate / must_serial / unknown`；超过 12 条时默认收起为带 `aria-expanded/aria-controls` 的摘要，小列表保持既有直接展示；展开列表限制为 `min(32vh, 280px)` 并独立纵向滚动。
- A1 过程反馈：首次实现因作者 CSS `display:flex` 覆盖原生 `hidden` 规则仍为 RED；补充显式 `[hidden]` 后定向用例 GREEN。完整回归随后发现 9 个长字段用例要求小列表直接展示，最终以 12 条阈值兼容原行为；相关真实规模 + 长字段矩阵 `12/12 Passed`。
- 定向 GREEN：21 tasks / 210 pair assessments 在三档视口 `3/3 Passed`；折叠与展开截图各 3 张位于忽略目录 `dashboard/frontend/artifacts/screenshots/real-scale/`。
- 截图 SHA256：collapsed 1366=`b7ef1aa3256c44a178dc7d7cf235236f763aa96d8ccbccfe0225447e0271d05c`、1920=`46beabcd8f946cbf363d18bbde4c16242f7986d92db4337cb2398f295bf4c388`、2560=`243378c6ed721936a26310bf41e17cdd508befc850967056d88a937d112a9378`；expanded 1366=`e26b88a8d09da697e53d799ff8ca7f824bc7cf0a9b57531353c8dd47164ba50a`、1920=`134e0f2430b6e4e83287da156fb3d42bf9e145e4cf646021c230f889a938c301`、2560=`1d62f04aee52ebef086ac52c2074a86e38a6b6fc30b6ad2bd9ef09dcc7d6487a`。
- 完整验证：`npm run verify` 通过；codegen 同步、typecheck、ESLint、81/81 Vitest、production build、79/79 Chrome Playwright 全部 GREEN。
- 依赖审计：完整 `npm audit --audit-level=moderate` 仍报告原 FE 已披露的 10 项开发依赖漏洞（3 moderate / 6 high / 1 critical），修复要求 eslint/vite breaking upgrade；`npm audit --omit=dev --audit-level=moderate` 为 0，package manifest/lock 未修改、未新增依赖。
- Scope：五个变更文件与 allowed files 完全相等，`scope_delta_count=0`；临时 index 纳入 untracked 后 `git diff --cached --check` exit 0。
- Campaign progress：`attempt_count=1`、`meaningful_progress=true`、`consecutive_no_progress=0/4`，无 GREEN→RED、严重度上升、外部副作用或 hard-stop；等待独立只读 Review。

## A1 独立只读 Review（2026-07-29）

- 首次调用：原生 `codex exec --ephemeral --sandbox read-only` 在 244 秒超时且没有形成回执，只记为 `Review not completed`，未用于任何结论；残留 Reviewer 进程已按精确 PID 停止，五文件 manifest 未变化。
- 最终 Reviewer：独立 native Codex session `019face7-a722-7332-8903-86d859717d10`，`approval=never / sandbox=read-only / ephemeral`；只读审查冻结 base、五文件 diff、测试报告、截图、workflow lint 与 Git 范围。
- 冻结输入：五文件 manifest SHA256 `7207f2e83ccb17b3b9d3a8f95edc12c2d86c2968f51e122020ff8a020e942ec5`，审查前后完全一致；`Workspace writes=None`。
- Decision：`Passed`；允许进入 UA4；`P0/P1/P2/P3=0/0/1/0`；`DASHBOARD-INTEGRATE-P1-001` Closed。
- `DASHBOARD-FE-REPAIR-RVW-P2-001`（非阻断）：toggle 激活后 `renderPairList()` 重建按钮，键盘展开会把焦点退回 `BODY`；内容仍可重新 Tab 到达，关系图高度、210 条数据完整性与鼠标/键盘激活能力不受影响。建议后续保持 toggle DOM 身份或重建后恢复焦点，并补“键盘展开后焦点仍在 toggle、随后 Tab 进入首条评估”的 oracle。
- 独立证据：Reviewer 解包原始 Playwright HTML 报告确认 79/79、三档真实规模 3/3；复算六张截图 SHA256、五文件 scope/manifest、Git base/status 与 workflow lint；静态确认统计直接来自 wire、数组顺序和结果/原因保留、无 package/contract/backend 差异。
- 验证边界：Reviewer 为零写入，未重跑会生成产物的 verify/audit；81 unit、production audit 0、RED 3/3 来自主控 fresh 收据。完整 Review receipt：`C:\Users\92336\AppData\Local\Temp\dashboard-fe-a1-review-2.stdout.txt`，SHA256 `2CEFDC48F2F1F742AE7643308BFCB574CD2C0F007605519FC21F7BB7F7F45BD7`。
- 状态边界：Review Passed 只允许邀请 UA4，不等于 `UA4 Passed / Accepted / commit / merge / push / release / Closed`。

## DASHBOARD-FE-001-REPAIR-001 UA4 2026-07-29

- 用户反馈：用户在收到可验收结论、1366×768 折叠/展开截图、完整自动验证、独立 Review `Passed` 和键盘焦点非阻断 P2 风险后明确回复“验收通过”。
- 验收范围：确认 21 tasks / 210 pair assessments 下关系图保持首屏主体，大列表统计摘要、折叠/展开、内部滚动、完整评估可达性和“候选不等于授权”语义符合预期。
- 验收结果：`UA4 Passed / User Confirmed / Accepted`。
- 已知风险：`DASHBOARD-FE-REPAIR-RVW-P2-001` 仍开放；键盘展开后焦点退回页面主体，需要重新 Tab 才能进入评估项，不阻断本次验收。
- 权限边界：本次“验收通过”只授权 UA4 与 Acceptance 状态写回，不授权 stage、commit、merge、push、release、删除 Worktree/分支或 Closed。

## 提交与合并授权 2026-07-29

- 用户授权：用户在 `UA4 Passed / User Confirmed / Accepted` 写回后明确回复“提交并合并”。
- 提交范围：只提交冻结的五文件 allowlist；忽略目录中的截图、测试报告、构建产物、依赖目录和本机临时文件不进入提交。
- 合并目标：本地 `main`；使用保留独立修复任务边界的 `--no-ff` merge，并在合并检出上重新运行完整前端验证。
- 权限边界：不包含 push、release、外部同步、删除 Worktree/分支或 Closed。

## 提交与合并结果 2026-07-29

- 功能提交：`3c8160f8041e3280e49f161fda4d7e2febdeb288`（`fix(dashboard): preserve graph space for large pair lists`）。
- 合并提交：`2ac8b3b80a391e488e7b080b3f97e8ccadfe8000`（本地 `main`，`--no-ff`，父提交为 `dbbc5e7591a06bc4d381401882c42515a7e05873` 与 `3c8160f8041e3280e49f161fda4d7e2febdeb288`）。
- 合并检出验证：`npm run verify` 已运行并通过；codegen、typecheck、ESLint、build 均通过，Vitest `81/81`、Chrome Playwright `79/79`。
- 交付边界：未 push、未 release、未外部同步、未删除 Worktree/分支，任务未 Closed。

## Outcome

- Base / Diff：base=dbbc5e7591a06bc4d381401882c42515a7e05873;diff=3c8160f8041e3280e49f161fda4d7e2febdeb288
- 隔离位置：`D:\open-source\ai-dev-flow-wt\dashboard-fe-001-repair-001` / `codex/dashboard-fe-001-repair-001`
- 修改文件：`dashboard/frontend/src/ui/toolbar.ts`、`dashboard/frontend/src/styles.css`、`dashboard/frontend/tests/browser/real-scale.spec.ts`、本 TASK 与 TASK_BOARD 投影；未修改 package、contract、backend 或 Skill。
- 验证证据：定向 RED `3/3 Failed` → GREEN `3/3 Passed`；修复分支和合并后的本地 `main` 均完整运行 `npm run verify` 并 GREEN（各 81 unit + 79 browser）；production dependency audit 0；scope 与 diff check GREEN。
- Review findings：独立只读 Review `Passed`，P0/P1/P2/P3=`0/0/1/0`；目标 P1 Closed；开放非阻断 `DASHBOARD-FE-REPAIR-RVW-P2-001` 为键盘展开后的焦点保持问题。
- UA 动作与结果：用户明确回复“验收通过”；`UA4 Passed / User Confirmed / Accepted`。
- 合并目标与事实证据：本地 `main`；feature=`3c8160f8041e3280e49f161fda4d7e2febdeb288`；merge=`2ac8b3b80a391e488e7b080b3f97e8ccadfe8000`；`--no-ff` 两父提交已核对。
- 回滚方式：功能与合并均已有独立 Git 提交；如后续需要回退，应另行授权后使用可审计的 `git revert`，不执行 reset、删除或历史改写。
- 状态边界：`Accepted / Review Passed / UA4 Passed / User Confirmed / Committed / Merged local main / Not Pushed / Not Released / Not Closed`。
