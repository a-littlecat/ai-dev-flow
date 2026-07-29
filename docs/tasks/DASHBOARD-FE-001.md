# DASHBOARD-FE-001：实现关系图优先的本地任务仪表盘前端

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `DASHBOARD-FE-001`
- `task_type`: `code`
- `task_class`: `C`
- `lifecycle`: `Accepted`
- `review_status`: `Passed`
- `ua_level`: `UA4`
- `ua_status`: `Passed`
- `ua_evidence`: `docs/tasks/DASHBOARD-FE-001.md#dashboard-fe-001-ua4-2026-07-29`
- `acceptance_authority`: `User Confirmed`
- `close_authority`: `None`
- `commit_status`: `Committed`
- `merge_status`: `Unmerged`
- `merge_authority`: `User Authorized`

## Scheduling

- `scheduling_schema`: `ai-dev-flow/scheduling/v1`
- `priority`: `high`
- `depends_on`: `DASHBOARD-BE-001#commit_status=Committed;DASHBOARD-BE-001#lifecycle=Accepted;DASHBOARD-BE-001#review_status=Passed;DASHBOARD-BE-001#ua_status=Passed`
- `replaces`: `none`
- `discovered_from`: `DASHBOARD-001`
- `parent`: `DASHBOARD-001`
- `conflicts_with`: `none`
- `parallel_intent`: `consider`
- `write_scope`: `dir:dashboard/frontend`
- `module_locks`: `dashboard-ui`
- `worktree`: `required`
- `branch_hint`: `codex/dashboard-fe-001`
- `risk_flags`: `public_api;shared_component`

## 目标与边界

- 目标：由 Kimi 实现一个本地、桌面优先、完整任务关系图为主视图的前端，让用户直观看到下一动作、并行候选、强制串行、阻塞、替代/派生关系和真实快照状态。
- 目标：严格消费 `dashboard/contracts/**` 的只读 API schema、fixtures 和 SSE transcript，不自行解析 TASK、TASK_BOARD 或 Git。
- 非目标：本 TASK 不规定具体框架、组件库、图布局算法、视觉 tokens、字体、间距、图标或动效实现；这些由 Kimi 在完成产品结果的前提下决定。
- 非目标：不实现后端、写接口、任务编辑器、自动执行按钮、Worktree 管理、账号/云同步、移动端完整编辑体验。
- 允许修改：未来执行时仅限 `dashboard/frontend/**`、`docs/tasks/DASHBOARD-FE-001.md` 和该任务在 `docs/TASK_BOARD.md` 的投影行；`dashboard/contracts/**` 只读消费。
- 禁止修改：`dashboard/backend/**`、`dashboard/contracts/**`、`skills/ai-dev-flow/**`、其他 TASK、版本/发布文件和本机 Skill；依赖选择必须在 TASK Review 中列明，新增大型依赖需用户确认。

## 产品结果要求

### 首页必须直接回答

1. 完整任务网络、主要串行链、汇合点和当前关注节点是什么。
2. 哪些节点有下一动作，动作是计划、执行、继续、Review、repair、用户决定还是交付相关动作。
3. 哪些只是并行候选，哪些因依赖、共享路径、模块锁、风险、UA 或 Worktree 证据必须串行。
4. 哪些任务被替代、拆分、取消或由新问题派生。
5. 当前 snapshot 是 fresh、stale 还是 partial；TASK、TASK_BOARD、Git/Worktree 或 Scheduling 是否有冲突。

### 信息与交互

- 完整关系图占主视觉区域；Kanban 不能成为默认首页。
- 全局状态持续显示项目根、branch/HEAD、revision/快照时间、fresh/stale/partial 和 error/violation/warning 数量。
- 提供可收起的任务详情，完整展示 lifecycle、Review、UA、Accepted、commit、merge、release、Closed、依赖、动作、并行、Git/Worktree、diagnostics 和 provenance。
- “下一动作”“并行候选”“需要决定”是图上筛选/高亮入口；不得把 candidate 表现成已授权执行。
- 支持按 lifecycle、动作、风险、等级、模块、Worktree、关系类型和诊断严重度筛选。
- 支持缩放、平移、适配视图、定位节点、聚焦上游/下游和恢复完整网络。
- depends_on、conflicts_with、replaces、discovered_from 使用不同线型/符号和文字，不只靠颜色。
- 覆盖 loading、empty、fresh、stale、partial、parse error、dependency cycle、unknown parallelism、API disconnected 和 SSE reset。

### 风格建议

- 推荐“工程控制台 + 关系地图”：深色中性背景、克制的蓝绿强调色、高密度但分组清晰。
- 字体、间距和节点层级服务于快速扫描；避免大面积渐变、装饰性玻璃、悬浮卡片堆叠和持续漂移动效。
- 状态色只作辅助，必须同时有文字/图标；diagnostic 严重度和 fresh/stale/partial 不得只用颜色区分。
- 动效只用于聚焦、筛选和 revision 更新，支持 `prefers-reduced-motion`。

### Kimi 的实施自由与硬边界

- Kimi 自主选择前端框架、组件库、图引擎、布局、design tokens、响应式和动效。
- Kimi 不得改变或合并 API schema 和正交状态语义；需要新增字段时停止并提交 contract change。
- 前端运行时只调用同源本地 GET/SSE，不读取文件系统、不执行 Git、不保存任务 authority。
- 浏览器本地状态只保存筛选、视口和展开偏好；不得把它当任务事实源。
- 所有 Mock、类型和测试样本必须从 versioned schema/fixtures 生成或校验，禁止手写另一套接口模型。

## 依赖与授权

- 前置依赖：`DASHBOARD-BE-001` 必须达到 `Review Passed / UA3 Passed / Accepted`，并提供可引用的 `dashboard/contracts/**` schema、validator、fixtures 和 SSE transcript。
- Base commit：规划基线为 `fb16bc50f02023aad4a51acd8bf495231fe65f63`；实际实施已基于共享 contract Accepted 链顶端 `fc34f11d7a1079f1ba84d22adaf61d0b973136d4`（`docs(dashboard): record Git snapshot backend merge`）重新冻结。
- 已有 authority：合同独立 Review、有限 repair、Ready 写回与规划提交（规划阶段，历史）；用户随后另行授权在独立 Worktree 实施前端、安装实施所需依赖，以及本轮实施证据写回（仅限本 TASK 与看板投影行）。
- 未授权动作：实现 Review 自批、代替用户执行 UA4、commit、merge、push、release、外部同步和 Closed。
- 执行位置：未来必须使用独立 Worktree 与 `codex/dashboard-fe-001` 分支；共享 contracts 只读时，可与 `DASHBOARD-BE-002` 候选并行。
- 候选并行门禁：必须同时满足父 TASK 的 Accepted contract consumer exception v1；BE-001 四个正交前置条件、只读 contracts、BE-002/FE-001 scope 与 module lock 分离、两个可核对 Worktree 和 clean ownership 缺一项均不得显示为 candidate。

## 路由与风险

- 路由：`Tracked`。
- Policy 输入：`task_class=C`、`ua_level=UA4`、风险包含 `public_api`、`shared_component`；未来会新增多文件前端并需要用户观察，当前无 execution authority。
- Reviewer 闸门：`Triggered`；public API/shared component 命中 Tracked Review 风险，进入 UA4 前必须隔离、只读 Review。
- 主要风险：前端复制状态机、把候选误报为授权、遗漏异常状态、图在真实任务量下不可读、可访问性不足、依赖体积和维护成本失控。
- 停止条件：需要改变共享 schema；需要直接读取/修改 TASK 或 Git；需要写接口；需要大型依赖但未取得确认；无法达到 WCAG 2.2 AA 或目标桌面宽度。

## 完成标准与验证

- 完成标准：首页无需打开详情即可回答完整关系、下一动作、并行/串行、阻塞和数据健康状态。
- 完成标准：所有正交状态、关系类型、diagnostic、provenance 和异常场景都有明确表现。
- 完成标准：前端只消费 versioned read-only API/SSE，schema/fixture validator 无漂移。
- 完成标准：1366px、1920px、2560px 桌面宽度无关键遮挡；键盘完成筛选、节点切换和详情查看；支持 reduced motion。
- 验证命令或检查：Kimi 在选定技术栈后把 build、typecheck、lint、unit/component test 和 dependency audit 命令写回本 TASK。
- 验证命令或检查：使用全部 versioned fixtures 做浏览器级 screenshot/interaction 检查，并验证 disconnected/reconnect/reset。
- 验证命令或检查：运行 `python skills/ai-dev-flow/scripts/workflow_lint.py docs/tasks/DASHBOARD-FE-001.md --format json`。
- 实际验证命令（已写回）：`npm run verify`（= `codegen:check` + `typecheck` + `lint` + `vitest run` + `vite build` + `playwright test`，在 `dashboard/frontend` 下执行）；依赖审计 `npm audit --audit-level=moderate`（只读，禁止 `audit fix`）。
- [x] build、typecheck、lint、组件测试和浏览器测试全部有 fresh 结果。
- [x] schema/fixtures strict validation 通过，无前端私有状态机或未记录 API 字段。
- [x] 1366/1920/2560、键盘、对比度、非颜色表达和 reduced motion 检查完成。
- [ ] 固定 pair fixture 验证完整条件唯一得到 candidate；缺任一前置条件或 Worktree 得到 unknown；contracts 写入、scope/lock 重叠得到 must_serial。（前端已验证 candidate / must_serial / unknown 三种 wire 结果及 reason code 的展示语义，以及 `parallel-unknown` fixture 的浏览器呈现；但"完整条件唯一得到 candidate / 缺任一前置条件得到 unknown / contracts 写入得到 must_serial"的条件矩阵由后端门禁测试证明，前端证据不覆盖，保持未勾选。）
- [x] `git diff --check` 通过，diff 只归属当前 TASK。

## 验收建议

