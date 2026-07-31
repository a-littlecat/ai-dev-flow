# DASHBOARD-FE-001-REPAIR-002：增强关系图选中态可见性

> 当前结论（2026-08-01）：`REL-005` 已核验本任务的实现、Review、UA、提交、主线与后继发布证据，任务现为 `Closed`。下文早期“当前状态/下一步/Not Closed”等措辞均是形成时的历史快照，不再代表当前状态；本说明与顶部 Contract 为唯一最新结论，且不改写原 UA 事实。

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `DASHBOARD-FE-001-REPAIR-002`
- `task_type`: `repair`
- `task_class`: `D`
- `lifecycle`: `Closed`
- `review_status`: `Passed`
- `ua_level`: `UA6`
- `ua_status`: `Passed`
- `ua_evidence`: `docs/tasks/DASHBOARD-FE-001-REPAIR-002.md#dashboard-fe-001-repair-002-ua6-2026-07-30`
- `acceptance_authority`: `User Confirmed`
- `commit_status`: `Committed`
- `merge_status`: `Merged`
- `merge_authority`: `User Authorized`
- `close_authority`: `User Authorized`

## Scheduling

- `priority`: `high`
- `parallel_intent`: `serial`
- `worktree_required`: `true`
- `branch_hint`: `codex/dashboard-fe-001-repair-002`
- `depends_on`: `DASHBOARD-FE-001#lifecycle=Accepted;DASHBOARD-FE-001-REPAIR-001#lifecycle=Accepted`
- `replaces`: `none`
- `discovered_from`: `DASHBOARD-INTEGRATE-001`
- `module_locks`: `dashboard-ui`
- `write_scope`: `file:dashboard/frontend/src/styles.css;file:dashboard/frontend/src/state/store.ts;file:dashboard/frontend/src/ui/graph/graphView.ts;file:dashboard/frontend/tests/browser/graph.spec.ts;file:dashboard/frontend/tests/browser/search.spec.ts;file:dashboard/frontend/tests/store.test.ts;file:docs/TASK_BOARD.md;file:docs/tasks/DASHBOARD-FE-001-REPAIR-002.md`

## 目标与边界

- 目标：修复 UA6 真实项目关系图中“选中任务框过淡、在密集连线中难以快速定位”的可视性问题。
- 目标：选中节点在深色和浅色主题中都具有明确的填充、粗描边和非纯颜色提示；与选中任务直接相连的规范关系边保持清晰，无关规范关系边适度退后。
- 目标：搜索命中任务后启用上游/下游聚焦时，搜索命中节点与聚焦链同时保持清晰，结构筛选仍优先约束可见上下文。
- 非目标：不改变布局、缩放、关系方向、调度、并行判断、详情加载或任何只读语义；不重做整体主题。
- 允许修改：`dashboard/frontend/src/styles.css`、`dashboard/frontend/src/state/store.ts`、`dashboard/frontend/src/ui/graph/graphView.ts`、`dashboard/frontend/tests/browser/graph.spec.ts`、`dashboard/frontend/tests/browser/search.spec.ts`、`dashboard/frontend/tests/store.test.ts`、本 TASK 和 `docs/TASK_BOARD.md` 对应投影。
- 禁止修改：`dashboard/contracts/**`、`dashboard/backend/**`、`dashboard/integration/**`、其他前端文件、依赖/锁文件、已 Accepted TASK 事实、发布或本机 Skill。

## 依赖与授权

- 前置依赖：`DASHBOARD-FE-001` 与 `DASHBOARD-FE-001-REPAIR-001` 已 Accepted、Committed、Merged；缺陷来自 `DASHBOARD-INTEGRATE-001` 的真实项目 UA6。
- Base commit：`main@9fe4c4453af1525a6a47adc856575a70c8437911`。
- 已有 authority：用户于 2026-07-29 提供真实截图并要求把过淡的选中框改得更容易看到；允许创建独立 repair Worktree、在精确 allowlist 内实施、运行自动/真实浏览器验证并执行独立只读 Review。
- 未授权动作：commit、merge、push、release、外部同步、删除分支/Worktree、Accepted 和 Closed。
- 执行位置：`D:\open-source\ai-dev-flow-wt\dashboard-fe-001-repair-002`，分支 `codex/dashboard-fe-001-repair-002`。

## 路由与风险

