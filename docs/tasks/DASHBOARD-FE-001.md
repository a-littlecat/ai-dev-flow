# DASHBOARD-FE-001：实现关系图优先的本地任务仪表盘前端

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `DASHBOARD-FE-001`
- `task_type`: `code`
- `task_class`: `C`
- `lifecycle`: `Ready`
- `review_status`: `Passed`
- `ua_level`: `UA4`
- `ua_status`: `Pending`
- `acceptance_authority`: `None`
- `close_authority`: `None`
- `commit_status`: `Uncommitted`
- `merge_status`: `Unmerged`
- `merge_authority`: `None`

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
- Base commit：规划基线为 `fb16bc50f02023aad4a51acd8bf495231fe65f63`；实际实施必须基于共享 contract Accepted commit 重新冻结。
- 已有 authority：允许本 TASK 实施合同的独立 Review、有限 repair、Ready 写回与规划提交。
- 未授权动作：前端实现、依赖安装、启动开发服务器、Worktree/分支创建、commit、merge、push、release、外部同步和 Closed。
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
- [ ] build、typecheck、lint、组件测试和浏览器测试全部有 fresh 结果。
- [ ] schema/fixtures strict validation 通过，无前端私有状态机或未记录 API 字段。
- [ ] 1366/1920/2560、键盘、对比度、非颜色表达和 reduced motion 检查完成。
- [ ] 固定 pair fixture 验证完整条件唯一得到 candidate；缺任一前置条件或 Worktree 得到 unknown；contracts 写入、scope/lock 重叠得到 must_serial。
- [ ] `git diff --check` 通过，diff 只归属当前 TASK。

## 验收建议

- 用户动作等级：UA4（用户在本机打开页面，观察完整关系图、筛选、详情、异常状态和响应式效果）。
- 是否需要用户实机测试：是；但只需运行本地页面，不涉及外部真实业务环境。
- 用户需要做什么：打开包含真实任务的本地仪表盘，检查关系是否易读、下一动作是否醒目、并行/串行是否不会误导。
- 不验收的风险：自动测试可证明结构正确，但不能代替用户判断关系图是否直观好用。
- 是否允许关闭任务：否；当前只是 Ready，尚未实施或验收。

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

## Outcome

- Base / Diff：`base=fb16bc50f02023aad4a51acd8bf495231fe65f63`；当前仅新增任务文档，implementation diff 尚不存在。
- 修改文件：`docs/tasks/DASHBOARD-FE-001.md` 和 TASK_BOARD 投影；前端文件尚未创建。
- 验证证据：任务文档 targeted lint 为 `errors/violations/warnings=0/0/1`，唯一 warning 是文件尚未形成 Git transition history；Scheduling 为 13/13 字段、引用均存在；TASK_BOARD 无 drift/missing/orphan/parse；链接、范围、whitespace 与敏感值检查通过。
- Review findings：最终独立 Review `Passed`；`DASHBOARD-TASKS-P1-001` Closed，无开放 finding。
- UA 动作与结果：UA4 Pending；用户尚未运行本地页面。
- 隔离位置：待 execution authority 且共享 contract baseline 可引用后创建独立 Worktree。
- 回滚方式：未实施；当前仅可删除本次新建 Draft 文档，但删除仍需用户明确授权。
- 状态边界：Ready / Review Passed / UA4 Pending / Uncommitted / Unmerged；未实施、未 Accepted、未交付、未 Closed。
- 剩余风险：技术栈和依赖尚由 Kimi 待选；任何大型依赖仍需用户确认。
- 下一步：等待 `DASHBOARD-BE-001` Accepted，并由用户另行授权 execution；本轮不得创建 Worktree 或执行代码。