- 用户动作等级：UA4（用户在本机打开页面，观察完整关系图、筛选、详情、异常状态和响应式效果）。
- 是否需要用户实机测试：是；但只需运行本地页面，不涉及外部真实业务环境。
- 用户需要做什么：打开包含真实任务的本地仪表盘，检查关系是否易读、下一动作是否醒目、并行/串行是否不会误导。
- 不验收的风险：自动测试可证明结构正确，但不能代替用户判断关系图是否直观好用。
- 是否允许关闭任务：否；最新独立 Review `Passed`（`P0/P1/P2/P3=0/0/4/0`），用户已在本机完成重新 UA4 并明确回复“好的，验收通过”，因此记录 `UA4 Passed / User Confirmed / Accepted`；本次确认不授权 commit、merge、push、release 或 Closed。

## 四份实施 TASK 初始独立 Review（2026-07-28）

- Reviewer：当前 Codex Harness 的独立 Reviewer 子上下文；仅收到 NTFS `RX` 冻结证据副本，`Workspace writes=None`。
- 冻结输入：本 TASK SHA256 `0A2B169E7839C10A3E592F8D7FE15EF346702B2526200530061712048615359C`；基线 `main@fb16bc50f02023aad4a51acd8bf495231fe65f63`。
- 结论：`Needs Fix`；`P0/P1/P2/P3=0/1/0/0`。
- `DASHBOARD-TASKS-P1-001`：与 BE-002 的候选并行缺少能覆盖默认串行规则的机器可验证例外。

## 四份实施 TASK Repair Round 1（2026-07-28）

- `attempt_id`: `DASHBOARD-TASKS-RC-001-A1`
- `repair_chain_id`: `DASHBOARD-TASKS-RC-001`
- `finding_ids`: `DASHBOARD-TASKS-P1-001`
- 修订：前置条件增加 Accepted/Review/UA/Committed 四个正交轴，并冻结 contracts 只读、scope/lock 分离、独立 Worktree/dirty ownership 和反例 fixture。
- GREEN：关闭标准已有机器可验证输入和唯一预期结果；是否关闭由下一次独立复审判定。

## 四份实施 TASK 最终独立复审（2026-07-28）

- 冻结输入：本 TASK SHA256 `028E056BE6AE85309E50A85CE687833D32EFC3BB862F690130105A77F62F9547`。
- 结论：`Passed`；`DASHBOARD-TASKS-P1-001` Closed 且最终复审无回归，无新增 finding；整体 `P0/P1/P2/P3=0/0/0/0`。
- Reviewer 确认：Kimi 实施自由、只读运行时合同、依赖门禁、并行反例、浏览器验证和可访问性合同足以进入 Ready。
- 状态边界：`Ready / Review Passed / UA4 Pending / Uncommitted / Unmerged`；没有 execution authority。

## 实施证据写回（2026-07-28，历史：initial implementation 记录）

> 本节为首次实施时的历史证据，其中 62/62 单测、28/28 浏览器测试、33 张截图（2026-07-29 00:28–00:29 UTC+8）已被后续 Repair Round 1（67/67、38/38、44 张）与 Repair Round 2（见末节）的 fresh 证据替代；保留仅为审计轨迹。

- 执行位置：独立 Worktree `D:/open-source/ai-dev-flow-wt/dashboard-fe-001`，分支 `codex/dashboard-fe-001`，实际 base `fc34f11d7a1079f1ba84d22adaf61d0b973136d4`。
- 技术栈与依赖选择：TypeScript 5.7 + Vite 5.4，无 UI 框架（DOM + SVG 直绘关系图）。运行时依赖仅 `ajv@^8.17.1`（对 versioned schema 做 strict 校验）；开发依赖为 `@playwright/test@1.61.0`、`@types/node@^22.10.0`、`eslint@^9.17.0`、`jsdom@^25.0.1`、`json-schema-to-typescript@^15.0.4`（契约类型 codegen）、`typescript@^5.7.2`、`typescript-eslint@^8.18.1`、`vite@^5.4.11`、`vitest@^2.1.8`。未引入大型运行时依赖。
- 修改范围：`dashboard/frontend/**` 全部为新文件（39 个非忽略文件，Untracked/Uncommitted）；类型由 `scripts/generate-types.mjs` 从 `dashboard/contracts/**` schema 生成，未手写第二套接口模型；`dashboard/backend/**`、`dashboard/contracts/**` 未触碰。
- 验证命令与 fresh 结果（命令于 2026-07-28 深夜（UTC+8）在 Worktree 复跑；Playwright 截图跨午夜生成，文件时间为 2026-07-29 00:28–00:29 UTC+8）：
  - `npm run codegen:check`：generated types 与 contract schema 同步。
  - `npm run typecheck`（`tsc --noEmit`）：通过。
  - `npm run lint`（`eslint .`）：通过，0 error。
  - `npm run test:unit`（`vitest run`）：5 个文件 62/62 通过。
  - `npm run build`（`vite build`）：通过，JS 产物 193.9 kB（gzip 59.5 kB）。
  - `npm run test:browser`（`playwright test`）：4 个 spec 28/28 通过（29.3s）。
  - 截图证据：33 张 PNG 位于 `dashboard/frontend/artifacts/screenshots/`（a11y 2、fixtures 9、graph 11、responsive 3、SSE 8；该目录被前端 `.gitignore` 忽略，仅为本机证据）。
  - `git diff --check`：使用临时 index 副本 + `git add -N` 安全纳入 untracked 文件后执行，0 error；临时 index 已删除，真实 index 未改动。
  - `python skills/ai-dev-flow/scripts/workflow_lint.py docs/tasks/DASHBOARD-FE-001.md --format json`：结果见 Outcome 验证证据。
- 依赖审计：`npm audit --audit-level=moderate`（只读，未执行 `audit fix`）报告 10 项漏洞（3 moderate / 6 high / 1 critical），全部位于开发依赖链：`eslint → @eslint/config-array / @eslint/eslintrc → minimatch → brace-expansion`（high，GHSA-mh99-v99m-4gvg）与 `vite / vitest → esbuild`（moderate，GHSA-67mh-4wv8-2f99，dev server 请求伪造）；官方修复需 breaking 升级（eslint 10 / vite 8）。运行时依赖 `ajv` 无已知漏洞，构建产物不受 dev-server 类漏洞影响；是否升级留待独立 Review 与用户决定。
- 规划 Review 边界：上方三轮"四份实施 TASK"Review / Repair / 复审记录的是任务合同（planning）Review `Passed`；它不覆盖、也不代表前端实现代码的 Review。实现代码此后经过三轮独立 Review，第三轮结论为 `Passed`——该结论仅为 2026-07-29 02:5x UTC+8 收据同步时点的历史状态（当时 `review_status=Passed`、UA4 `Pending`），已被后续 UA4 `Failed`（2026-07-29 11:54 UTC+8）与 UA4 修复独立 Review `Needs Fix` 取代，不代表当前状态；历史 Review Passed 不等于用户验收或 Accepted。
- 未验证 / 未发生项：与真实后端的联调未发生（当前只消费 versioned fixtures 与 SSE transcript，经本地 mock 提供）；用户 UA4 实机观察在本节书写时点（2026-07-28 深夜 UTC+8）尚未执行——此后已于 2026-07-29 11:54 UTC+8 执行且结论 `Failed`；audit 报告的开发依赖漏洞未修复；未 commit、未 merge、未 push。

## 实现代码独立 Review Round 1（2026-07-29）

- Reviewer：当前 Codex Harness 独立、ephemeral、read-only 上下文；Kimi 为实施者，不参与 Review 结论。
- 冻结输入：41 个非忽略变更文件，聚合 SHA256 `b20e7cdf5057a03d5da3c151a12d4b94bcc99259d56bd44fd21915fd955c6b3c`；审查后文件数与摘要一致，Workspace writes=None。
- 结论：`Needs Fix`；不允许进入 UA4；最高严重度 P1；Codex finding `P0/P1/P2/P3=0/4/4/0`。
- 阻断 finding：`DASHBOARD-FE-RVW-001-P1-001` 前端私有重排下一动作；`P1-002` 同 revision 的 reset 被忽略；`P1-003` 快照与详情旧响应可覆盖新事实；`P1-004` 1366px 图例遮挡关系内容。
- 追加视觉 finding：`DASHBOARD-FE-RVW-001-P1-005` 诊断抽屉因 transformed ancestor 改变 fixed containing block 而错位到页头，遮挡全局状态，并与 stale/partial 提示重叠。
- 非阻断 finding：`DASHBOARD-FE-RVW-001-P2-001` mock ETag/SSE wire 不精确；`P2-002` 非法 SSE 帧静默忽略；`P2-003` 10 个开发依赖漏洞待独立升级任务；`P2-004` 跨午夜证据日期与旧状态文字不准确。
- 专项边界：固定 pair 条件矩阵由已验收后端门禁证明，前端只展示 wire 结果，不是 FE 缺失实现；真实后端未联调不单独阻止进入 UA4，但不得声称端到端通过。
- Repair authority：用户要求由 Kimi 执行并持续到可验收，允许针对上述 finding 进行有限修复；不授权 commit、merge、push、release、Accepted 或 Closed。

## 实现代码 Repair Round 1（2026-07-29，Kimi）

- `attempt_id`: `DASHBOARD-FE-RVW-001-RC-001-A1`
- `repair_chain_id`: `DASHBOARD-FE-RVW-001-RC-001`
- `finding_ids`: `DASHBOARD-FE-RVW-001-P1-001`、`P1-002`、`P1-003`、`P1-004`、`P1-005`、`P2-001`、`P2-002`、`P2-004`（`P2-003` 仅准确记录，不做 breaking 升级）
- 修改范围：仅 `dashboard/frontend/**` 与本 TASK；`dashboard/contracts/**`、`dashboard/backend/**`、`skills/**` 未触碰；未 commit。

### DASHBOARD-FE-RVW-001-P1-001（前端私有重排下一动作）