- 路由：`Controlled`。
- Policy 输入：`task_class=D`、`ua_level=UA6`、风险包含 `real_environment`、`shared_component`、`tests_do_not_cover_oracle`，需要用户观察真实密集关系图。
- Reviewer 闸门：`Required`；在新的 UA6 邀请前执行隔离、只读 Review。
- 主要风险：只增强边框仍不足以穿透密集连线；过度压暗无关网络会丢失全局上下文；CSS 选择器可能破坏搜索/聚焦已有 dimming 语义。
- 停止条件：需要改变合同/后端/布局算法/依赖；出现移动端溢出、键盘回归、浅色主题不可读或范围外修改。

## 完成标准与验证

- 完成标准：选中节点及其直接规范关系在深浅主题和三档视口中可被快速识别；自动验证通过，独立只读 Review 无开放 P0/P1，并返回用户进行新的 UA6。
- 验证命令或检查：定向 Playwright RED→GREEN、`npm run verify`、三档真实项目数据浏览器检查、workflow lint、`git diff --check`、allowlist manifest 与独立只读 Review。
- [x] 选中节点在深色/浅色主题均有清晰填充、至少 3px 描边和加粗的 `已选中` 文字标记，不仅依赖颜色。
- [x] 选中任务的直接规范关系边带明确 selected-context class；非直接规范关系边适度退后，但关系类型、线型和箭头语义不变。
- [x] 浏览器回归覆盖选中/取消、搜索、聚焦、键盘、详情与既有关系语义。
- [x] 真实浏览器在 `1440×900`、`1024×768`、`390×844` 检查无文字重叠、裁切和横向溢出，并保留截图证据。
- [x] 前端 `npm run verify` 通过，集成层相关自动验证按风险重跑。
- [x] 独立、只读 Review 无开放 P0/P1。
- [x] `git diff --check` 通过，diff 只归属当前 TASK allowlist。

## Repair Chain Ledger