- 修复：删除 `src/state/derive.ts` 的私有 `ELIGIBILITY_RANK` 及排序逻辑；`primaryActionByTask` 改为严格取服务器 wire 顺序首项，`actionsByTask` 原样保留 wire 顺序。`tests/makers.ts` 默认动作修正为冻结动作矩阵第 6 行（`execute/needs_authority/execution/unsupported/EXECUTION_AUTHORITY_UNSUPPORTED`）；单元与浏览器测试样本全部改为矩阵合法组合（In Progress→continue、Ready+依赖未满足→execute/blocked、Review→review/needs_authority、Review+Passed+UA Pending→user_decision/actionable、Draft→plan/needs_authority、Merged→release+close 双 recommendation）。
- RED：原测试把私有优先级当 oracle（`needs_authority  beats blocked`），样本含矩阵不可能组合（`execute/actionable`）。
- GREEN：`tests/derive.test.ts` 新增多 recommendation 顺序回归——Merged 任务 wire 顺序 `[release(unknown), close(actionable)]` 主动作必须为 `release`，反转 wire 输入则原样镜像，证明 blocked/needs_authority/unknown 不会被前端重排；Vitest 67/67、Playwright 38/38 通过。

### DASHBOARD-FE-RVW-001-P1-002（同 revision 的 reset_required 被忽略）

- 修复：`src/main.ts` `onSnapshotEvent` 删除同 revision early return；`reset_required=true` 时先同步 `resetViewState()`，再按合同以 `If-None-Match` 重新 GET；304 保留本地快照但绝不撤销 reset。
- RED：原 `tests/browser/sse.spec.ts` 只覆盖"不同 revision + reset"。
- GREEN：新增浏览器测试 `same-revision reset_required clears view state even when GET answers 304`——当前 revision + reset + GET 304 下，选择、聚焦、详情、高亮全部清空，revision 与节点数不变（截图 `sse/same-revision-reset-304.png`）。

### DASHBOARD-FE-RVW-001-P1-003（旧响应覆盖新事实的竞态）

- 修复：`src/main.ts` 快照刷新经单调递增 epoch + Promise 链串行化（initial/retry/health/SSE/协议错误重同步同一队列），被取代的请求启动前与响应落地时两次丢弃；详情请求绑定触发时的 task ID + snapshot revision，`src/state/store.ts` `setDetailReady/setDetailError` 增加 revision 核对，旧 revision 响应不得覆盖。
- RED：原实现允许多个 SSE 刷新与详情请求并发完成，store 只核对 task ID。
- GREEN：浏览器测试用 `page.route` 制造可控乱序——慢 800ms 的旧快照响应无法回退已显示的更新 revision（`sse/out-of-order-snapshot.png`）；慢 800ms 的旧详情响应被丢弃，面板始终显示新 revision 事实（`sse/out-of-order-detail.png`）；`tests/store.test.ts` 覆盖 revision 不匹配时 ready/error 均被忽略。

### DASHBOARD-FE-RVW-001-P1-004（1366px 图例遮挡）

- 修复：`src/styles.css` 图例从绝对定位浮层改为 SVG 下方文档流横条（`.graph-area` 变 flex 列）；图例在 SVG 视口之外，fit 计算天然排除其占用区域，结构上不可能遮挡节点/标签。
- RED：原 `responsive-a11y.spec.ts` 只查横向溢出与 SVG 宽度，旧截图 `width-1366.png` 中图例遮挡 `TASK-GAMMA`。
- GREEN：三个目标宽度均新增 bounding-box oracle——图例矩形与全部可见 `.node/.edge-label/.assessment-label` 零相交；重新生成并目检 `responsive/width-1366/1920/2560.png`。

### DASHBOARD-FE-RVW-001-P1-005（诊断抽屉 fixed containing block 错位）

- 修复：`.diag-drawer` 移出带 `transform` 的 `.overlay-layer`；整个 overlay 体系去 fixed 化——banner/stale strip 为状态栏之下、工作区之上的全宽文档流条（`Overlays.root`），诊断抽屉为主区之后的文档流页脚（`Overlays.drawerRoot`），不再存在 transformed ancestor 与覆盖式定位，stale 提示与抽屉结构上不可能叠加。
- RED：Codex 人工截图发现抽屉错位到页头遮挡全局状态并与 stale/partial 提示重叠。
- GREEN：1366/1920/2560 + stale 场景 bounding-box oracle——抽屉贴底（底边 = 视口高 ±2px）、全宽（x≈0、宽 = 视口宽 ±2px）、与 `.status-bar` 及 `.stale-strip-stale` 零相交，展开后仍在视口内且位于状态栏之下；strip 与状态栏同样零相交；重生成并目检 `responsive/drawer-*-stale(-open).png`。

### DASHBOARD-FE-RVW-001-P2-001（mock ETag/SSE wire 不精确）

- 修复：`vite.config.ts` mock ETag 精确为 `"sha256-<revision>"`（附 `Cache-Control: private, no-cache`）；SSE `retry: 2000`、`X-Accel-Buffering: no`、无快照时 503；初连（无 `Last-Event-ID`）立即发送当前 revision + 全部 task IDs + `reset_required=true`，ID 匹配则等待，不匹配则当前 revision + 空 change list + reset；事件帧统一带 `id: <revision>`；新增 test-only `/__mock__/raw-event` 原始帧注入。
- GREEN：合同级 oracle 测试直接断言 ETag 头、304、`retry: 2000`、初连 reset 帧（含全部 task IDs）、匹配/过期 `Last-Event-ID` 两种重连语义、无快照 503；浏览器断线重连测试验证匹配 ID 重连不产生伪 reset（选择保留）；同 revision reset 测试证明浏览器无手工注入事件时也会收到初连 reset 并正确清空视图。

### DASHBOARD-FE-RVW-001-P2-002（非法 SSE 帧静默忽略）

- 修复：`src/api/sse.ts` 新增 `onProtocolError` 回调，JSON 解析失败与 schema drift 均上报（帧仍丢弃，不污染状态）；`src/main.ts` 接线为可见 `协议错误` banner（`store.setStreamProtocolError`，保留 last-good 快照与连接状态）+ 受控 GET 重同步；成功应用新快照后 banner 自动清除。
- RED：原 `tests/sse.test.ts` 把静默忽略作为期望。
- GREEN：单测覆盖非法 JSON/schema drift 各触发 `onProtocolError` 且恢复后正常投递；浏览器测试注入非法帧与 drift 帧，验证 banner 可见、revision/图不变、有效新 revision 事件后恢复（`sse/protocol-error(-recovered).png`）。

### DASHBOARD-FE-RVW-001-P2-003（开发依赖漏洞，仅记录）

- 处置：本轮不升级（修复需 eslint 10 / vite 8 breaking 迁移，超出 Repair 授权）；`npm audit --audit-level=moderate`（只读，未 `audit fix`）复跑仍为 10 项（3 moderate / 6 high / 1 critical），全部位于开发依赖链（`brace-expansion`、`esbuild` 间接依赖），运行时依赖 `ajv` 无漏洞，构建产物不含 dev-server 面。是否建立独立升级任务留待独立复审与用户决定；不阻止复审进入 UA4 的判定。

### DASHBOARD-FE-RVW-001-P2-004（文档过时表述与跨午夜日期）

- 修复：删除过时的"尚未实施"类表述（此前已随 Review 写回修正为"仍有 P1 finding 待修复"）；实施证据写回与 Outcome 的命令结果与截图时间分别记录真实日期（命令 2026-07-28 深夜 UTC+8，截图跨午夜 2026-07-29 00:28–00:29 UTC+8）；Review/UA 状态不推进。

### Repair Round 1 验证证据（2026-07-29 fresh）

- `npm run verify` 全链通过：`codegen:check` 同步；`typecheck` 通过；`lint` 0 error；Vitest 5 文件 67/67；`vite build` 通过（JS 194.6 kB，gzip 59.9 kB）；Playwright 4 spec 38/38（40.4s）。
- 截图 44 张（git-ignored 本机证据），新增/重生成：responsive 9（三宽度 + 三宽度 stale 抽屉开合）、sse 12（含 same-revision-reset-304、out-of-order-snapshot/detail、protocol-error(-recovered)）；已逐张目检三宽度、stale 抽屉与协议错误截图，无遮挡、无错位。
- `npm audit --audit-level=moderate`（只读）：10 项（3 moderate / 6 high / 1 critical），同上记录。
- targeted `workflow_lint`：`errors/violations/warnings=0/0/1`，唯一 warning 同前（Uncommitted 无 Git transition history）。
- `git diff --check`（临时 index 副本 + `git add -N` 纳入 untracked，真实 index 未改动）：0 error。
- 状态边界：本记录不推进任何状态——`lifecycle=Needs Fix`、`review_status=Needs Fix`、UA4 `Pending`、`Uncommitted/Unmerged`；是否关闭各 finding 由下一轮 Codex 独立复审判定，实施者不自批。

## 实现代码独立 Review Round 2（2026-07-29，Codex 复审）

- Reviewer：当前 Codex Harness 独立、ephemeral、read-only 上下文；Kimi 为实施者，不参与 Review 结论。
- 冻结输入：41 个非忽略变更文件，聚合 SHA256 `c3576c15404fb3b170a4a0c913663ee7760171d590a73c89d5bda3598094a78d`；branch `codex/dashboard-fe-001`，HEAD/base `fc34f11d7a1079f1ba84d22adaf61d0b973136d4`。
- 结论：`Needs Fix`；不允许进入 UA4；最高严重度 P1；`P0/P1/P2/P3=0/2/6/0`；第一轮无回归。
- 第一轮复审：`P1-001`、`P1-002`、`P1-004`、`P1-005`、`P2-001` Closed；`P1-003`、`P2-002` Open（部分修复）；`P2-003`、`P2-004` Open。
- 阻断 finding（仅这两个 P1 阻断 UA4）：`DASHBOARD-FE-RVW-001-P1-003` 详情路径未校验成功 payload 的 `TaskDetail.revision` 与错误 envelope 非空 revision 是否等于触发 revision，旧页面可接受另一 revision 的详情；新增 `DASHBOARD-FE-RVW-002-P1-001` Toolbar 每次状态更新重建搜索框与 checkbox，真实逐字键盘输入与连续键盘筛选丢焦点。
- 新增非阻断 finding：`DASHBOARD-FE-RVW-002-P2-001` 响应 body 读取异常被静默吞掉；`P2-002` mock 在有快照时错误 envelope revision 仍为 null，违反冻结合同；`P2-003` 实时更新重建诊断抽屉丢失无障碍焦点与展开状态。
- 专项边界：P2 均可拆为后续任务，不单独阻止 UA4；真实后端集成未发生，不得声称端到端通过；10 项开发依赖漏洞为本地 dev 工具链风险；固定 pair 条件矩阵仍属后端门禁，FE TASK 该项保持未勾选是正确边界。
- Repair authority：用户要求由 Kimi 执行 Repair Round 2；不授权 commit、merge、push、release、Accepted 或 Closed，是否关闭各 finding 由下一轮 Codex 独立复审判定。

## 实现代码 Repair Round 2（2026-07-29，Kimi）

- `attempt_id`: `DASHBOARD-FE-RVW-002-RC-001-A1`
- `repair_chain_id`: `DASHBOARD-FE-RVW-002-RC-001`
- `finding_ids`: `DASHBOARD-FE-RVW-001-P1-003`、`DASHBOARD-FE-RVW-002-P1-001`、`DASHBOARD-FE-RVW-001-P2-002`、`DASHBOARD-FE-RVW-002-P2-001`、`DASHBOARD-FE-RVW-002-P2-002`、`DASHBOARD-FE-RVW-002-P2-003`、`DASHBOARD-FE-RVW-001-P2-004`（`DASHBOARD-FE-RVW-001-P2-003` 仅 fresh 记录，不做 breaking 升级）
- 修改范围：仅 `dashboard/frontend/**` 与本 TASK；`dashboard/contracts/**`、`dashboard/backend/**`、`skills/**` 未触碰；未 commit。

### DASHBOARD-FE-RVW-001-P1-003（详情 payload / 错误 envelope revision 精确校验）

- 修复：`src/main.ts` `loadDetail` 在 epoch 与触发 revision 核对之外，新增两道精确校验——成功 payload 的 `TaskDetail.revision` 必须等于触发时的 snapshot revision，否则丢弃该响应并触发一次受控快照重同步（304 不落地任何变更，revision 对齐后由快照更新路径自动重取详情，无循环）；错误 envelope 的非空 `revision` 不等于触发 revision 时同样丢弃并重同步。`src/state/store.ts` `setDetailReady` / `setDetailError` 增加同规则的最后防线（payload revision 不匹配、envelope 非空 revision 不匹配均忽略），跨 revision 详情与错误均不得显示。
- GREEN：store 单测新增 2 例（payload 自身 revision ≠ 触发 revision 时保持 loading、匹配后 ready；envelope 非空 revision 不匹配忽略、null 或匹配时应用）；浏览器 oracle 新增 `a current reply whose payload revision mismatches is discarded and the panel recovers`——当前请求返回 revision B 的 payload 而快照为 A 时，面板保持"正在加载"、不显示跨代标题、不回退任何旧事实，快照推进到 B 后同一 payload 被正常接受（截图 `sse/detail-revision-mismatch-dropped.png` / `-recovered.png`）。

### DASHBOARD-FE-RVW-002-P1-001（Toolbar 键盘输入丢焦点）

- 修复：`src/ui/toolbar.ts` 改为增量更新——搜索 input 构造一次、永不重建，更新只跳过它本身，其值仅在外部变更（如"清除筛选"）时同步，焦点、光标与选择区间天然保留；filter panel 以选项结构 key 判定，结构不变时原地更新 checkbox `checked`（DOM 身份保留），结构真正变化重建时按稳定 input id 恢复焦点；checkbox change handler 改读当前 store 状态，避免闭包捕获旧 filters。
- GREEN：Playwright 新增 2 例——真实 `keyboard.type` 逐字输入 `EPSILON`，逐字符断言完整值与焦点，并验证光标保留（继续键入追加为 `EPSILONX`）与筛选结果；键盘 Space 连续切换 `Ready`、`Review` 两个筛选项并再次切回，逐次断言 `checked`、焦点停留与节点过滤结果（截图 `graph/search-keyboard-focus.png`、`graph/filter-keyboard-focus.png`）。

### DASHBOARD-FE-RVW-001-P2-002（非法 SSE 后 304 重同步不清除 protocol 错误）

- 修复：`src/state/store.ts` 新增 `protocolErrorActive` 标记与 `clearProtocolError()`——只清除 `setStreamProtocolError` 设置的协议错误，`setPhaseError` 的真实失败不受影响；`src/main.ts` 受控重同步收到 304（本地快照已最新，重同步成功）时调用清除，200 路径本即经 `setSnapshot` 清除。不会形成循环：清除不触发任何新请求。
- GREEN：store 单测新增 1 例（protocol 错误可清、network 失败不可清、真实失败覆盖 protocol 标记）；浏览器测试改为确定性时序（路由延迟使短暂 banner 可观察）：非法帧 banner 可见 → 受控 304 重同步自动清除且快照/图/连接不变；随后构造真实失败（abort 的 GET）banner 可见，同 revision 304 重读不清除，仅新 revision 200 清除（截图 `sse/protocol-error.png`、`sse/protocol-error-recovered-304.png`、`sse/protocol-error-recovered.png`）。

### DASHBOARD-FE-RVW-002-P2-001（响应 body 读取异常静默吞掉）

- 修复：`src/api/client.ts` 把 `response.text()` 纳入 try/catch，读取异常映射为 `network` failure——快照路径因此进入 `setPhaseError` 可见 banner + 健康轮询/重试，而不是被 Promise 链静默吞掉；`vite.config.ts` mock 新增 test-only `/__mock__/truncate` 一次性钩子（先 `flushHeaders` 并写出部分 body、再延迟销毁 socket，规避 Chrome 对零字节连接重置的幂等 GET 自动重试）。
- GREEN：新增 `tests/client.test.ts` 3 例（快照/详情的 body 读取 reject 均映射 network、fetch 层 reject 仍映射 network）；浏览器新增 `a snapshot reply that drops mid-body surfaces a network error and the event chain recovers`——截断响应后 banner 可见、保留旧 revision，后续事件链重同步成功并应用最新 revision（截图 `sse/body-read-failure.png`、`sse/body-read-recovered.png`）。

### DASHBOARD-FE-RVW-002-P2-002（mock 错误 envelope revision 违反合同）

- 修复：`vite.config.ts` mock 统一 `errorRevision`：存在当前快照时 `TASK_NOT_FOUND`、`ROUTE_NOT_FOUND` envelope `revision` 为当前 revision，无快照时才为 null（503 `SNAPSHOT_UNAVAILABLE` 路径本就只在无快照时出现，保持 null，符合父合同 `:565`）。
- GREEN：mock wire oracle 新增 `error envelopes carry the current revision with a snapshot, null without`——直接请求未知任务与未知路由，分别在有/无快照状态精确断言 HTTP status（header 级）与 envelope `error.code`/`revision`（body 级）。

### DASHBOARD-FE-RVW-002-P2-003（实时更新重建诊断抽屉丢焦点）

- 修复：`src/ui/overlays.ts` 抽屉改为增量更新——以 diagnostics 内容 key 判定，内容不变时 toggle 与列表保持 DOM 身份（焦点与展开状态天然保留，`aria-expanded` 与列表 `hidden` 再同步）；内容真正变化时重建，若焦点原在抽屉内则恢复到唯一可聚焦的 toggle；抽屉消失（无诊断）时才移除。
- GREEN：Playwright 新增 `drawer keeps focus and expanded state across snapshot and connection updates`——打开抽屉并聚焦 toggle 后，revision 更新与 SSE 断线/重连均保持焦点、`aria-expanded=true` 与列表可见；新增诊断内容触发重建后焦点恢复到 toggle 且展开状态不变（截图 `sse/drawer-focus-kept.png`、`sse/drawer-focus-restored-after-rebuild.png`）。

### DASHBOARD-FE-RVW-001-P2-003（开发依赖漏洞，仅 fresh 记录）

- 处置：本轮不升级（修复需 eslint 10 / vite 8 breaking 迁移，超出 Repair 授权，且用户明确禁止 `audit fix` 与 breaking 升级）；fresh `npm audit --audit-level=moderate`（只读，退出码 1）仍为 10 项（3 moderate / 6 high / 1 critical），全部位于开发依赖链（`brace-expansion`、`esbuild` 间接依赖），运行时依赖仅 `ajv` 无漏洞，构建产物不含 dev-server 面；风险限于本机 Vite dev server，运行时不应暴露给不可信网络。保持为开放 P2，留待独立复审与用户决定是否建立独立升级任务。

### DASHBOARD-FE-RVW-001-P2-004（文档当前/历史状态歧义）

- 修复：`验收建议` 改为"两轮独立 Review 均 Needs Fix、第二轮 2 个 P1 已定向修复、仍未通过独立复审"；规划 Review 边界段改为"实现已经过两轮独立 Review（Needs Fix），review_status=Needs Fix，等待复审"；原"实施证据写回"节明确标注为历史 initial implementation 记录（62/62、28/28、33 张截图、2026-07-29 00:28–00:29 UTC+8），已被 Repair Round 1/2 证据替代；Outcome 节同步标注历史段并以真实时间记录 Round 2 证据。
- 附带修复：`src/main.ts` subscribe 回调首行格式瑕疵（多余行内空格）已修正。

### Repair Round 2 验证证据（2026-07-29 fresh，命令与截图均为 2026-07-29 01:5x–02:2x UTC+8 真实时间）

- `npm run verify` 全链通过：`codegen:check` 同步；`typecheck` 通过；`lint` 0 error；Vitest 6 文件 73/73；`vite build` 通过（JS 196.5 kB，gzip 60.3 kB）；Playwright 4 spec 45/45（49.8s）。
- 截图 53 张（git-ignored 本机证据），新增/重生成并目检：`sse/detail-revision-mismatch-dropped(-recovered)`、`sse/protocol-error(-recovered/-recovered-304)`、`sse/body-read-failure(-recovered)`、`sse/drawer-focus-kept`、`sse/drawer-focus-restored-after-rebuild`、`graph/search-keyboard-focus`、`graph/filter-keyboard-focus` 及既有三宽度/抽屉/乱序/重连截图。
- `npm audit --audit-level=moderate`（只读，退出码 1，未 `audit fix`）：10 项（3 moderate / 6 high / 1 critical），同上记录。
- targeted `workflow_lint`：`errors/violations/warnings=0/0/1`，唯一 warning 同前（Uncommitted 无 Git transition history）。
- `git diff --check`（临时 index 副本 + `git add -N` 纳入 untracked，真实 index 未改动）：0 error。
- 状态边界：本记录不推进任何状态——`lifecycle=Needs Fix`、`review_status=Needs Fix`、UA4 `Pending`、`Uncommitted/Unmerged`；是否关闭各 finding 由下一轮 Codex 独立复审判定，实施者不自批。