- Finding：`DASHBOARD-UA6-VISIBILITY-P1-001`；真实项目 UA6 中选中节点只有 2px 低对比度描边，正文和背景层级未变化，在 22 个任务及 231 组并行关系下难以辨认，阻断当前 UA6。
- Repair chain：`repair_chain_id=DASHBOARD-FE-SELECTION-VISIBILITY-RC-001`；`finding_ids=[DASHBOARD-UA6-VISIBILITY-P1-001]`；`closure_contract_hash=9e9b276a382f8d6a9b6d50986c18a8037d05b934ed4170fcbb330e243ad9efe1`；`allowed_files_hash=ef2230d2228bfa8c3c6bb639827f991c372ff8120ee8f70bb0d2d39254438c48`。
- Trigger evidence：用户提供的当前 Dashboard 截图；代码定位为 `.node-selected .node-frame` 仅改变 `stroke` 与 `stroke-width: 2`，未增强填充、文字或关联边层级。
- Attempt 收据链：`AR-1` session `019fae52-ebb3-7532-b15e-fac0d463f617` / receipt SHA256 `5fc29909ef85b4153adfd3e60031f5c53b72b8d96f0ab12036aa9fa8dcc31df5` 为 `Needs Fix`，开放 `DASHBOARD-RVW-P1-001` 与 `DASHBOARD-RVW-P1-002`；`AR-2` session `019fae65-1423-7451-b102-467a590f9eda` / receipt SHA256 `d1e334d58ab736da792c979a41af4c7cb04fd88b17334bd0ca675d3dd0b66daf` 确认前两项 Closed，但开放 `DASHBOARD-RVW-P1-003`、`DASHBOARD-RVW-P1-004` 与 `DASHBOARD-RVW-P2-001`；`AR-3` session `019fae71-3921-7ba0-b749-cdb5d49a976f` / receipt SHA256 `eb11a96978c0935154715d0eccebde52026b7793521ac8073e4020e7d0f9b172` 为 `Passed`，P0/P1/P2/P3=`0/0/0/0`，全部既往 finding Closed。
- History anchor：`attempt_count=3`；`head_receipt_hash=eb11a96978c0935154715d0eccebde52026b7793521ac8073e4020e7d0f9b172`；source 为当前 TASK。
- Trusted context：当前用户消息、截图、`main@9fe4c44` 只读代码与独立 Worktree 状态。
- 机械判定：基础 `AutoRepair` 两轮已用完；AR-2 虽关闭两个旧 P1，但补丁引入新的 selection × focus 阻断项，因此不声称满足 `ExtendRound3` 的“无 patch 新增阻断 finding”条件。
- Orchestrator 提升：用户此前明确“授权你继续，直至可验收为止”，且当前修复仍在同一 UA6 可见性合同、五文件 allowlist 和无外部副作用边界内；据此使用 scope-bound `RepairCampaignAuthority / AR-3`。`meaningful_progress=true`、`consecutive_no_progress=0/4`；AR-3 已 Passed，自主 repair loop 结束。
- 新 Finding：`DASHBOARD-UA6-FOCUS-VISIBILITY-P1-001`；搜索唯一命中任务后点击“聚焦上游/下游”，状态条虽切换成功，但搜索优先级使聚焦链继续保持 `node-dimmed`，真实用户无法观察聚焦结果。
- 新 Repair chain：`repair_chain_id=DASHBOARD-FE-SEARCH-FOCUS-VISIBILITY-RC-001`；`finding_ids=[DASHBOARD-UA6-FOCUS-VISIBILITY-P1-001]`；`closure_contract_hash=064a94f178952bdf628d3dbbcbb226e6d7f8caa90f1d6afd79b2f489d0a941b3`；`allowed_files_hash=6e2e171d850ef57b3f9a972f2edfddae936910d36490b433a1e77b300bdf3b06`。冻结关闭标准为“搜索命中节点与聚焦链取并集点亮、结构筛选仍约束可见上下文、搜索改变选择时清除旧 focus、主动选中节点及直接关系不继承 dimming、上游与下游组合测试均 GREEN、真实 22 任务页面可观察”；closure canonical 为 `search-match-and-focus-union|structural-filters-win|stale-focus-cleared-on-selection-change|selected-node-and-direct-edges-never-dimmed|upstream-downstream-browser-green|real-22-task-page-observable`。8 文件 canonical allowlist 为 6 个前端实现/测试文件、本 TASK 和 `docs/TASK_BOARD.md`；Hash 输入均为 UTF-8/LF、无尾随换行，allowed files 额外按路径升序连接。
- 新链 Review 1：Codex 原生 `review --uncommitted`，session `019faeaa-1494-7e62-b329-33c1e8df0006`，`Needs Fix`；开放 `DASHBOARD-FOCUS-RVW-P1-001`（旧完成清单误报）与 `DASHBOARD-FOCUS-RVW-P2-001`（搜索切换后保留过期焦点链）。
- 新链 Review 2：Codex 原生 `review --uncommitted`，session `019faeb1-fe05-73b3-8f41-8519fbe28706`，`Needs Fix`；确认 Review 1 两项关闭，开放 `DASHBOARD-FOCUS-RVW2-P1-001/-002`（验证证据与 chain 范围绑定记录）以及 `DASHBOARD-FOCUS-RVW2-P2-001/-002`（主动选中节点仍继承 dimming、回滚清单过期）。
- 新链 Review 3：Codex 原生 `review --uncommitted`，session `019faebc-7a40-7962-ab40-ed4729759958`，`Needs Fix`；未发现新的实现或测试问题，开放 `DASHBOARD-FOCUS-RVW3-P1-001/-002`（生命周期仍为 Ready、机器可读 write_scope 未包含两项治理文件）。
- 新链 Review 4：Codex 原生 `review --uncommitted`，session `019faec2-0d35-7b42-a181-ddfc524b0bbb`，`Needs Fix`；仅开放 `DASHBOARD-FOCUS-RVW4-P1-001`（allowed-files hash 错含末尾 LF），实现与测试无新增 finding。
- 新链 Review 5：Codex 原生 `review --uncommitted`，session `019faec9-d504-76d0-81f6-07e75b39bf71`，`Passed`；未发现明确、可操作的功能缺陷，P0/P1/P2/P3=`0/0/0/0`。审查沙箱因禁止 esbuild 创建子进程未能独立复跑单元测试；Orchestrator 已在同一最终代码状态下完成 fresh `npm run verify` 全量验证。
- 新链状态：根因、依赖、权限、关闭合同和 8 文件范围已冻结；无依赖、公共接口、后端、数据或外部副作用变更；Review 1 至 Review 4 的全部 finding 已关闭，Review 5 `Passed`，自主 repair loop 结束。

## DASHBOARD-FE-001-REPAIR-002 UA6 2026-07-30