## 实现代码独立 Review Round 3（2026-07-29）

- Reviewer：原生 Codex CLI 的独立、ephemeral、read-only 审查上下文；Kimi 为实施者，不参与 Review 结论；审查期间 Workspace writes=None。
- 冻结输入：base/HEAD `fc34f11d7a1079f1ba84d22adaf61d0b973136d4`，40 个 `dashboard/frontend/**` 非忽略文件 + 本 TASK + Board 投影，共 42 个文件。主控冻结算法为按路径排序后聚合 `path<TAB>file_sha256`（LF 连接），摘要 `3061071fe06346d3b32a54d5e6a72c75f590e137bce031b520cfd7ef84a4ba82`；Reviewer 另用 `path<NUL>file_sha256<LF>` 在审查前后复算均为 `dcc61e9dae5bd38eebd3534344eae53893f6d50a4e1b5c18458aaddcdd725cc2`。
- 结论：`Passed`；允许进入 `UA4 Pending`；最高开放严重度 P2；冻结输入的 `P0/P1/P2/P3=0/0/4/0`；无 Regressed。
- P1 闭环：`DASHBOARD-FE-RVW-001-P1-003`（详情 revision 精确绑定）与 `DASHBOARD-FE-RVW-002-P1-001`（搜索/checkbox 键盘焦点）Closed；上一轮已关闭的 `P1-001/P1-002/P1-004/P1-005` 均保持 Closed。
- P2 闭环：`DASHBOARD-FE-RVW-002-P2-001`（body 读取失败）、`P2-002`（mock error revision）、`P2-003`（diagnostics drawer 焦点）Closed；上一轮已关闭的 `DASHBOARD-FE-RVW-001-P2-001`（mock ETag/SSE wire）保持 Closed。
- 开放 `DASHBOARD-FE-RVW-001-P2-002`：普通“协议错误→304”与“真实错误→304”路径正确；但若先发生 network/server error、随后又发生协议错误，再收到 304，共用的 `phaseError + protocolErrorActive` 会清除被覆盖的真实错误。该组合序列未被现有测试覆盖，保持 P2。
- 开放 `DASHBOARD-FE-RVW-001-P2-003`：开发依赖链仍有 10 项漏洞（3 moderate / 6 high / 1 critical）；运行时依赖仅 Ajv，风险限于本地开发工具链，保持 P2。
- 新增 `DASHBOARD-FE-RVW-003-P2-001`：详情收起按钮、关系图节点与 highlight chip 在普通状态更新时仍会因整段 DOM 重建而丢失键盘焦点；不阻止 UA4，但需后续按稳定 task/control ID 保持或恢复焦点，并补真实键盘 oracle。
- `DASHBOARD-FE-RVW-001-P2-004` 在冻结输入中仍为 Open：Outcome 把当前 frontend 文件数写成 39，且历史节残留字面量 `\r`。本次仅作审查收据同步时已机械修正为 40 个 frontend 文件并删除字面量，不涉及功能代码；经最终 lint/diff 复核后作为文档项关闭。
- 独立验证边界：Reviewer 完整阅读规则、TASK、父合同、schema、fixtures、全部 frontend 源码与相关测试，目检关键截图并确认 53 张截图存在；未独立运行可能写缓存/产物的 Vitest、Playwright、build、typecheck、lint、codegen、workflow_lint 或 audit。Kimi 的 73/73、45/45 与 audit 10 项在该轮仅作为已有实施收据，不替代主控最终 fresh 验证。
- 权限边界：本结论不是 Accepted，不授权 commit、merge、push、release、交付或 Closed；真实后端尚未联调，UA4 仍需用户判断关系图的直观性和易读性。

<a id="ua4-user-feedback-round-1"></a>

## UA4 用户验收反馈 Round 1（2026-07-29 11:54 UTC+8）

- 结论：`Failed / None`。用户反馈“搜索好像有问题，搜了没反应”，并明确要求页面“更好看、优雅、有品味一点，让我看着舒服一点”；当前任务回到 `Needs Fix`，不得维持 Review Passed 或进入 Accepted。
- 反馈分类：原任务未完成
- 是否属于当前 TASK 范围：是
- 下一步建议：进入审查-修复循环（review_repair_loop）
- RED 失败信号：搜索状态虽然写入前端，但匹配项与非匹配项被组合筛选统一压暗，用户看不到明确搜索反馈；现有视觉层级、密度与空间利用也未达到用户明确提出的舒适、优雅和有品味要求。
- GREEN 通过信号：搜索在任意 quick highlight / focus 组合下都能清楚区分匹配与非匹配结果，并同步结果计数、空状态和详情；三个冻结 viewport 的页面层级、密度、对齐、配色与空间利用达到本节两个 P1 closure contract，且完整验证、独立 Review 和用户重新 UA4 均按顺序完成。
- SIGNAL 证据来源：用户文字反馈与截图（下列固定路径和 SHA256），以及主控对同一页面的 DOM / computed-style 只读取证。
- SIGNAL：用户截图 `C:/Users/92336/AppData/Local/Temp/codex-clipboard-98d86de5-3894-4fee-ac38-cb9714faeec6.png`，SHA256 `af108206e7de6a9016ed7f578c29c65ed4f796609f02e528de10ca61e343393a`；本机页面 `http://127.0.0.1:5173/`；主控浏览器 DOM / computed-style 只读取证。
- 分类：原 TASK 的“搜索筛选应有明确可观察结果”和 UA4 易读性完成标准未满足；用户同时明确扩大视觉品质要求。建立新的 UA finding / closure contract，不沿用或清零旧 finding 历史。

### DASHBOARD-FE-UA4-001-P1-001（搜索与 quick highlight 组合后无可辨识反馈）

- RED：先启用“需要决定”，再搜索 `gamma`。状态层确实为 4 个非匹配节点加上 `node-filtered`，但 quick highlight 又给包括唯一匹配 `TASK-GAMMA` 在内的全部 5 个节点加上 `node-dimmed`；浏览器实测 5 个节点 computed opacity 均为 `0.28`、仍为 visible，匹配项没有结果计数或显著强调，详情仍显示被过滤的 `TASK-ALPHA`。用户截图与 DOM 信号一致，用户感知为“搜了没反应”。
- GREEN：任意 quick highlight / focus 组合下，非空搜索或结构筛选必须产生清楚且一致的可观察结果；匹配节点不得与非匹配节点同等变暗，非匹配节点不可继续抢占主要视觉注意力；显示匹配计数与无结果提示；当前详情若已不属于可见结果，必须清空或切换到唯一明确匹配项，不能展示与搜索不一致的旧任务。
- 验证：浏览器真实键盘输入 `gamma`，覆盖 highlight=none / actionable / candidates / decisions；逐项断言匹配/非匹配节点的 class、computed opacity 或 visibility、结果计数、详情一致性、清除搜索恢复；补 1440×900 截图和无结果截图。

### DASHBOARD-FE-UA4-001-P1-002（视觉品质未达到用户验收）

- RED：用户明确拒绝当前视觉品质。截图显示状态信息和工具条层级偏平、边框密集、控件与文字过于紧凑、画布有效内容比例偏小、详情侧栏压迫且信息密度缺少节奏；整体更像调试控制台，未达到“优雅、有品味、看着舒服”的产品体验。
- GREEN：采用克制、专业、安静的工作台方向，在不改变只读合同与核心功能的前提下，统一颜色/字体/间距/圆角/边框/阴影 token，重整状态栏、搜索与筛选区、并行评估、关系图节点/连线、详情面板和诊断区域的视觉层级；桌面画布更充分利用空间，详情信息更易扫描。禁止随机紫蓝渐变、玻璃拟态、过度圆角、装饰性光斑、卡片套卡片和新增大型依赖。
- 无障碍/响应式硬条件：所有状态继续使用文字/符号/线型，不仅依赖颜色；保留 focus-visible、reduced motion 和合同字段完整性；1440×900、1024×768、390×844 无文字重叠、裁切、意外横向滚动、固定区遮挡或空白画布。
- 验证：保留用户截图为 before 信号；Kimi 生成 after 截图并逐张目检三个 viewport，覆盖默认关系图、搜索 `gamma`、筛选展开、任务详情、stale/partial 与诊断抽屉；完整 `npm run verify`、dependency audit、workflow_lint 和 diff 范围检查；修复后必须重新独立 Review，再由用户重新执行 UA4。

- 允许修改范围：`dashboard/frontend/**`、本 TASK、`docs/TASK_BOARD.md` 的唯一 DASHBOARD-FE-001 投影行。
- 禁止范围：`dashboard/backend/**`、`dashboard/contracts/**`、`skills/**`、依赖 breaking 升级、新生产依赖、commit/merge/push/release/Accepted/Closed。
- 实施者：用户明确要求把两项反馈交给 Kimi；Kimi 可先只读诊断，再在上述冻结 closure contract 内实施，不得自批通过。

### UA4 Round 1 修复实施与验证收据（2026-07-29 12:4x UTC+8，Kimi）

- 修改范围：仅 `dashboard/frontend/**`（untracked）与本 TASK、Board 投影行收据；`dashboard/backend/**`、`dashboard/contracts/**`、`skills/**` 未触碰；无新增依赖、无 breaking 升级、未 `audit fix`、未 commit/merge/push。

#### DASHBOARD-FE-UA4-001-P1-001 实施

- 搜索优先级：`src/state/derive.ts` 新增导出纯函数 `taskMatchesText()`（与 `filterTasks` 共用同一文本谓词）；`src/ui/graph/graphView.ts` 在搜索文本非空时 dimming 完全由文本匹配决定——匹配节点加 `node-match`（accent 描边加粗 + `◈ 搜索匹配` 非颜色角标 + aria 追加“搜索匹配”），绝不因 quick highlight/focus 组合加 `node-dimmed`；非匹配节点一律 `node-dimmed`。搜索为空时原 highlight/focus 语义逐字保留。
- 计数与空状态：`src/ui/toolbar.ts` 搜索框旁新增 `role="status"` 的 `.search-status`（`匹配 X / 共 Y 个任务`，零结果时 `无匹配结果` + `search-status-empty`）；零匹配时图内渲染居中空状态文本。搜索 input 仍构造一次永不重建（既有键盘焦点合同未动）。
- 详情同步：`derive.ts` 新增纯函数 `resolveSelectionAfterFilter()`（选择仍可见→不动；不可见且唯一可见→切换；零/多结果→清空）；`src/main.ts` 在 filters 变化时应用，无选择时绝不自动选中。

#### DASHBOARD-FE-UA4-001-P1-002 实施

- `src/styles.css` 整体重写（class 名与 DOM 钩子全保留）：统一 token（8px 间距节奏、圆角 ≤6px、字号阶、降对比边框、降饱和状态色、克制蓝 accent，light/dark 双套）；状态栏、搜索/筛选、highlight chips（安静文本按钮 + accent 激活态）、并行评估、图节点/连线、详情面板（420px、节标题层级、def-table 去密集行线、卡片改极浅底+左状态条）、诊断区域全部重整；无紫蓝渐变/玻璃拟态/过度圆角/装饰光斑/卡片套卡片/新依赖；focus-visible、reduced motion、非颜色状态表达、只读语义与合同字段全部保留。

#### 验证证据（fresh，2026-07-29 12:3x–12:4x UTC+8）

- `npm run verify` 退出码 0：codegen:check 同步；typecheck 通过；lint 0 error；Vitest 6 文件 81/81（新增 `taskMatchesText` 4 例、`resolveSelectionAfterFilter` 4 例）；vite build 通过（JS 197.6 kB / gzip 60.7 kB，CSS 14.3 kB）；Playwright 6 spec 59/59（原 45 + 新增 14）。
- P1-001 组合 oracle（`tests/browser/search.spec.ts` 8 例，真实 `keyboard.type`）：highlight=none/actionable/candidates/decisions 下搜索 `gamma`，TASK-GAMMA 均有 `node-match` 无 `node-dimmed`、computed opacity=1，其余节点 `node-dimmed` 且 opacity<0.5，计数“匹配 1 / 共 5 个任务”；search × upstream focus 匹配节点不 dimmed；零结果有计数/空状态/详情清空；详情跟随唯一匹配切换、多结果清空；清除后全节点 opacity=1 恢复；既有 `search-keyboard-focus`、`filter-keyboard-focus` 焦点回归仍绿。
- P1-002 响应式 oracle（`responsive-a11y.spec.ts` 新增 `frozen UA4 viewports`）：1440×900、1024×768 无横向溢出、SVG 非空、图例与节点/标签零相交；390×844 纵向堆叠、无横向滚动、画布非空；1366/1920/2560 既有回归未改仍绿。
- after 截图 18 张（git-ignored 本机证据）已逐张目检：`artifacts/screenshots/after/`（default/search-gamma-highlight/filter-panel/detail-alpha/diag-drawer-open/stale/partial/dark-default/dark-search-gamma @1440，default @1024/@390）与 `artifacts/screenshots/search/`（gamma 无 highlight、三种 highlight 组合、focus-upstream、no-results、detail-follows-unique-match）——无重叠、裁切、意外横向滚动、遮挡或空白画布（stale/partial fixture 本身 tasks=0，空画布为数据语义）。
- `npm audit --audit-level=moderate`（只读，未 fix）退出码 1：10 项（3 moderate / 6 high / 1 critical），与基线一致，全在开发依赖链，运行时 ajv 无漏洞。
- targeted `workflow_lint`（TASK 与 Board 均）：退出码 0，`errors/violations/warnings=0/0/1`，唯一 warning 同前（Uncommitted 无 Git transition history）。
- whitespace/diff 范围检查：临时 index 副本 + `git add -N` 纳入全部 untracked 后 `git diff --check` 退出码 0，真实 index 未改动；`git status` 确认改动仅 `dashboard/frontend/**` 与本 TASK、Board 投影行。
- 状态边界：本收据不推进任何状态——`lifecycle=Needs Fix`、`review_status=Needs Fix`、`ua_status=Failed`、`acceptance_authority=None`、`Uncommitted/Unmerged`；两个 P1 是否关闭由下一轮独立 Review 判定，用户重新 UA4 前不得视为验收通过。

### UA4 修复独立 Review Round 1（2026-07-29 12:47–12:55 UTC+8，Codex）

- 冻结输入：base/HEAD `fc34f11d7a1079f1ba84d22adaf61d0b973136d4`；42 个非忽略 `dashboard/frontend/**` 文件 + 本 TASK + Board 投影行；Kimi 为实施者，不参与 Review 结论。
- 独立验证：主控无管道 fresh 执行 `npm run verify`，退出码 0（Vitest 6 文件 81/81、Playwright 6 spec 59/59、typecheck/lint/build 全部通过）；`npm audit --audit-level=moderate` fresh 退出码 1，仍为 10 项开发依赖链漏洞；TASK/Board workflow_lint 均为 `0 error / 0 violation / 1 warning`；tracked 文档 diff check 0 error。
- Review 结论：`Needs Fix`；`P0/P1/P2/P3=0/4/1/0`；不允许进入用户重新 UA4。原用户复现的 search × quick-highlight 症状已定向修复，但两个 UA4 finding 均因下列阻断项尚未满足完整 closure contract 而保持 Open。

#### DASHBOARD-FE-UA4-RVW-004-P1-001（搜索覆盖结构筛选的 AND 语义）

- RED：主控在真实浏览器中先搜索 `gamma`，再勾选生命周期 `Ready`；`filterTasks()` 的组合结果为 0，但页面仍显示“匹配 1 / 共 5 个任务”，`TASK-GAMMA` 同时具有 `node-match node-filtered` 且 computed opacity=`1`，无图内零结果提示。原因是 `graphView.ts` 搜索非空时完全绕过 `visible`，`toolbar.ts` 计数只算文本谓词。
- GREEN：Graph 的 `node-match`、亮暗、计数、空状态和详情必须消费同一个“全部结构筛选 AND 文本搜索”的组合结果集；搜索只覆盖 quick highlight/focus 的压暗，不得覆盖 lifecycle/risk/class/module/Worktree/severity 等结构筛选。补 search × lifecycle/risk/severity/Worktree 的真实浏览器 oracle。

#### DASHBOARD-FE-UA4-RVW-004-P1-002（视觉 token 未满足 WCAG 2.2 AA）

- RED：独立静态颜色计算显示 dark `--faint #6f7987` 在 `--surface`/`--surface-2` 约为 3.79/3.45:1，light `--faint #79838f` 在白色/`--surface-2` 约为 3.85/3.43:1，低于普通小字 4.5:1；light `--edge #8b95a1` 在背景约 2.76:1，低于非文本图形 3:1。现有测试仅抽查 status/node ID/legend，未覆盖实际 faint 元素和 dark theme。
- GREEN：提高 light/dark 的 faint、edge 与必要 border token 对比度；为两种主题的实际小字号语义元素和关键关系线增加机器对比度 oracle，普通小字 ≥4.5:1、关键非文本图形 ≥3:1。

#### DASHBOARD-FE-UA4-RVW-004-P1-003（合法长合同字段可在冻结 viewport 溢出）

- RED：合同对 task ID、title、source path 等无长度上限；`.filter-option` 强制 nowrap，详情标题/字段和多个 flex 子项缺少 `min-width:0`、`overflow-wrap`/`word-break`。现有 1024/390 只用短 fixture，且未覆盖搜索、展开筛选、长详情、stale/partial 与诊断抽屉的完整冻结状态矩阵。
- GREEN：状态栏、toolbar、filter option、pair 内容、详情标题/单元格等长内容可收缩或安全换行；用 schema-valid 极长 task ID/title/Worktree/source path 在 1440×900、1024×768、390×844 覆盖默认、搜索、筛选展开、详情、stale/partial、诊断抽屉，断言无横向溢出、遮挡或裁切。dark 截图必须由可重现测试生成。

#### DASHBOARD-FE-UA4-RVW-004-P1-004（TASK 当前事实源互相矛盾）

- RED：`验收建议` 与 Outcome 仍声称历史第三轮 Review Passed/允许进入 UA4，并把 40 个 frontend 文件、73/73、45/45、历史 Repair Round 2 写成“当前有效”；Outcome 还残留 `User Confirmed`，与 canonical `acceptance_authority=None` 冲突。
- GREEN：旧 Review/验证全部明确标成历史；Outcome 只保留一套当前状态和最新文件数/验证/Review 结论；删除未标轴的 `User Confirmed`；Board 与 TASK 一致保持 `Needs Fix / Review Needs Fix / UA4 Failed / None`，直到新的独立 Review。

#### DASHBOARD-FE-UA4-RVW-004-P2-001（非阻断，保持开放）

- localStorage 只验证 JSON 为对象，没有逐字段类型/有限数值校验；旧版本或损坏同源数据可令 `.trim()`/`.includes()` 抛错。该项不阻止本轮 UA4 视觉/搜索修复，但需后续白名单归一化并增加 reload 测试，或保持为显式开放 P2。

- Repair Round 2 允许范围与前述相同；禁止新增依赖、修改 backend/contracts/skills、执行 `audit fix` 或推进 commit/merge/push/Accepted/Closed。

### UA4 Repair Round 2 实施与验证收据（2026-07-29 13:0x–13:2x UTC+8，Kimi）

- 修改范围：仅 `dashboard/frontend/**`（untracked）与本 TASK、Board 投影行收据；backend/contracts/skills 未触碰（lint 产生的 `skills/**/__pycache__` 缓存副产物已删除还原）；无新增依赖、无 breaking 升级、未 `audit fix`、未 commit/merge/push。

#### DASHBOARD-FE-UA4-RVW-004-P1-001（搜索覆盖结构筛选 AND 语义）