- 验收环境：用户在本机真实项目页面检查 `DASHBOARD-BE-002` 的搜索、选中态及“聚焦上游/聚焦下游”效果。
- 验收结果：用户明确回复“验收通过”；`UA6 Passed / User Confirmed / Accepted`。
- 权限边界：本次确认只授权验收状态写回，不自动授权 commit、merge、push、release、外部同步或 Closed。

## 提交与合并结果 2026-07-30

- 功能提交：`048c5139c2fe1ec738e5ee4f933f029d397906f9`（`fix(dashboard): clarify selection focus visibility`）。
- 合并提交：`acd0dddac8b56559b2b65c9a86e83e93f8f11cdb`（本地 `main`，`--no-ff`；父提交为 `9fe4c4453af1525a6a47adc856575a70c8437911` 与 `048c5139c2fe1ec738e5ee4f933f029d397906f9`）。
- 合并检出验证：`npm run verify` 已运行并通过；codegen、typecheck、ESLint、production build 均通过，Vitest `82/82`、Chrome Playwright `83/83`。
- 权限边界：用户明确授权“提交并合并”；本次不包含 push、release、外部同步、删除 Worktree/分支或 Closed。

## Outcome

- Base / Diff：base=9fe4c4453af1525a6a47adc856575a70c8437911;diff=048c5139c2fe1ec738e5ee4f933f029d397906f9
- 隔离位置：独立 Worktree `D:\open-source\ai-dev-flow-wt\dashboard-fe-001-repair-002`，分支 `codex/dashboard-fe-001-repair-002`。
- 回滚方式：当前未提交；仅逆向应用本 TASK 的 8 文件工作区 diff（6 个前端文件、本 TASK、`docs/TASK_BOARD.md`），不影响 main、集成 Worktree 或其他已 Accepted artifact。
- 修改文件：`styles.css` 增加深浅主题 selected surface/glow、3px 选中框、选中文字和直接/无关关系边层级；`graphView.ts` 组合搜索与 focus 语义，并保证主动选中节点及直接关系不继承 dimming；`store.ts` 在选择锚点变化时清除旧 focus；`graph.spec.ts`、`search.spec.ts`、`store.test.ts` 覆盖选中态、搜索 × 上下游、结构筛选和过期 focus；本 TASK 与看板记录受控状态。
- 验证证据：旧选中态链的 AR-1/AR-2/AR-3 证据保持不变；新 search × focus 链最终补丁完成后 fresh `npm run verify` exit `0`：codegen in sync、typecheck、ESLint、Vitest `82/82`、production build、Chrome Playwright `83/83`；包含搜索 × 上游、搜索 × 下游、结构筛选优先、搜索切换清除旧 focus、主动选择覆盖 dimming。
- 真实项目视觉证据：从 `DASHBOARD-INTEGRATE-001` Worktree 的真实只读快照加载 22 个任务；深色主题选择 `DASHBOARD-BE-002` 后，selected tag=`✓ 已选中`、描边=`3.4px`（搜索匹配叠加态）、直接规范关系边 `12`、退后规范关系边 `38`；`1440×900`、`1024×768`、`390×844` 均无页面横向溢出，390 宽度“定位”后节点完整可见；浏览器 error log=`0`。
- Review findings：旧选中态 AR-3 Review `Passed`；新链 Review 1 至 Review 4 的 finding 均已关闭，最终 Review 5 `Passed`、P0/P1/P2/P3=`0/0/0/0`。五次新链审查环境均为 `approval=never / sandbox=read-only`，Workspace writes=`None`；Review 5 的测试复跑受只读沙箱进程限制，但 Orchestrator 的最终代码全量验证已通过。
- UA 动作与结果：用户于 2026-07-30 在真实项目页面完成检查并明确回复“验收通过”；`UA6 Passed / Accepted`。
- 合并目标与事实证据：本地 `main`；feature=`048c5139c2fe1ec738e5ee4f933f029d397906f9`；merge=`acd0dddac8b56559b2b65c9a86e83e93f8f11cdb`；`--no-ff` 两父提交已核对。
- 状态边界：`Accepted / Review Passed / UA6 Passed / User Confirmed / Committed / Merged local main / Not Pushed / Not Released / Not Closed`。
- 剩余风险：完整网络视图仍然是高密度总览；本任务只修复选中态定位，不重构关系图信息架构。`npm ci` 报告的依赖审计项来自既有锁文件，本 TASK 未新增、升级或修改依赖。
- 下一步：push、release、外部同步、删除 Worktree/分支与 Closed 均需用户另行授权。