- 修复：`src/ui/graph/graphView.ts` 搜索非空时 `searchMatched = filterTasks()` 组合集（结构筛选 AND 文本搜索），`node-match`/dimming/零匹配空状态全部消费该集合；`src/ui/toolbar.ts` 计数改为同一 `filterTasks().size`。搜索只覆盖 quick highlight/focus 的压暗，不再覆盖 lifecycle/risk/class/module/Worktree/severity。`resolveSelectionAfterFilter` 本就消费 `filterTasks`，与图对齐。
- RED→GREEN：新 oracle 在旧代码 5 failed / 1 passed；修复后 search+graph 25/25 绿。新增 `search × structural filters: AND semantics` 6 例（lifecycle/risk/severity/Worktree 逐项排除文本匹配项，断言 class、computed opacity、计数、空状态、详情一致性与取消恢复；AND 交集 `匹配 2 / 共 5`；选中匹配被结构排除后详情清空不复活）。Round 1 全部用例未删改仍绿。

#### DASHBOARD-FE-UA4-RVW-004-P1-002（WCAG 2.2 AA 对比度）

- 修复：dark `--faint #6f7987→#8a93a1`、light `--faint #79838f→#646e7a`、light `--edge #8b95a1→#7a8492`（faint 保持辅助 meta 亮度）。
- RED→GREEN：新 oracle 首跑失败（dark legend-note 3.79 < 4.5，与 Review 计算一致）；修复后 13/13 绿。`responsive-a11y.spec.ts` 新增用例在 dark/light 两主题（`emulateMedia`）下用相对亮度公式计算真实 computed 值：`--faint` 实际元素（legend-note/pair-reasons/detail-disclaimer/node-class）≥4.5，关键非文本图形（edge-line/assessment-line stroke）≥3。

#### DASHBOARD-FE-UA4-RVW-004-P1-003（长字段溢出与冻结 viewport 矩阵）

- 修复：status/toolbar/filter option/pair/详情标题/def-table td/worktree/诊断等 20 处加 `min-width:0`+`overflow-wrap:anywhere`（或去强制 nowrap）；`node-id` 加截断。长字段 payload 由测试内深拷贝 versioned fixture 注入极长 task_id/title/worktree/source_path 并经 `validateContract` 校验（未触碰 contracts）。
- GREEN：`tests/browser/long-fields.spec.ts` 9 例——1440×900/1024×768/390×844 ×（默认→搜索→筛选展开→长详情→诊断抽屉）+ stale/partial × 3 viewport，断言无 document 级横向溢出、status/toolbar 不越出视口、detail-panel 无横向溢出。dark default/search 截图已移入 `visual.spec.ts` 可重现测试（`emulateMedia colorScheme dark`），不再依赖手工脚本。

#### DASHBOARD-FE-UA4-RVW-004-P1-004（TASK 事实源冲突）

- 修复：「验收建议」不再声称历史第三轮 Review Passed 可进入 UA4，改为指向当前最新 Review 结论；Outcome 收敛为单一当前事实源（42 个 frontend 文件、当前有效验证、当前 Review 状态），旧 40 文件/73/73/45/45/历史 Round 全部明确标注为历史审计轨迹；删除未标轴的 `User Confirmed`，与 canonical `acceptance_authority=None` 一致；补回 contract 必需的 `Review findings`/`验证证据` 字段并保持 Base/Diff 机器格式。

#### DASHBOARD-FE-UA4-RVW-004-P2-001（localStorage 类型归一化）

- 处置：保持开放 P2，本轮未修（优先 4 个 P1）；明确记录，不漏报不清零。

#### 验证证据（fresh，真实退出码，无管道掩盖）

- `npm run verify` 退出码 0：codegen:check 同步、typecheck 通过、lint 0 error、Vitest 6 文件 81/81、build 通过（JS 197.5 kB / gzip 60.6 kB，CSS 14.8 kB）、Playwright 7 spec 76/76（59 + search×结构 6 + 对比度 1 + long-fields 9 + dark 1）。
- `npm audit --audit-level=moderate`（只读，未 fix）退出码 1：10 项（3 moderate / 6 high / 1 critical），与基线一致，全在开发依赖链。
- targeted `workflow_lint`（TASK 与 Board 均）：退出码 0，`errors/violations/warnings=0/0/1`（唯一 warning 同前）。
- whitespace/diff 范围检查：临时 index 副本 + `git add -N` 纳入全部 untracked 后 `git diff --check` 退出码 0，真实 index 未改动；`git status` 确认改动仅 `dashboard/frontend/**` 与本 TASK、Board 投影行。
- 截图（git-ignored）已逐张目检：新增 `long-fields/`（matrix-1440/1024/390、stale/partial × 3 viewport）与 `search/and-intersection.png`，重生成 `after/`（含可重现 dark default/search）；长 id/标题在 pair 按钮、详情、节点均安全换行或截断，无溢出/遮挡；390×844 下“详情+抽屉同时展开”时图区可视段较小（workspace 内滚动可恢复，非溢出/遮挡违例，如实记录）。
- 状态边界：本收据不推进任何状态——`lifecycle=Needs Fix`、`review_status=Needs Fix`、`ua_status=Failed`、`acceptance_authority=None`、`Uncommitted/Unmerged`；4 个 P1 是否关闭由下一轮独立 Review 判定，实施者不自批。

### UA4 Repair Round 3 实施与验证收据（2026-07-29 13:4x–13:5x UTC+8，Kimi）

- 背景：第二轮独立 Review 确认 `DASHBOARD-FE-UA4-RVW-004-P1-001`（搜索 AND 语义）与 `P1-002`（两主题对比度）可关闭；`P1-003`（长字段 oracle 不足）与 `P1-004`（TASK 事实源冲突）仍阻断。本轮定向修复这两项。
- 修改范围：仅 `dashboard/frontend/**`（untracked，43 个非忽略文件，fresh 实测 `git ls-files --others --exclude-standard dashboard/frontend`）与本 TASK、Board 投影行；backend/contracts/skills 未触碰；无新增依赖、未 `audit fix`、未 commit/merge/push。

#### DASHBOARD-FE-UA4-RVW-004-P1-003（长字段测试 oracle 强化）

- `tests/browser/long-fields.spec.ts` 整体重写：新增 `buildLongFieldStateSnapshot("stale"|"partial")`——在长字段 payload 深拷贝上改 `state` 并克隆 versioned `stale.json`/`partial.json` 的 `stale_sources` 与 SOURCE_STALE/SOURCE_UNAVAILABLE 诊断，全程 `validateContract` 校验；stale/partial 矩阵不再使用 tasks=0 短 fixture。
- 新 oracle：`expectNoClippedText`（元素级 `scrollWidth ≤ clientWidth+1`，覆盖 status-item/pair-button/pair-reasons/search-status/detail-title/def-table td/worktree-line/diag-item/filter-option；`.pair-reasons` 宽度 ≥80px 反逐字竖排）、`expectRegionsDisjoint`（status-bar/app-main/diag-drawer/graph-area/detail-panel 关键区域两两不相交）、`expectNodeIdTruncated`（长 id 节点省略号截断且文本宽 ≤ 节点内宽）。
- 矩阵：3 viewport ×（default→search→filter 展开→detail→drawer，每步全 oracle）+ 长字段 stale/partial × 3 viewport。
- RED/GREEN：强化 oracle 在 Round 2 旧 CSS 上自然抓到 3 例失败（`.pair-reasons` 被压至 73.23px，正是 Reviewer 指出的挤压问题）；正式 RED 实验——临时移除 `.pair-item` 的 `flex-wrap: wrap` + `.pair-reasons` 的 `flex: 1 1 200px` 两项防护后 oracle 失败，恢复后 9/9 绿，证明 oracle 非永真。
- CSS 修复：`.pair-item` 改 `flex-wrap: wrap` + `max-width:100%`，`.pair-reasons` 加 `flex: 1 1 200px`，空间不足时原因文本落整行而非逐字竖排；390 长字段布局可读。

#### DASHBOARD-FE-UA4-RVW-004-P1-004（TASK 事实源冲突）

- 修复：历史「实施证据写回」节的“第三轮 Review Passed / 当前 `review_status=Passed` / UA4 Pending”与“用户 UA4 实机观察未执行”改为明确的时点历史表述，注明已被 UA4 `Failed`（2026-07-29 11:54 UTC+8）与后续 Review `Needs Fix` 取代；Outcome 文件数由 42 更正为 fresh 实测 43 并注明实测命令；「当前 Review 状态」行更新为第二轮 Review 结论（P1-001/P1-002 可关闭，P1-003/P1-004 修复待审）；不含任何“当前可进入 UA4”语义。

#### 验证证据（fresh，真实退出码，无管道掩盖）

- `npm run verify` 退出码 0：codegen:check 同步、typecheck 通过、lint 0 error、Vitest 6 文件 81/81、build 通过、Playwright 7 spec 76/76。
- `npm audit --audit-level=moderate`（只读，未 fix）退出码 1：10 项（3 moderate / 6 high / 1 critical），与基线一致。
- 截图（git-ignored）已逐张目检：重生成 `long-fields/`（matrix-390-default 为关键修复证据——原因栏整行横排、无逐字竖排、无横向滚动；matrix/stale/partial × 1440/1024/390，长字段 stale/partial 含真实 SOURCE_STALE/SOURCE_UNAVAILABLE 诊断）；本人抽查 matrix-390-default 与 stale-390 确认可读。
- 状态边界：本收据不推进任何状态——`lifecycle=Needs Fix`、`review_status=Needs Fix`、`ua_status=Failed`、`acceptance_authority=None`、`Uncommitted/Unmerged`；`P1-003`/`P1-004` 是否关闭由下一轮独立 Review 判定，实施者不自批；非阻断 P2（localStorage 归一化、组合错误序列、非输入控件焦点、dev 依赖 10 项漏洞）继续如实开放。

### UA4 docs-only Repair Round 4 收据（2026-07-29，Kimi）

- 背景：Codex 独立 Review Round 3（冻结 45 files / 43 frontend，digest `37f3b5cc2ae2dfc80a5da5e393efafe4329e8d71506586009b697777fa93507a`）结论 `Needs Fix`，`P0/P1/P2/P3=0/1/4/0`；确认 `DASHBOARD-FE-UA4-RVW-004-P1-001`、`P1-002`、`P1-003` Closed，`P1-004` 保持开放——唯一剩余冲突为本 TASK「验收建议」仍把 Round 1 的 `0/4/1/0` 称为“当前最新 Review”，与 Outcome/Board 的后续结论矛盾。
- 修复（docs-only）：「验收建议」改为唯一当前事实——最新完成的独立 Review 为 Round 3（`Needs Fix`，`0/1/4/0`，仅 `P1-004` 开放），当前仍不允许 UA4，等待本次修复后的新独立 Review；Outcome 与 Board 投影行同步。未触碰 `dashboard/frontend/**`、backend/contracts/skills/其他 TASK；未 commit/merge/push。
- 验证：docs-only——TASK 与 Board targeted `workflow_lint` 均退出 0、`errors/violations/warnings=0/0/1`（唯一 warning 同前）；tracked docs `git diff --check` 0 error；`git status --short` 确认实现文件无漂移（`dashboard/frontend/**` 整体 untracked 未变，docs 仅本 TASK 与 Board 投影行）；代码验证沿用 Round 3 fresh 结果（verify 81/81 + 76/76，本轮无代码变更）。
- 状态边界：`P1-004` 已定向修复但是否关闭由下一轮独立 Review 判定，实施者不自批、不写 Review Passed；保持 `lifecycle=Needs Fix`、`review_status=Needs Fix`、`ua_status=Failed`、`acceptance_authority=None`、`Uncommitted/Unmerged`。

### UA4 修复独立 Review Round 4（2026-07-29，Codex）

- 冻结输入：base/HEAD `fc34f11d7a1079f1ba84d22adaf61d0b973136d4`；43 个 `dashboard/frontend/**` 非忽略新文件 + 本 TASK + Board 投影，共 45 个文件；聚合 digest `42b150d496fdb0d766523b0854adfc3cba661509abde59cd54ca2ae4f0b21206`。审查结束复算一致，Reviewer writes=None。
- 结论：`Passed`，`P0/P1/P2/P3=0/0/4/0`；`DASHBOARD-FE-UA4-RVW-004-P1-001`（搜索 AND 语义）、`P1-002`（两主题对比度）、`P1-003`（长字段裁切/遮挡矩阵）、`P1-004`（单一当前事实源）全部 Closed；允许进入用户重新 UA4。
- Review 边界：本轮为独立只读复审，Reviewer 未修改文件、未运行会写缓存或产物的命令；主控在同一实现上 fresh `npm run verify` 退出码 0（Vitest 81/81、Playwright 76/76、codegen/typecheck/lint/build 全部通过），TASK/Board workflow_lint 均为 `0 error / 0 violation / 1 warning`，tracked/untracked whitespace 检查 0 error。
- 开放 P2：localStorage 偏好类型归一化、组合错误序列保真、部分非输入控件普通更新时的焦点保持、开发依赖链 10 项漏洞；均不阻止本次 UA4，但不得漏报。
- 权限边界：Review Passed 不等于 UA4 Passed、Accepted 或 Closed，不授权 commit、merge、push、release；`acceptance_authority=None`、`Uncommitted/Unmerged` 保持。

<a id="dashboard-fe-001-ua4-2026-07-29"></a>

## DASHBOARD-FE-001 UA4 2026-07-29

- 用户动作：用户在本机 `http://127.0.0.1:5173/` 查看并操作仪表盘，检查了搜索反馈与整体视觉，并进一步确认“完整网络”仅恢复关系图视图、当前仪表盘为只读且不执行任务。
- 验收结果：用户明确回复“好的，验收通过”；记录为 `UA4 Passed / User Confirmed`，据此将 lifecycle 推进为 `Accepted`。
- 验收范围：关系图、搜索与筛选的可观察反馈、视觉舒适度、详情/视图操作及只读产品边界；独立 Review 的四个 P1 已全部 Closed，四个非阻断 P2 继续保留。
- 权限边界：本次用户反馈只构成 UA4 与 Acceptance authority，不授权 commit、stage、merge、push、release、删除 Worktree/分支或 Closed。

## 提交与合并授权 2026-07-29

- 用户授权：用户在 `UA4 Passed / Accepted` 写回和“先提交合并、再进行集成任务”的顺序说明后，明确回复“提交合并”；授权精确提交 `DASHBOARD-FE-001` 并合并到本地 `main`。
- 合并候选：43 个 `dashboard/frontend/**` 新文件 + 本 TASK + Board，共 45 文件；冻结 digest `93534f92bae0501c51da9dbb588f22a6f337e3c8437da75b9af3ff7099cc351e`。
- 门禁证据：完整前端验证 fresh 通过（Vitest 81/81、Playwright 76/76、codegen/typecheck/lint/build 全部通过）；运行时依赖审计 0 漏洞；独立 merge enforcement Review `Passed`，`P0/P1/P2/P3=0/0/4/0`。
- 提交策略：用独立提交保存 `In Progress`、`Review` 两个合法 lifecycle checkpoint，再由本功能提交保存已审查实现树和 `Accepted / Committed / Unmerged` 状态；随后对仍干净的 `main@fc34f11` 执行本地 `--no-ff` merge。
- 权限边界：不包含 push、release、外部同步、删除分支/Worktree、启动 `DASHBOARD-INTEGRATE-001` 或 Closed。

## 分支提交结果 2026-07-29

- 生命周期检查点：`b1ea619` 保存 `In Progress`，`a1e8a60` 保存 `Review / Review Passed`，使 Git 历史可证明 `Ready → In Progress → Review → Accepted` 的合法流转。
- 功能提交：`2ed2bb9`（`feat(dashboard): add accepted relationship frontend`）保存冻结的 45 文件候选和 `Accepted / Committed / Unmerged` 状态。
- 提交后门禁：本 TASK targeted `workflow_lint` 退出码 0，`errors/violations/warnings=0/0/1`；唯一 warning 为 Markdown 无法证明用户身份，不是状态或流转违规。Board targeted lint 退出码 0，`0/0/1`。
- 权限边界：本节只证明分支已提交；本地合并结果将在 `main` 合并后单独记录，不代表 push、release、Closed 或集成任务已启动。

## Outcome


- Base / Diff：base=fc34f11d7a1079f1ba84d22adaf61d0b973136d4;diff=fc34f11..2ed2bb9
- 修改文件：`dashboard/frontend/**`（43 个已提交新文件）、`docs/tasks/DASHBOARD-FE-001.md`、`docs/TASK_BOARD.md` 的 DASHBOARD-FE-001 投影行。
- 验证证据：提交候选上的最新 fresh `npm run verify` 退出码 0（`codegen:check` 同步、`typecheck` 通过、`lint` 0 error、Vitest 6 文件 81/81、production build 通过、Playwright 7 spec 76/76）；`npm audit --omit=dev --audit-level=moderate` 退出码 0、运行时依赖 0 漏洞；完整 audit 仍有 10 项开发依赖链漏洞（3 moderate / 6 high / 1 critical），未执行 `audit fix`；提交后本 TASK 与 Board targeted `workflow_lint` 均退出 0、`errors/violations/warnings=0/0/1`。
- 当前 Review 状态：最新完成的独立 Review 为「UA4 修复独立 Review Round 4」（Codex；冻结 45 files / 43 frontend，digest `42b150d496fdb0d766523b0854adfc3cba661509abde59cd54ca2ae4f0b21206`），结论 `Passed`，`P0/P1/P2/P3=0/0/4/0`；允许进入用户重新 UA4，但不等于 UA4 Passed 或 Accepted。
- Review findings：`DASHBOARD-FE-UA4-RVW-004-P1-001`～`P1-004` 全部 Closed；非阻断 `DASHBOARD-FE-UA4-RVW-004-P2-001`（localStorage 类型归一化）与历史遗留开放 P2（`DASHBOARD-FE-RVW-001-P2-002`、`DASHBOARD-FE-RVW-001-P2-003`、`DASHBOARD-FE-RVW-003-P2-001`）继续如实开放。
- 历史验证证据（均已被上文“验证证据”取代，仅保留审计轨迹）：初实施 62/62 单测、28/28 浏览器（截图 2026-07-29 00:28–00:29 UTC+8）；Repair Round 1 67/67、38/38（约 01:32–01:33 UTC+8）；Repair Round 2 73/73、45/45（01:5x–02:2x UTC+8，主控 02:56–02:58 UTC+8 复跑一致）；UA4 Repair Round 1 81/81、59/59（主控 12:47–12:55 UTC+8 fresh）；UA4 Repair Round 2 81/81、76/76（13:0x–13:2x UTC+8 fresh）；历史第三轮实现 Review `Passed`（冻结输入 `P0/P1/P2/P3=0/0/4/0`）与上述计数同属历史，不再代表当前文件数、验证或 Review 状态。
- UA 动作与结果：用户在本机完成重新 UA4 并明确回复“好的，验收通过”；`UA4 Passed / User Confirmed / Accepted`。
- 隔离位置：Worktree `D:/open-source/ai-dev-flow-wt/dashboard-fe-001`，分支 `codex/dashboard-fe-001`。
- 回滚方式：在未 push 前，可基于提交 `2ed2bb9` 创建反向提交；不使用覆盖历史或直接删除，任何实际回滚需用户另行授权。
- 状态边界：`Accepted`（lifecycle）/ 实现 Review `Passed` / UA4 `Passed` / `User Confirmed` / `Committed` / `Unmerged`；未 merge、未 push、未 release、未交付、未 Closed。
- 剩余风险：开放 P2 为 localStorage 偏好类型归一化（`DASHBOARD-FE-UA4-RVW-004-P2-001`）、组合错误序列可能丢失原始真实错误、部分非输入控件在普通更新时丢失键盘焦点、开发依赖链 10 项已知漏洞；真实后端联调未发生；自动测试不能替代用户对关系图易读性的判断（UA4 不可由自动测试替代）。
- 下一步：按用户已授予的本地合并权限，将 `codex/dashboard-fe-001` 以 `--no-ff` 合并到干净的 `main@fc34f11` 并在合并后的 checkout 复验；不自动 push、release、启动集成任务或 Closed。
