# DASHBOARD-001：规划本地任务关系仪表盘与只读调度后端

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `DASHBOARD-001`
- `task_type`: `plan`
- `task_class`: `C`
- `lifecycle`: `Accepted`
- `review_status`: `Passed`
- `ua_level`: `UA2`
- `ua_status`: `Passed`
- `ua_evidence`: `#dashboard-001-ua2-2026-07-28`
- `acceptance_authority`: `User Confirmed`
- `close_authority`: `None`
- `commit_status`: `Committed`
- `merge_status`: `Unmerged`
- `merge_authority`: `None`

## 需求来源与已确认偏好

- 使用场景：仅在用户本机使用，不建设公网服务、团队 SaaS 或移动端主流程。
- 首要目标：打开页面后优先观察完整任务关系，而不是先看 Kanban 状态列。
- 视觉参考：用户没有指定参考产品或既有品牌风格。
- 前端职责：本 TASK 只冻结总体产品要求、风格建议、必须呈现的信息和前后端合同；具体布局、组件、动效和视觉实现由 Kimi 负责。
- 后端职责：必须把事实源、关系数据、下一动作判定、并行候选判定、Git/Worktree 证据、只读 API、实时刷新、安全和验证写成可实施合同。
- 当前仓库没有前端代码、`PRODUCT.md` 或 `DESIGN.md`；本任务不擅自新增这些文件，也不把尚未实现的视觉方案写成既有设计系统。

## 目标与边界

- 目标：定义一个本地、只读、关系图优先的任务仪表盘，使用户能看见完整任务网络、下一动作、并行候选、强制串行关系、阻塞原因、任务替代/拆分历史和真实 Git/Worktree 状态。
- 目标：复用现有 `WorkflowContract.inspect(project_root)` 及其 `ReaderReport`、diagnostics、projections，不在仪表盘后端复制第二套 TASK 状态解析器。
- 目标：定义稳定的 Scheduling Profile、只读快照模型和本地 HTTP/SSE 合同，让 Kimi 可以只依赖 API 完成前端实现。
- 目标：任何建议均带原因、证据和 provenance；未知信息保持 `unknown`，不得猜测为可执行或可并行。
- 非目标：本任务不实现前端、后端、文件监听、HTTP 服务、关系图、测试代码或打包脚本。
- 非目标：不让浏览器成为 TASK、Review、UA、Git 或权限的事实源。
- 非目标：不自动创建/修改 TASK，不自动启动 agent、Worktree、Review、repair、merge、push、release 或 Closed。
- 非目标：不建设数据库、远程 API、云同步、用户系统、遥测、模型 Adapter 或通用任务执行调度器。
- 允许修改：`docs/tasks/DASHBOARD-001-local-task-relationship-dashboard.md`、`docs/TASK_BOARD.md`。
- 禁止修改：`skills/ai-dev-flow/**`、现有代码/测试、版本、依赖、发布文件、本机 Skill 副本和其他既有 TASK。

## 依赖与授权

- 前置依赖：规划本身无功能前置；以 `main@fb16bc50f02023aad4a51acd8bf495231fe65f63` 为事实基线。
- Base commit：`fb16bc50f02023aad4a51acd8bf495231fe65f63`
- 已有 authority：用户明确授权创建本任务；前端只写总体产品要求和风格推荐，具体实施交给 Kimi；后端方案写清楚。用户于 2026-07-28 在最终 Review Passed 后回复“确认，并创建文档”，据此记录 UA2 Passed，并授权创建本节列明的四份后续实施 TASK 文档。用户随后明确要求审核四份 TASK、有限修复直至可执行，并在新对话执行和审核 `DASHBOARD-BE-001` 至可验收；又明确授权提交规划文件。
- Repair authority：用户于 2026-07-28 在收到 `P0/P1/P2/P3=0/5/1/0` 审查结论和“Kimi 只读”歧义说明后明确回复“授权”；该授权仅绑定 `DASHBOARD-001-P1-001`～`005`、`DASHBOARD-001-P2-006` 和前端运行时措辞修订。
- 当前新增授权：本轮可修改并独立复审本 TASK、四份实施 TASK 与 TASK_BOARD，可精确提交这六份规划文件；复审通过并形成 Git baseline 后，可在新对话为 `DASHBOARD-BE-001` 创建独立 Worktree/分支并实施、验证、Review/repair 到 `Review Passed / UA3 Pending`。
- 未授权动作：执行 `DASHBOARD-BE-002`、`DASHBOARD-FE-001` 或 `DASHBOARD-INTEGRATE-001`，增加未经确认的依赖，替代用户 UA3，merge、push、release、外部同步、删除、历史改写和 `Closed`。
- 执行位置：当前 `main` 仅处理并提交六份规划文件；`DASHBOARD-BE-001` 代码必须在新对话和该 TASK 冻结的独立 Worktree 中实施。
- 前端交接边界：Kimi 可以决定具体前端技术栈和视觉实现；改变本任务的 API、状态语义、权限边界或事实源需要先回到本 TASK 重新 Review / UA。

## 路由与风险

- 路由：`Controlled`
- Policy 输入：`task_class=C`；`ua_level=UA2`；请求动作为架构规划；风险标记包含 `architecture`、`public_api`、`shared_component`、`parallel_writers`；当前仅有文档写入 authority；规划内容可静态核对，但未来界面体验需要用户观察。
- Reviewer 闸门：`Required`；架构规划在进入 UA2 或创建实施任务前必须经过当前 Harness 的隔离、只读 Review。
- 主要风险：仪表盘形成第二套状态源；关系或并行推断过度；把候选建议误报为权限；前后端各自复制状态机；文件变化产生半更新快照；本地 HTTP 暴露到非本机网络。
- 停止条件：需要改变 `adf/v0.7.0` 核心字段或生命周期；需要数据库/云服务才能工作；需要自动写回 TASK；需要自动启动并行 agent；缺少 provenance 仍想给出确定结论；前端实现要求反向改变已冻结后端语义。

## 产品定位

### 核心用户与任务

- 核心用户：在本地使用 `ai-dev-flow` 管理多个 TASK、分支和 Worktree 的单人开发者。
- 核心任务：观察完整任务关系，快速识别当前主路径、可以同时准备的工作、阻塞点、需要用户决定的节点以及需求重构造成的替代关系。
- 使用频率：开发过程中反复打开并长期停留，属于工具型产品，不是展示型落地页。
- 设备范围：桌面端优先；首版至少覆盖常见 1366px 到 2560px 宽度。移动端仅保证能看到错误说明和基本任务列表，不要求完整关系图编辑体验。

### 必须回答的问题

首页在不打开单个 TASK 的情况下，必须能回答：

1. 当前完整任务网络是什么，主要串行链和汇合点在哪里？
2. 哪些节点是当前可采取的下一动作，动作类型是什么？
3. 哪些任务只是“并行候选”，哪些已具备独立 Worktree/分支证据？
4. 哪些任务必须串行，原因是依赖、共享文件、模块锁、风险、UA、真实环境还是权限？
5. 哪些任务被拆分、替代、取消或由新问题派生？
6. TASK、TASK_BOARD、Git/Worktree 或 Scheduling Profile 是否存在冲突、缺失或过期？

## 前端总体要求与风格推荐

### 产品布局要求

- 采用“关系图优先的桌面工作台”，完整任务关系图是主视觉区域，不以 Kanban 卡片列作为默认首页。
- 页面需要持续可见的全局状态区：项目根、Git 分支/HEAD、快照时间、fresh/stale/partial 状态、错误/违规/警告计数。
- 关系图旁必须有可收起的任务详情区域，用于展示状态轴、依赖条件、阻塞原因、Review/UA/delivery 边界、Git/Worktree 和 provenance。
- “下一动作”“并行候选”“需要决定”应是图上的筛选/高亮入口，而不是与关系图竞争的大型卡片首页。
- 用户必须能按 lifecycle、动作类型、风险、任务等级、模块、Worktree、关系类型和诊断严重度筛选。
- 关系图必须支持缩放、平移、适配视图、定位当前节点、聚焦上游/下游和恢复完整网络。
- `depends_on`、`conflicts_with`、`replaces`、`discovered_from` 等边必须有不同线型或符号；不能仅依赖颜色区分。
- 具体三栏、双栏、浮动详情、工具栏位置和组件拆分由 Kimi 决定，只要满足上述信息结果与可访问性要求。

### 风格建议

- 品牌性格：冷静、可靠、精确。
- 视觉策略：克制的中性色作为大面积背景，单一主强调色用于当前聚焦和可操作入口；危险、阻塞、未知分别使用稳定语义色，并同时配合图标/文字。
- 信息密度：允许中高密度，但通过字号、字重、留白、线型和分组建立层级；不把所有信息放进等尺寸卡片。
- 避免风格：暗黑赛博霓虹、装饰性玻璃拟态、渐变文字、超大圆角、重阴影、满屏发光、无限嵌套卡片和传统 Jira 式密集字段表。
- 主题：建议跟随系统并同时支持明暗主题；若首版只能完成一个主题，优先选择高对比、低炫光、适合长时间桌面阅读的中性浅色主题。
- 动效：只用于关系图聚焦、筛选结果和快照刷新；不得让节点持续漂浮或闪烁。必须支持 `prefers-reduced-motion`。
- 可访问性：以 WCAG 2.2 AA 为最低目标；正文对比度不低于 4.5:1；键盘可完成筛选、节点切换和详情查看；状态不能只靠颜色表达。

### 前端运行时与 Kimi 交付边界

- Kimi 自主决定具体框架、组件库、图布局算法、视觉 tokens、字体、间距、图标、动效和响应式实现。
- Kimi 可以调整布局，但不得隐藏或合并 Review、UA、Accepted、commit、merge、release、Closed 等正交状态。
- “只读”限制的是产品运行时，不是限制 Kimi 的开发角色：Kimi 执行后端实施 TASK 时，可以在该 TASK 的 allowlist 内修改后端代码和测试；交付出的后端服务仍只能读取项目 TASK / Git / Worktree，不得修改它们。
- Kimi 执行前端实施 TASK 时，前端运行时只能消费后端只读 API，不直接读取或修改 TASK 文件，不调用 Git 命令，不自行推断 authority。
- 同一个 Kimi 可以分会话串行完成后端与前端任务；若使用多个隔离会话并行，必须先冻结并验收 API schema / fixtures，各会话使用独立 Worktree，最终通过集成任务汇合。
- Kimi 必须覆盖 loading、empty、fresh、stale、partial、parse error、dependency cycle、unknown parallelism 和 API disconnected 状态。
- 前端实现完成后需要浏览器级视觉检查、键盘操作检查、常见桌面宽度检查和用户 UA；这些属于未来前端实施任务，不属于本规划任务的已验证结果。

## 后端总体架构

```text
docs/tasks/*.md + docs/TASK_BOARD.md + Git/Worktrees
                         |
                         v
       Existing WorkflowContract.inspect(project_root)
                         |
                         v
              Scheduling Profile Adapter
                         |
              +----------+-----------+
              |                      |
              v                      v
        Relationship Engine    Git/Worktree Snapshot
              |                      |
              +----------+-----------+
                         v
              Immutable DashboardSnapshot
                         |
              Local Read-only HTTP + SSE
                         |
                         v
                    Kimi Frontend
```

### 模块责任

| 模块 | 责任 | 明确禁止 |
|---|---|---|
| Contract Gateway | 调用公开的 `WorkflowContract.inspect(project_root)`，取得 contracts、diagnostics 和 board projections | 不复制 `_workflow_contract.py` 的状态解析逻辑，不从 TASK_BOARD 反向覆盖 TASK |
| Scheduling Profile Adapter | 从 TASK 正文读取可选调度字段，规范化关系、范围和执行隔离信息 | 不修改 `adf/v0.7.0` Core 字段，不批量迁移旧 TASK，不对缺失字段猜值 |
| Relationship Engine | 构建任务节点、依赖边、替代/派生/冲突关系、下一动作和并行候选 | 不产生执行 authority，不启动任务，不把建议写回 TASK |
| Git/Worktree Snapshot | 只读收集 root、HEAD、branch、worktree、dirty、任务分支映射和命令诊断 | 不 checkout、stash、commit、merge、删除或清理 |
| Snapshot Coordinator | 原子构建不可变快照，管理 revision、fresh/stale/partial 和 last-known-good | 不向前端暴露半更新数据，不因单文件错误静默删除任务 |
| Local API Server | 仅向本机前端提供 JSON/SSE、健康状态和静态资源 | 不提供写接口，不绑定公网地址，不开放 CORS |

## 数据来源与真相优先级

1. TASK 文件：任务边界、Workflow Contract、调度关系和证据的细粒度事实源。
2. Git/Worktree：分支、HEAD、dirty 和执行隔离的运行时事实。
3. TASK_BOARD：只读索引/投影，只用于 drift 诊断，不产生 TASK 状态。
4. DashboardSnapshot：派生缓存，不是持久事实源，进程退出后可以完全重建。
5. 浏览器状态：仅保存筛选、视口和展开偏好，不保存任务状态或 authority。

发生冲突时必须输出 diagnostics 和 provenance；不得按“看起来更新”静默选边。

## Scheduling Profile

### Canonical schema 与读取入口

- Scheduling schema 独立版本固定为 `ai-dev-flow/scheduling/v1`；字段名使用 `scheduling_schema`，不得再次声明 `schema_version`，避免被现有 Workflow Contract Reader 误认成第二个 Core schema。
- 新 TASK 可以增加零个或一个精确 H2 `## Scheduling`。不存在时 profile 为 absent；存在多个、嵌套在其他 H2、包含 H3/表格/代码围栏/注释/裸文本时为 `SCHEDULING_PARSE_ERROR`，整个 profile 无效。
- Adapter 不从 `ReaderReport.sections` 猜测 Scheduling，因为当前 canonical Reader 只为既有 allowlist 提取 section fields。Snapshot Coordinator 先读取冻结的 UTF-8 Markdown bytes 和 SHA256，再分别把文件路径交给 `WorkflowContract.inspect`、把同一份冻结文本交给 Scheduling Parser；任一文件在候选快照发布前 digest 改变，整次候选作废并重建。
- Scheduling Parser 只解析 `## Scheduling` 到下一个 H2 之间的内容。允许空行；其他非空行必须完全匹配 ``- `key`: `value` ``，value 非空且不得包含反引号、CR、LF 或控制字符。
- 本节出现时，下表 13 个字段必须各出现一次；字段顺序可任意，未知、缺失或重复 key 均使整个 profile 无效。规范化输出按下表顺序排列。
- 结构错误使整个 profile 的关系、动作和并行输入为 `unknown`；字段值或引用错误只使受影响字段为 `unknown`。两者都保留 TaskNode Core 状态并输出带路径、行号和 raw value 的 diagnostic，不得回退到猜测值。

Canonical 示例：

```markdown
## Scheduling

- `scheduling_schema`: `ai-dev-flow/scheduling/v1`
- `priority`: `high`
- `depends_on`: `CONTRACT-006#lifecycle=Accepted;TASK-X#review_status=Passed`
- `replaces`: `none`
- `discovered_from`: `PLAN-001`
- `parent`: `none`
- `conflicts_with`: `none`
- `parallel_intent`: `consider`
- `write_scope`: `file:docs/tasks/DASHBOARD-001.md;dir:dashboard`
- `module_locks`: `workflow-contract;dashboard-api`
- `worktree`: `required`
- `branch_hint`: `codex/dashboard-001`
- `risk_flags`: `architecture;public_api;shared_component`
```

### 字段 registry 与规范化

| 顺序 | 字段 | 合法值 | 基数与规范化 |
|---|---|---|---|
| 1 | `scheduling_schema` | 仅 `ai-dev-flow/scheduling/v1` | 单值 |
| 2 | `priority` | `high / medium / low / TBD` | 单值，大小写敏感 |
| 3 | `depends_on` | `TASK-ID#axis=expected` | `;` 列表或 `none`；按 target、axis、expected 排序 |
| 4 | `replaces` | TASK ID | `;` 列表或 `none`；去重前若重复即 error，规范化后按 TASK ID 排序 |
| 5 | `discovered_from` | TASK ID | 同上 |
| 6 | `parent` | TASK ID 或 `none` | 单值 |
| 7 | `conflicts_with` | TASK ID | `;` 列表或 `none`；规范化排序 |
| 8 | `parallel_intent` | `serial / consider / unknown` | 单值；只表达评估意图 |
| 9 | `write_scope` | `file:<path>` 或 `dir:<path>` | `;` 列表或 `none`；路径按 Windows 规范化合同处理后排序 |
| 10 | `module_locks` | `[a-z][a-z0-9._-]*` | `;` 列表或 `none`；大小写敏感、规范化排序 |
| 11 | `worktree` | `required / optional / forbidden / unknown` | 单值 |
| 12 | `branch_hint` | `git check-ref-format --branch` 可接受的分支短名或 `none` | 单值；仅作为匹配提示，不作为命令片段 |
| 13 | `risk_flags` | 下方冻结 registry | `;` 列表或 `none`；规范化排序 |

列表统一规则：

- 分隔符只能是 ASCII `;`，token 两侧不得有空白；空 token、重复 token、`none` 与其他 token 混用均为 error。
- TASK ID 使用现有 `[A-Za-z0-9]+(?:[._-][A-Za-z0-9]+)*`，大小写敏感；所有目标必须存在，否则为 dangling-reference error。
- 文本先解码为 UTF-8，标识符和路径执行 Unicode NFC；除 Windows 路径比较外不做 case folding。
- `risk_flags` v1 精确允许：`architecture`、`business_files_gt_3`、`build_or_deploy_config`、`core_execution_path`、`core_writer_path`、`data_migration`、`delivery`、`explicit_independent_review`、`external_sync`、`historical_p1`、`irreversible_action`、`parallel_writers`、`public_api`、`real_environment`、`release`、`security`、`shared_component`、`tests_do_not_cover_oracle`。新增 flag 必须提升 Scheduling schema 版本。

### Legacy inference

- 旧 TASK 不批量改写；缺少 `## Scheduling` 时仍显示节点，Scheduling provenance 为 `absent`。
- v1 只允许从冻结文本中精确识别以下显式 token：`前置依赖`中的完整 `TASK-ID#axis=expected`、`允许修改`中的 `file:`/`dir:` token、`执行位置`中的完整 branch/worktree token。自然语言“完成后”“同模块”“当前分支”等一律不求值。
- legacy token 必须满足 canonical registry 才能产生 `legacy_inferred`；否则输出 warning 并保持相应字段 `unknown`。存在 canonical profile 时不执行 legacy inference，避免双来源覆盖。
- legacy inference 永远不能产生 authority、`candidate` 并行结论或可执行动作；最多构建带 warning 的关系/范围输入。

### Dependency-condition registry

`depends_on` 的当前 TASK 是 dependent（存储边 `source=current task → target=prerequisite`）；拓扑排序和图形箭头使用反向的 `prerequisite → dependent` 邻接，API 同时返回 `storage_direction` 和 `display_direction`，不得由前端猜测。

v1 允许的 axis 和 expected 值精确如下：

| axis | expected 枚举来源与合法值 |
|---|---|
| `lifecycle` | `Draft / Ready / In Progress / Blocked / Review / Needs Fix / Accepted / Closed / Deferred / Cancelled` |
| `review_status` | `Pending / In Review / Passed / Needs Fix / Do Not Merge` |
| `ua_status` | `Not Required / Pending / Passed / Failed / Deferred / TBD` |
| `acceptance_authority` | `None / User Confirmed / Designated Acceptor Confirmed` |
| `commit_status` | `Not Applicable / Uncommitted / Committed` |
| `merge_status` | `Not Applicable / Unmerged / Merged / Deferred` |
| `merge_authority` | `None / User Authorized / Denied` |
| `close_authority` | `None / User Authorized / Rule Authorized / Denied` |

- expected 与当前 `ReaderReport.normalized` 的精确字符串比较；不使用生命周期包含关系，例如 `Closed` 不自动满足 `Accepted`。
- 同一 prerequisite 的不同 axis 条件按 AND 求值；同一 target/axis/value 重复为 error，同一 target/axis 出现不同 expected 为 conflict error。任一条件 missing、invalid、conflicting 或来自有 error 的目标 TASK，聚合依赖结果为 `unknown`，不得判定满足。
- 未注册 axis 一律 `DEPENDENCY_AXIS_UNKNOWN`；不得从 Outcome、TASK_BOARD 或自然语言增加临时 axis。
- 每个条件形成独立边，稳定 ID 为 SHA256(`depends_on\0source\0target\0axis\0expected`)；同一 target 的条件聚合状态另存为 `dependency_group`。
- 反向 `blocks`、`replaced_by` 和 `children` 只由引擎派生，不在多个 TASK 中双写。

## 后端领域模型

### `TaskNode`

- `task_id`、`title`、`source_path`
- `task_type`、`task_class`
- `lifecycle`
- `review_status`
- `ua_level`、`ua_status`、`acceptance_authority`
- `commit_status`、`merge_status`、`merge_authority`、`close_authority`
- `unsupported_axes`：v1 固定包含 `commit_authority / release_status / release_authority / repair_authority`；这些轴不在 `adf/v0.7.0`，必须显式显示为 unsupported，不得从 Outcome 或自然语言补值。
- `priority`、`risk_flags`
- `write_scope`、`module_locks`
- `parallel_intent`、`worktree_requirement`、`branch_hint`
- `diagnostics`、`provenance`
- `freshness`: `fresh / stale / partial`

### `RelationshipEdge`

- `edge_id`：由 type、source、target、condition 形成稳定 SHA256。
- `type`：`depends_on / parent / replaces / discovered_from / conflicts_with`。
- `source_task_id`、`target_task_id`。
- `condition`：`depends_on` 必须使用 `{axis, operator:"eq", expected, actual, evaluation}`；其他关系为 `null`。
- `storage_direction`：`dependent_to_prerequisite`；`display_direction`：`prerequisite_to_dependent`。非依赖边按关系语义填写，不允许前端反推。
- `directional`：除 `conflicts_with` 外均为 `true`。
- `origin`：`canonical / legacy_inferred / derived`。
- `provenance`：路径、heading、line、raw value。

依赖拓扑只使用 `depends_on`。`conflicts_with` 为对称边；替代、派生和层级关系可以参与展示，但不得影响依赖拓扑，除非另有显式 `depends_on`。

### `ActionRecommendation`

- 每个 TASK 返回零到多个 recommendation；`action_id=SHA256(task_id + "\0" + action_kind)`，按下方矩阵顺序稳定排序。
- `task_id`
- `action_kind`：`plan / execute / continue / review / repair / user_decision / commit / merge / release / close / none`
- `eligibility`：`actionable / blocked / needs_authority / unknown / not_applicable`
- `reason_codes`：稳定、可测试的原因码列表。
- `blocking_task_ids`
- `blocking_condition_ids`、`related_diagnostic_ids`：分别保存依赖条件 ID 和 diagnostic ID；不得混入 `reason_codes`。
- `required_authority`：固定枚举 `none / execution / review / repair / commit / merge / release / close / user_decision`。
- `authority_state`：`not_required / present / missing / denied / unsupported / unknown`。
- `evidence` 与 `provenance`

该对象是建议，不是 authority receipt。前端必须显示“建议/候选”措辞；Local API 不提供执行端点。

### `ParallelAssessment`

- `left_task_id`、`right_task_id`
- `result`：`candidate / must_serial / unknown`
- `reason_codes`
- `hard_conflicts`
- `projection_conflicts`
- `worktree_evidence`
- `requires_user_confirmation=true`

`candidate` 只表示机械候选；不能显示为“已允许并行”。

### `DashboardSnapshot`

- 快照 schema：JSON 属性 `schema_version` 固定为 `ai-dev-flow/dashboard-snapshot/v1`。
- `revision`：对规范化输入清单、内容 digest、派生对象、diagnostics 和 Git 快照做 canonical SHA256；不包含 `generated_at`。
- `generated_at`
- `state`: `fresh / stale / partial`
- `project`：root、branch、HEAD、dirty、worktrees。
- `tasks`、`edges`、`actions`、`parallel_assessments`
- `diagnostics`、`stale_sources`
- `summary`：各状态、动作、严重度和关系类型计数。
- `capabilities`：明确 v1 支持/不支持的 axis、action 和 authority source。
- `disclaimer`：明确自动验证、Review、UA、delivery 和 Closed 不能互相推导。

## 下一动作判定

### Authority 事实边界

- v1 唯一 authority 事实源是 `ReaderReport.normalized` 中已有的 `acceptance_authority`、`merge_authority`、`close_authority`。TASK_BOARD、Scheduling、Outcome prose、branch 名和浏览器状态均不能产生 authority。
- `adf/v0.7.0` 没有 execution、review、repair、commit、release authority 字段。v1 对这些动作只能给出“建议动作种类”，其 `eligibility` 必须为 `needs_authority` 或 `unknown`，除非未来版本接入由 Orchestrator 提供并单独验证的 trusted authority receipt；本任务不定义该扩展。
- `release_status / release_authority` 不在 v1 Core。为避免隐藏 release 边界，已合并任务可以返回 `action_kind=release`，但固定为 `eligibility=unknown`、`authority_state=unsupported`、`reason_codes=["RELEASE_AXIS_UNSUPPORTED"]`，绝不能显示为可执行。
- repair chain/authority 同样不由 Scheduling 提供。出现 Needs Fix 时返回 repair 建议，但固定 `needs_authority / repair / unsupported / REPAIR_AUTHORITY_UNSUPPORTED`；是否已有 repair authority 由当前任务执行流程判断，不由本地仪表盘代替。
- commit 没有 canonical authority：Accepted + Uncommitted 固定返回 `commit / needs_authority / commit / unsupported / COMMIT_AUTHORITY_UNSUPPORTED`。

### 状态优先级与动作矩阵

先运行现有 Workflow Contract diagnostics。Core parse error、状态 guard violation 或互相冲突的正交轴存在时，固定只返回：`action_kind=none`、`eligibility=unknown`、`required_authority=none`、`authority_state=unknown`、`reason_codes=["CONTRACT_STATE_INVALID"]`；相关 diagnostic ID 放入 `related_diagnostic_ids`，不得用下表覆盖错误。无上述错误时按顺序求值，前一条命中后停止 workflow action；已合并后的 release/close boundary 可以各返回一条独立 recommendation。

| 顺序 | 当前事实 | action_kind | eligibility | required_authority | authority_state | 唯一 reason_code |
|---|---|---|---|---|---|---|
| 1 | `lifecycle=Closed / Cancelled` | `none` | `not_applicable` | `none` | `not_required` | `TERMINAL_STATE` |
| 2 | `review_status=Needs Fix / Do Not Merge`，或 `lifecycle=Needs Fix` | `repair` | `needs_authority` | `repair` | `unsupported` | `REPAIR_AUTHORITY_UNSUPPORTED` |
| 3 | `lifecycle=Draft` | `plan` | `needs_authority` | `user_decision` | `missing` | `PLANNING_DECISION_REQUIRED` |
| 4 | `lifecycle=Ready` 且任一依赖 unknown | `execute` | `unknown` | `execution` | `unsupported` | `DEPENDENCY_STATE_UNKNOWN` |
| 5 | `lifecycle=Ready` 且任一依赖 unsatisfied | `execute` | `blocked` | `execution` | `unsupported` | `DEPENDENCY_UNSATISFIED` |
| 6 | `lifecycle=Ready` 且全部依赖 satisfied | `execute` | `needs_authority` | `execution` | `unsupported` | `EXECUTION_AUTHORITY_UNSUPPORTED` |
| 7 | `lifecycle=In Progress` | `continue` | `needs_authority` | `execution` | `unsupported` | `CONTINUE_AUTHORITY_UNSUPPORTED` |
| 8 | `lifecycle=Review` 且 `review_status=Pending / In Review` | `review` | `needs_authority` | `review` | `unsupported` | `REVIEW_AUTHORITY_UNSUPPORTED` |
| 9 | `lifecycle=Review`、`review_status=Passed`、`ua_status=Pending / TBD` | `user_decision` | `actionable` | `user_decision` | `not_required` | `USER_DECISION_PENDING` |
| 10 | `lifecycle=Review`、Review Passed、UA Passed/Not Required，但尚未 Accepted | `user_decision` | `actionable` | `user_decision` | `not_required` | `ACCEPTANCE_RECORD_PENDING` |
| 11 | `lifecycle=Accepted` 且 `commit_status=Uncommitted` | `commit` | `needs_authority` | `commit` | `unsupported` | `COMMIT_AUTHORITY_UNSUPPORTED` |
| 12a | Committed + Unmerged/Deferred + `merge_authority=User Authorized` | `merge` | `actionable` | `merge` | `present` | `MERGE_AUTHORITY_PRESENT` |
| 12b | Committed + Unmerged/Deferred + `merge_authority=Denied` | `merge` | `blocked` | `merge` | `denied` | `MERGE_AUTHORITY_DENIED` |
| 12c | Committed + Unmerged/Deferred + `merge_authority=None` | `merge` | `needs_authority` | `merge` | `missing` | `MERGE_AUTHORITY_REQUIRED` |
| 13a | `merge_status=Merged` 且未 Closed | `release` | `unknown` | `release` | `unsupported` | `RELEASE_AXIS_UNSUPPORTED` |
| 13b | Merged + `close_authority=User Authorized / Rule Authorized` | `close` | `actionable` | `close` | `present` | `CLOSE_AUTHORITY_PRESENT` |
| 13c | Merged + `close_authority=Denied` | `close` | `blocked` | `close` | `denied` | `CLOSE_AUTHORITY_DENIED` |
| 13d | Merged + `close_authority=None` | `close` | `needs_authority` | `close` | `missing` | `CLOSE_AUTHORITY_REQUIRED` |
| 14 | 其他合法但矩阵未覆盖组合 | `none` | `unknown` | `none` | `unknown` | `STATE_COMBINATION_UNMAPPED` |

每条 recommendation 的 `reason_codes` 必须只包含上表唯一主 reason，不得追加任意字符串。dependency condition ID 写入 `blocking_condition_ids`，diagnostic ID 写入 `related_diagnostic_ids`。`authority_state` 只能由本表或 canonical merge/close authority 映射产生，不允许实现者自行选择 `missing / unsupported / unknown / not_required`。

`lifecycle=Needs Fix` 和 `review_status=Needs Fix` 是两个独立轴：任一命中都会给 repair 建议；若另一个轴与高阶状态冲突（例如 Accepted + review Needs Fix），现有 validator diagnostic 优先，动作整体为 unknown，不用“repair 优先级”掩盖非法状态。

依赖条件的每个轴必须逐项核对。缺 TASK、值冲突、未知状态或缺 provenance 时，结果为 `unknown`，不能降级为满足。

排序只用于呈现，不授予权限。建议稳定顺序：

1. 已明确授权且正在进行的动作；
2. 高优先级、依赖已满足的动作；
3. 位于更多下游任务上游的阻塞节点；
4. 需要用户决定的节点；
5. 同序时按 `task_id` 排序，保证快照确定性。

没有工期数据时只能显示依赖深度和下游数量，不能把它命名为“按时长计算的关键路径”。

## 依赖与关系校验

- TASK ID 必须唯一；关系目标必须存在，否则输出 dangling-reference error。
- `depends_on` 子图必须无环；使用强连通分量或等价算法报告完整 cycle path。
- 禁止任务直接或间接依赖自身。
- `replaces` 不得指向自身；替代链循环为 error。
- `parent` 只能有一个 canonical 值；多父冲突为 error。
- `conflicts_with` 可单边记录、双向派生；重复边去重但保留全部 provenance。
- 同一关系 canonical 与 inferred 冲突时不产生确定边。
- Cancelled/Closed 节点继续保留在历史图中，不因生命周期结束而删除。

## 并行候选判定

只有全部条件已知且通过时才返回 `candidate`：

- 两个任务之间不存在直接或间接依赖路径。
- 不存在显式 `conflicts_with`。
- `write_scope` 的 exact path 或目录 prefix 不重叠。
- `module_locks` 不重叠。
- 不同时修改公共 API、schema、协议、构建/发布配置、核心执行路径或同一共享组件。
- D 级、高风险架构迁移、真实环境、数据迁移、不可逆动作和 delivery 默认为 `must_serial`。
- 需要 UA5/UA6/UA7 的代码任务默认为 `must_serial`。
- 两个代码任务都有独立分支/Worktree 要求和可核对的执行位置；未知时为 `unknown`。
- 当前工作区存在来源不明的相关 dirty 变更时为 `unknown` 或 `must_serial`。

### Accepted contract consumer exception v1

`BE-001 → (BE-002 ∥ FE-001)` 使用一个窄化且可机器验证的例外，不改变上述默认保守规则。只有两个消费者任务同时满足以下全部条件，D 级、`public_api`、`security`、`shared_component` 或 `core_execution_path` 风险才不会仅凭 flag 直接判为 `must_serial`：

1. 两个任务的 `parallel_intent=consider`，且不存在直接或间接依赖路径、显式冲突、scope overlap 或 module lock overlap。
2. 两个任务具有同一个直接前置合同拥有者；各自 `depends_on` 必须同时包含该前置任务的 `commit_status=Committed`、`lifecycle=Accepted`、`review_status=Passed`、`ua_status=Passed`，缺一项即为 `unknown`。
3. 前置任务的 `write_scope` 明确拥有共享 contract 目录；两个消费者的 `write_scope` 均不得覆盖该目录，并把它列为只读。消费者如需修改 contract，结果立即变为 `must_serial`，停止当前任务并返回前置任务重新 Review。
4. 两个消费者的业务 `write_scope`、`module_locks` 和实际 dirty ownership 均互不重叠；只允许共享 TASK_BOARD 之类的 `projection_conflict`，且投影写回必须串行。
5. 两个消费者均要求独立 branch/Worktree，且 Git 快照能唯一证明 branch、Worktree、HEAD 和 dirty ownership；缺失、歧义或来源不明均为 `unknown`。
6. 任一消费者出现 `data_migration`、`delivery`、`external_sync`、`irreversible_action`、`real_environment` 或 `release`，或任一任务要求 UA5/UA6/UA7，例外失效并固定为 `must_serial`。
7. 满足例外仍只返回 `candidate`、固定 `requires_user_confirmation=true` 和 `reason_code=ALL_CHECKS_PASSED`；它不产生 execution authority。

BE-001 Accepted 合同消费者 fixture 必须唯一验证：完整条件得到 `candidate`；删除任一正交前置条件得到 `unknown`；任一消费者写入 `dashboard/contracts/**`、scope/lock 重叠或出现被排除风险得到 `must_serial`；缺 Worktree、分支映射或 dirty ownership 得到 `unknown`。

冲突分两层展示：

- `hard_conflict`：业务文件、模块、接口、风险或依赖冲突，必须串行。
- `projection_conflict`：仅共享 `docs/TASK_BOARD.md` 等投影文件；业务实现可作为候选并行，但投影写回和集成必须串行。

引擎可以生成候选 Wave 预览，但不得创建 Wave 文件、Worktree 或执行会话。任何候选都固定带 `requires_user_confirmation=true`。

### Windows 路径 canonicalization

`write_scope` 在比较前必须经过以下固定流程；任一步失败都输出 diagnostic，并使涉及该任务的并行结果为 `unknown`，不得返回 `candidate`：

1. 先解析 `file:` / `dir:` 类型；path 必须是非空 repo-relative POSIX 形式，只使用 `/`。拒绝 `\`、盘符、UNC、URI、开头 `/`、NUL/控制字符、空 segment、`.`、`..`、segment 结尾空格或点，以及 Windows 保留设备名。
2. 对 path 执行 Unicode NFC；保留原值用于 provenance，比较键使用每个 segment 的 Unicode `casefold()`。即使某个 NTFS 目录启用了大小写敏感，也使用更保守的 case-insensitive 冲突判断，允许误报串行但不允许漏报冲突。
3. 从 Git 明确返回的 Worktree root 开始逐 segment 检查已有 ancestor。已有 symlink/junction 必须解析最终目标并验证仍位于该 Worktree root；逃逸或无法解析为 error。未存在的尾部只做词法规范化，不调用 shell。
4. canonical key 为 `(kind, segment_tuple)`。`file:a/b` 只与同一文件或覆盖它的 `dir:a` / `dir:a/b` 冲突；`dir:a/b` 与其任意后代及祖先目录冲突。prefix 只能按完整 segment 比较，因此 `dir:src/a` 不匹配 `src/ab`。
5. 两个 scope 内部重复、同一 TASK 同时声明覆盖关系或 file/dir 类型冲突均输出 warning 并去重为最宽的安全范围；不同 TASK 之间任一 overlap 为 `hard_conflict`。

`module_locks` 使用大小写敏感精确匹配；`public_api`、`shared_component`、`build_or_deploy_config`、`core_execution_path` 等风险 flag 任一在两项代码任务中出现时，除非满足上节全部 Accepted contract consumer exception v1 条件，v1 固定为 `must_serial`。

## Git 与 Worktree 只读采集

- 只允许参数数组调用以下固定命令族，不经过 shell：`git -C <root> rev-parse --show-toplevel --git-dir --git-common-dir --verify HEAD`、`git -C <root> worktree list --porcelain -z`、以及对每个列出 Worktree 调用 `git -C <worktree> status --porcelain=v1 -z --untracked-files=all --ignore-submodules=none`。禁止把 TASK 内容拼接成命令。
- 启动时记录 Git version；不支持 `worktree list --porcelain -z` 时标记 `GIT_CAPABILITY_UNSUPPORTED`，保留 TASK 图但 Worktree/并行证据为 `unknown`，不切换到未经测试的文本猜测。
- 每个命令默认 5 秒超时，stdout 按原始 bytes 以 UTF-8 解码；解码、超时、非零退出分别返回稳定错误码。stderr 只保存截断后的本地诊断，不进入 revision 原始输入，不写外部日志。
- `worktree list` 每项冻结 `root / HEAD / branch / detached / locked / prunable`。root 必须是绝对路径、可解析，并来自 Git 输出；`.git` 为文件的 linked Worktree 通过 `--git-dir / --git-common-dir` 找到真实 metadata，watcher 不假设 `.git` 一定是目录。
- `branch_hint` 匹配完整 `refs/heads/<branch_hint>`。零匹配、多匹配、detached、locked/prunable 或 root 无法读取均为 `unknown`；两个代码 TASK 映射到同一 Worktree 时为 `must_serial`。
- status 使用 NUL 分隔解析，包含 tracked、untracked、ignored 之外的所有状态；rename/copy 的旧路径和新路径都进入 dirty set，submodule path 按目录范围处理。非法路径、无法解析的 rename/submodule 或 status 超时使该 Worktree dirty evidence 为 `unknown`。
- dirty ownership 仅在 TASK 的 `branch_hint` 唯一映射到该 Worktree，且每个 dirty path 都完全落在其 canonical `write_scope` 时记为 `owned_by_task`。超出 scope、同时落入另一任务 scope、来自未映射 Worktree或无法归属时为 `unknown`；不得用进程、编辑器或用户名猜 ownership。
- 两个代码 TASK 返回 `candidate` 还要求各自映射到不同 Worktree，相关 dirty 均为 clean 或 `owned_by_task`，且前述依赖、scope、module、risk、UA 条件全部通过。
- Git 不可用、浅历史或某个 Worktree 无法读取时进入降级模式，保留 TASK 图并将相关 Git/并行证据标记为 `unknown`。
- 不执行 `checkout`、`switch`、`stash`、`clean`、`reset`、`commit`、`merge`、`push`、删除或任何写操作。

## 实时刷新与一致性

- 首版使用本地文件轮询或等价只读 watcher，监控 `docs/tasks/*.md`、`docs/TASK_BOARD.md`、`.git` 中与 HEAD/refs/worktree 相关的必要入口。
- watcher 通过 `git rev-parse --git-dir --git-common-dir` 解析主 Worktree 和 linked Worktree metadata；监控入口由 Git 结果生成，不硬编码 `.git` 为目录。
- 保存事件使用 200ms trailing-edge debounce，连续事件最多延迟 1 秒强制构建一次；临时文件不进入输入 manifest。
- 每次刷新先在后台构建完整不可变候选快照；校验结束后一次性替换当前 revision。
- 有 last-known-good 时，解析失败保留上一版可用数据并将 snapshot 标为 `stale`，同时暴露当前错误和 `stale_sources`。
- 首次构建就失败时返回 `partial`，不得伪装为 fresh，也不得静默隐藏失败任务。
- last-known-good 只保存在进程内存；它不是事实源。stale 快照的 revision 同时包含当前失败输入 digest、当前 diagnostics 和被复用对象的 last-good digest，因此错误变化一定产生新 revision。
- `changed_task_ids` 比较前后 TaskNode、相邻 edges、actions 和 pair assessments；任一相关对象变化都包含对应 task ID。首次事件包含全部当前 task IDs。
- SSE 只发送 revision、state 和 changed task IDs；前端收到后重新读取快照，避免在事件流中复制完整状态。
- 默认目标：稳定保存后 1 秒内发出新 revision。性能不足时先记录测量，再决定是否引入增量解析。

## 只读本地 API 合同

### 端点

| 方法与路径 | 返回 |
|---|---|
| `GET /api/v1/snapshot` | 完整 `DashboardSnapshot`，支持 ETag / `If-None-Match` |
| `GET /api/v1/tasks/{task_id}` | 单个 TaskNode、相邻 edges、action、parallel assessments 和 provenance |
| `GET /api/v1/events` | `text/event-stream`，推送 revision/state/changed IDs |
| `GET /api/v1/health` | server、watcher、last refresh、snapshot state 和 diagnostic counts |

### JSON wire schema v1

以下表格是 normative schema；所有 object 均 `additionalProperties=false`，所有字段都必须出现。标记 `T|null` 的字段可以为 JSON `null`；数组永不为 null，无值时为 `[]`。整数不得为负，时间使用 UTC RFC3339 `YYYY-MM-DDTHH:mm:ss.sssZ`。枚举大小写敏感。任何字段删除、改名、类型/枚举收窄或语义改变都必须升级 `/api/v2` 或 snapshot schema；只允许向 v1 object 新增前端明确忽略的可选字段，但首版实现仍按本表禁止额外字段，以便 fixture 严格校验。

Wire enum registry v1：

| 类型 | 精确枚举 |
|---|---|
| `TaskType` | `document / plan / code / review / repair / test` |
| `TaskClass` | `A / B / C / D` |
| `Lifecycle` | `Draft / Ready / In Progress / Blocked / Review / Needs Fix / Accepted / Closed / Deferred / Cancelled` |
| `ReviewStatus` | `Pending / In Review / Passed / Needs Fix / Do Not Merge` |
| `UaLevel` | `UA0 / UA1 / UA2 / UA3 / UA4 / UA5 / UA6 / UA7 / TBD` |
| `UaStatus` | `Not Required / Pending / Passed / Failed / Deferred / TBD` |
| `AcceptanceAuthority` | `None / User Confirmed / Designated Acceptor Confirmed` |
| `CommitStatus` | `Not Applicable / Uncommitted / Committed` |
| `MergeStatus` | `Not Applicable / Unmerged / Merged / Deferred` |
| `MergeAuthority` | `None / User Authorized / Denied` |
| `CloseAuthority` | `None / User Authorized / Rule Authorized / Denied` |
| `DependencyAxis` | `lifecycle / review_status / ua_status / acceptance_authority / commit_status / merge_status / merge_authority / close_authority` |
| `StorageDirection` | `dependent_to_prerequisite / child_to_parent / replacement_to_replaced / discovered_to_origin / symmetric` |
| `DisplayDirection` | `prerequisite_to_dependent / parent_to_child / replaced_to_replacement / origin_to_discovered / symmetric` |
| `ActionKind` | `plan / execute / continue / review / repair / user_decision / commit / merge / release / close / none` |
| `RequiredAuthority` | `none / execution / review / repair / commit / merge / release / close / user_decision` |
| `ActionReasonCode` | `CONTRACT_STATE_INVALID / TERMINAL_STATE / REPAIR_AUTHORITY_UNSUPPORTED / PLANNING_DECISION_REQUIRED / DEPENDENCY_STATE_UNKNOWN / DEPENDENCY_UNSATISFIED / EXECUTION_AUTHORITY_UNSUPPORTED / CONTINUE_AUTHORITY_UNSUPPORTED / REVIEW_AUTHORITY_UNSUPPORTED / USER_DECISION_PENDING / ACCEPTANCE_RECORD_PENDING / COMMIT_AUTHORITY_UNSUPPORTED / MERGE_AUTHORITY_PRESENT / MERGE_AUTHORITY_DENIED / MERGE_AUTHORITY_REQUIRED / RELEASE_AXIS_UNSUPPORTED / CLOSE_AUTHORITY_PRESENT / CLOSE_AUTHORITY_DENIED / CLOSE_AUTHORITY_REQUIRED / STATE_COMBINATION_UNMAPPED` |
| `ParallelReasonCode` | `DEPENDENCY_PATH_PRESENT / EXPLICIT_CONFLICT / WRITE_SCOPE_OVERLAP / MODULE_LOCK_OVERLAP / SHARED_HIGH_RISK_SURFACE / HIGH_RISK_SERIAL / UA_LEVEL_SERIAL / WORKTREE_EVIDENCE_UNKNOWN / WORKTREE_SHARED / DIRTY_OWNERSHIP_UNKNOWN / PROJECTION_ONLY_CONFLICT / ALL_CHECKS_PASSED` |

`RelationshipEdge.type` 唯一映射方向：`depends_on → dependent_to_prerequisite / prerequisite_to_dependent`；`parent → child_to_parent / parent_to_child`；`replaces → replacement_to_replaced / replaced_to_replacement`；`discovered_from → discovered_to_origin / origin_to_discovered`；`conflicts_with → symmetric / symmetric`。其他组合为 schema error。

通用对象：

| 对象 | 必选字段 |
|---|---|
| `Provenance` | `source_path:string`（repo-relative POSIX）、`heading:string|null`、`field:string|null`、`line:int`、`raw_value:string|null`、`source_type:canonical|legacy_inferred|derived|git|default` |
| `Diagnostic` | `diagnostic_id:string`、`code:string`、`severity:error|violation|warning|info`、`message:string`、`task_ids:string[]`、`provenance:Provenance[]` |
| `WorktreeSnapshot` | `root:string`、`head:string|null`、`branch:string|null`、`detached:boolean`、`locked:boolean`、`prunable:boolean`、`dirty_state:clean|dirty|unknown`、`dirty_paths:string[]`、`diagnostic_ids:string[]` |
| `ProjectSnapshot` | `root:string`、`branch:string|null`、`head:string|null`、`dirty:boolean|null`、`git_state:ok|degraded|unavailable`、`worktrees:WorktreeSnapshot[]` |
| `StaleSource` | `source_path:string`、`current_digest:string`、`last_good_digest:string|null`、`diagnostic_ids:string[]` |

领域对象：

| 对象 | 必选字段 |
|---|---|
| `TaskNode` | `task_id:string`、`title:string`、`source_path:string`、`task_type:TaskType|null`、`task_class:TaskClass|null`、`lifecycle:Lifecycle|null`、`review_status:ReviewStatus|null`、`ua_level:UaLevel|null`、`ua_status:UaStatus|null`、`acceptance_authority:AcceptanceAuthority|null`、`commit_status:CommitStatus|null`、`merge_status:MergeStatus|null`、`merge_authority:MergeAuthority|null`、`close_authority:CloseAuthority|null`、`unsupported_axes:string[]`、`scheduling_state:canonical|legacy_inferred|absent|invalid`、`priority:high|medium|low|TBD|null`、`risk_flags:string[]`、`write_scope:string[]`、`module_locks:string[]`、`parallel_intent:serial|consider|unknown|null`、`worktree_requirement:required|optional|forbidden|unknown|null`、`branch_hint:string|null`、`freshness:fresh|stale|partial`、`diagnostic_ids:string[]`、`provenance:Provenance[]` |
| `DependencyCondition` | `axis:DependencyAxis`、`operator:eq`、`expected:AxisValue(axis)`、`actual:AxisValue(axis)|null`、`evaluation:satisfied|unsatisfied|unknown` |
| `RelationshipEdge` | `edge_id:string`、`type:depends_on|parent|replaces|discovered_from|conflicts_with`、`source_task_id:string`、`target_task_id:string`、`condition:DependencyCondition|null`、`storage_direction:StorageDirection`、`display_direction:DisplayDirection`、`directional:boolean`、`origin:canonical|legacy_inferred|derived`、`provenance:Provenance[]` |
| `ActionRecommendation` | `action_id:string`、`task_id:string`、`action_kind:ActionKind`、`eligibility:actionable|blocked|needs_authority|unknown|not_applicable`、`reason_codes:ActionReasonCode[]`、`blocking_task_ids:string[]`、`blocking_condition_ids:string[]`、`related_diagnostic_ids:string[]`、`required_authority:RequiredAuthority`、`authority_state:not_required|present|missing|denied|unsupported|unknown`、`evidence:Provenance[]` |
| `ParallelAssessment` | `assessment_id:string`、`left_task_id:string`、`right_task_id:string`（按 task ID 排序）、`result:candidate|must_serial|unknown`、`reason_codes:ParallelReasonCode[]`、`hard_conflicts:ParallelReasonCode[]`、`projection_conflicts:ParallelReasonCode[]`、`worktree_evidence:WorktreeSnapshot[]`、`requires_user_confirmation:true` |

`DashboardSnapshot` 必选字段：

| 字段 | 类型与规则 |
|---|---|
| `schema_version` | 常量 `ai-dev-flow/dashboard-snapshot/v1` |
| `revision` | 64 位小写 hex SHA256 |
| `generated_at` | UTC RFC3339 |
| `state` | `fresh / stale / partial` |
| `project` | `ProjectSnapshot` |
| `tasks` | `TaskNode[]`，按 `task_id` 排序 |
| `edges` | `RelationshipEdge[]`，按 `edge_id` 排序 |
| `actions` | `ActionRecommendation[]`，按 task ID、动作矩阵顺序、action ID 排序 |
| `parallel_assessments` | `ParallelAssessment[]`，按 left/right 排序 |
| `diagnostics` | `Diagnostic[]`，按 severity、code、path、line、diagnostic ID 排序 |
| `stale_sources` | `StaleSource[]`，按 source_path 排序 |
| `summary` | `{task_total:int, edge_total:int, action_total:int, counts_by_lifecycle:object, counts_by_action:object, counts_by_severity:object, counts_by_relation:object}`；各 map 包含 schema 所有枚举键，缺失计数为 0 |
| `capabilities` | `{supported_scheduling_schema:string[], supported_actions:string[], unsupported_actions:string[], unsupported_axes:string[], authority_sources:string[]}` |
| `disclaimer` | 精确字面值：`本快照是只读派生视图；自动验证、Review、UA、Accepted、commit、merge、release、delivery 与 Closed 相互独立，任何建议均不构成执行或交付授权。` |

`GET /api/v1/tasks/{task_id}` 使用 schema `ai-dev-flow/dashboard-task-detail/v1`，必选字段为 `schema_version`、`revision`、`task:TaskNode`、`edges:RelationshipEdge[]`、`actions:ActionRecommendation[]`、`parallel_assessments:ParallelAssessment[]`、`diagnostics:Diagnostic[]`。只返回涉及该 task 的对象，排序规则与 snapshot 相同。

`GET /api/v1/health` 使用 schema `ai-dev-flow/dashboard-health/v1`，必选字段为 `schema_version`、`server_state:starting|ready|degraded`、`watcher_state:starting|ready|failed`、`last_refresh_at:string|null`、`snapshot_state:fresh|stale|partial|null`、`revision:string|null`、`diagnostic_counts:{error:int,violation:int,warning:int,info:int}`。health 永远不返回 TASK 正文。

错误 envelope 使用 schema `ai-dev-flow/dashboard-error/v1`：

```json
{
  "schema_version": "ai-dev-flow/dashboard-error/v1",
  "error": {
    "code": "TASK_NOT_FOUND",
    "message": "任务不存在",
    "details": {},
    "provenance": []
  },
  "revision": null
}
```

`details` 只允许该 error code 文档化的 JSON scalar/array，不包含堆栈、命令行、环境变量或 TASK 全文。

Error registry v1（`details` 同样 `additionalProperties=false`）：

| HTTP | error.code | 固定 message | details 精确 shape |
|---|---|---|---|
| 400 | `INVALID_TASK_ID` | `任务 ID 形状非法` | `{task_id:string}` |
| 400 | `HOST_NOT_ALLOWED` | `Host 不允许` | `{host:string}` |
| 404 | `TASK_NOT_FOUND` | `任务不存在` | `{task_id:string}` |
| 404 | `ROUTE_NOT_FOUND` | `路由不存在` | `{path:string}` |
| 405 | `METHOD_NOT_ALLOWED` | `方法不允许` | `{method:string,allow:["GET"]}` |
| 503 | `SNAPSHOT_UNAVAILABLE` | `快照尚不可用` | `{server_state:"starting"|"degraded"}` |
| 500 | `INTERNAL_ERROR` | `内部错误` | `{incident_id:string}` |

所有未预见异常统一映射 `INTERNAL_ERROR`，不得动态创造新 error code。routing/Host/method 错误的 `provenance=[]`；task/snapshot 错误可以附现有 `Provenance[]`。有当前快照时 envelope `revision` 为当前 revision，否则为 null。

### Revision、ETag 与 HTTP 状态

- canonical payload 为上述 snapshot 移除 `revision`、`generated_at` 后的对象；字符串保持 NFC，object key 按 Unicode code point 排序，数组按本节稳定顺序，使用 UTF-8、`ensure_ascii=false`、无空白分隔符序列化后计算 SHA256。相同逻辑输入必须产生相同 revision。
- `ETag` 精确为 `"sha256-<revision>"`，`Cache-Control: private, no-cache`。state、current diagnostics、current source digest 或 last-good digest 任一变化都会改变 revision；仅时间变化不会。
- `GET snapshot`：有快照返回 200；匹配 `If-None-Match` 返回 304 且无 body；首次构建尚无任何 snapshot 返回 503 error。
- `GET task`：malformed task ID 返回 400；形状合法但 snapshot 中不存在返回 404；存在返回 200；尚无 snapshot 返回 503。task ID 只做内存枚举匹配，不拼接为文件路径。
- `GET health` 始终返回 200；`GET events` 正常为 200，尚无 snapshot 为 503。已知路由上的 `POST / PUT / PATCH / DELETE` 返回 405、`Allow: GET` 和 error envelope；未知路由返回 404。

### SSE wire contract

- 响应头固定：`Content-Type: text/event-stream; charset=utf-8`、`Cache-Control: no-cache`、`Connection: keep-alive`、`X-Accel-Buffering: no`。
- 每个数据事件使用 `event: snapshot`，`id: <revision>`，单行 `data:` JSON schema `ai-dev-flow/dashboard-event/v1`：`{schema_version, revision, state, changed_task_ids, reset_required}`；随后两个 LF。发送前先输出 `retry: 2000`。
- 无 `Last-Event-ID` 时立即发送当前 revision，`changed_task_ids` 为全部 task IDs，`reset_required=true`。ID 等于当前 revision 时等待后续变化；ID 不等于当前 revision 时立即发送当前 revision、`changed_task_ids=[]`、`reset_required=true`。
- 同一持续连接上的直接后继 revision 发送精确 changed IDs、`reset_required=false`。服务只保证当前和直接前一 revision 的 diff；断线、跳号或 reset 时前端必须重新 `GET snapshot`，不能从 SSE 自行拼快照。
- 无变化时每 15 秒发送注释 `: keep-alive`，不带 id/data。客户端阻塞超过 30 秒或待发送缓冲超过 64 KiB 时断开，由浏览器按 retry 重连。
- SSE 只是失效通知。前端每次 snapshot event 都以 `If-None-Match` 重新读取，不把 event 当事实源。

### Fixture 合同

- 后端实施任务必须提交同一 schema validator 和至少 8 组 versioned JSON fixtures：`fresh`、`stale`、`partial`、`parse-error`、`dependency-cycle`、`parallel-unknown`、`git-degraded`、`task-detail-error`，以及一份 SSE transcript。
- Kimi 前端只允许从这些 fixtures 和本节 schema 生成类型/Mock；后端响应和前端 fixtures 必须在 CI 中使用同一 validator 严格拒绝 missing/extra/type/enum 错误。
- 前端不得依赖未记录字段；API 变更需要版本提升或兼容扩展，并重新 Review。

### 本地安全

- 默认只绑定 `127.0.0.1`，不绑定 `0.0.0.0`；非本机暴露属于新风险和新授权范围。
- `Host` 只接受配置端口上的 `127.0.0.1:<port>`、`localhost:<port>`；若未来显式启用 IPv6 loopback，再加入 `[::1]:<port>`。其他 Host 返回 400。禁用 CORS，不发送 `Access-Control-Allow-Origin`。
- 静态页面设置 `Content-Security-Policy: default-src 'self'; connect-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'`、`X-Content-Type-Options: nosniff`、`Referrer-Policy: no-referrer`。实现不得依赖 inline script/style，若前端构建要求改变 CSP 必须重新 Review。
- 不渲染未经清理的原始 HTML；Markdown 详情默认以纯文本或经过 allowlist 的安全渲染输出。
- 不读取 `.env`、密钥、证书、用户目录或项目根外文件。
- 不记录 TASK 全文到遥测或外部日志；本任务不引入遥测。
- 静态资源和 API 路由使用固定映射，防止 path traversal。

## 性能与兼容目标

- 核心保持离线、确定性、只读；后端优先使用 Python 标准库并复用现有模块。
- 不为了首版刷新引入数据库、消息队列、常驻系统服务或大型运行时。
- 兼容现有 Legacy TASK；没有 Scheduling Profile 时节点仍可见，但相关结论为 `unknown`。

### 可复现 benchmark protocol v1

- generator schema 固定为 `ai-dev-flow/dashboard-benchmark/v1`；三档数据集为 `50 TASK / 200 edges`、`500 / 2000`、`1000 / 4000`。TASK ID 为 `BENCH-0001` 起的四位序号。
- edge generator 必须逐语句等价执行以下 Python 3.11/3.12 算法；不得用 sample/shuffle 或自选 axis。由于 target 永远小于 source，结果天然为 DAG：

```python
AXES = (
    ("lifecycle", "Ready"),
    ("review_status", "Pending"),
    ("ua_status", "Pending"),
    ("acceptance_authority", "None"),
    ("commit_status", "Uncommitted"),
    ("merge_status", "Unmerged"),
    ("merge_authority", "None"),
    ("close_authority", "None"),
)
rng = random.Random(20260728)
edges = set()
while len(edges) < edge_count:
    source = rng.randrange(2, task_count + 1)
    target = rng.randrange(1, source)
    axis, expected = AXES[rng.randrange(0, len(AXES))]
    edges.add((source, target, axis, expected))
edges = sorted(edges)
```

- 对每个 source，把 `BENCH-{target:04d}#axis=expected` 按 `(target,axis,expected)` 排序并用 `;` 连接；无边为 `none`。`module_index=(i-1)%20+1`、`worktree_index=(i-1)%5+1`。
- TASK 必须用下列 LF-only UTF-8 模板逐字替换 `{...}`；`h1="#"`、`h2="##"`、`bt` 为一个 U+0060 backtick，`depends` 是上一条结果，`module_index` 两位十进制。使用 heading/backtick placeholder 是为了避免本规划 TASK 的现有 Reader 把 fenced fixture 误认成第二个 H1、Contract 或 Core declaration；generator 替换后必须得到下述真实 Markdown。基础内容后追加一个 `<!-- PAD:` + N 个 ASCII `x` + ` -->\n`，使每个 TASK 精确为 2048 bytes；基础内容已超过 2048 时 generator 必须失败。

```markdown
{h1} {task_id}：benchmark {task_id}

{h2} Workflow Contract

- {bt}schema_version{bt}: {bt}adf/v0.7.0{bt}
- `task_id`: `{task_id}`
- `task_type`: `plan`
- `task_class`: `B`
- `lifecycle`: `Ready`
- `review_status`: `Pending`
- `ua_level`: `UA2`
- `ua_status`: `Pending`
- `commit_status`: `Uncommitted`
- `merge_status`: `Unmerged`

{h2} Scheduling

- `scheduling_schema`: `ai-dev-flow/scheduling/v1`
- `priority`: `medium`
- `depends_on`: `{depends}`
- `replaces`: `none`
- `discovered_from`: `none`
- `parent`: `none`
- `conflicts_with`: `none`
- `parallel_intent`: `consider`
- `write_scope`: `file:bench/files/{task_id}.txt;dir:bench/modules/m{module_index}`
- `module_locks`: `bench-common;module-{module_index}`
- `worktree`: `required`
- `branch_hint`: `bench/w{worktree_index}`
- `risk_flags`: `public_api;shared_component;tests_do_not_cover_oracle`

{h2} 目标与边界

- 目标：benchmark fixture
- 非目标：production
- 允许修改：`bench/**`
- 禁止修改：`outside/**`

{h2} 完成标准与验证

- 完成标准：fixture 可解析
- 验证命令或检查：benchmark validator

{h2} Outcome

- Base / Diff：benchmark
- 修改文件：none
- 验证证据：generated fixture
- Review findings：none
```

- 本 benchmark 小节中的 `\n` / `b"\n"` 精确表示单个 LF byte `0x0A`，`\0` / `b"\0"` 表示单个 NUL byte `0x00`，不是反斜杠加字母的两个可见字符。
- TASK_BOARD 的第 1 行精确为 `| 任务 | 名称 | 等级 | 状态 | Review | UA | 验收 | 交付 | 任务文件 |\n`，第 2 行精确为 `|---|---|---|---|---|---|---|---|---|\n`；每个数据行精确为 ``| {task_id} | benchmark {task_id} | B | Ready | Pending | UA2 | Pending / None | commit=Uncommitted;merge=Unmerged;merge_authority=None | [{task_id}](tasks/{task_id}.md) |\n``，按 task ID 排序，不再追加额外空行。
- Git fixture 在临时 repo 写入 `.gitattributes` 内容 `* -text\n`、TASK_BOARD、TASK files 和逻辑 `worktrees.json`。所有 Git 调用固定 `core.autocrlf=false`，作者/提交者为 `Dashboard Benchmark <benchmark@example.invalid>`，时间为 `2026-01-01T00:00:00Z`，commit message 为 `benchmark fixture`。
- 从该唯一 base commit 创建五个 clean linked Worktree：逻辑名/branch 精确为 `w1→refs/heads/bench/w1` 到 `w5→refs/heads/bench/w5`。`worktrees.json` 精确为 object `{schema_version:"ai-dev-flow/dashboard-worktrees-fixture/v1",worktrees:[...]}`；每项包含且只包含 `branch`、`dirty_state`、`head`、`name`，值为对应 `refs/heads/bench/wN`、`clean`、`BASE`、`wN`。数组按 name 排序，object key 按 Unicode code point 排序，使用 UTF-8、`ensure_ascii=false`、separators `(",",":")`、末尾一个 LF。运行时用临时绝对路径和真实 base SHA 替换展示值；`.git/**`、绝对 root 和替换后的 SHA 不进入 dataset SHA256。
- generator 输出 manifest `{schema_version, seed, task_count, edge_count, file_count, total_bytes, dataset_sha256}`。dataset 源文件精确包含 `.gitattributes`、`docs/TASK_BOARD.md`、全部 `docs/tasks/BENCH-*.md` 和 `worktrees.json`，不包含递归的 manifest 自身。每个 source content SHA256 为 64 位小写 ASCII hex；按 NFC POSIX path 排序后，每项编码为 `path_utf8 + b"\\0" + content_sha256_ascii + b"\\n"`，串联后计算 dataset SHA256。`file_count/total_bytes` 只统计这些 source files。两次生成 manifest 不同即 benchmark 无效。
- reference profile：Windows 11 23H2 或更新、x64、至少 8 logical CPU、16 GiB RAM、本地 NTFS SSD、Python 3.11 或 3.12、Git 2.40+、系统电源“平衡”、Defender 默认开启；报告必须记录 OS build、CPU 型号/逻辑核、RAM、磁盘类型、Python/Git 版本和当前进程峰值 RSS。虚拟机、网络盘或电池节能模式结果只能作为补充，不用于首版门禁。
- 所有 benchmark 在新建临时目录运行，不修改真实项目。每项先 5 次 warm-up，再执行 30 个 measured samples；样本使用 `time.perf_counter_ns()`。P50/P95 使用 nearest-rank：排序后索引 `ceil(p*n)-1`。
- `cold_snapshot_ms`：每个 sample 启动新 Python 进程，从读取 manifest/TASK/Git fixtures开始，到完整 snapshot UTF-8 bytes 和 revision 可用为止；包含 import、解析、关系计算与序列化，不包含 HTTP bind，不主动清 OS file cache。
- `stable_save_to_revision_ms`：常驻服务 ready 后，以原子 rename 替换一个 TASK；t0 为 rename 返回，t1 为对应 SSE event 已写入本机 socket。每轮等待 watcher 回到 idle 并恢复同一 fixture；记录 30 次 P50/P95。
- `api_serialize_ms`：内存 snapshot 到完整 UTF-8 response bytes，包含 schema 校验、ETag 和 Content-Length 计算，不包含网络传输；同时记录 payload bytes。
- 结果 JSON 固定字段：`schema_version`、`environment`、`dataset_manifest`、`metric`、`samples_ms`、`p50_ms`、`p95_ms`、`payload_bytes`、`peak_rss_bytes`、`started_at`、`finished_at`。原始 30 个样本必须保留，不能只报汇总。
- 首版门禁仅针对参考 profile 的 `500/2000`：`cold_snapshot p95 <= 2000ms`、`stable_save_to_revision p95 <= 1000ms`、`api_serialize p95 <= 250ms`、完整 snapshot `payload_bytes <= 10 MiB`。50/200 和 1000/4000 只记录趋势。
- 同一 reference machine 连续两次完整运行必须得到相同 dataset SHA256，且各门禁都通过；一次通过不算稳定证据。未达标先用测量定位瓶颈，不直接引入大型依赖。

## 后端测试合同

### 单元测试

- Scheduling `scheduling_schema`、13 字段基数、任意输入顺序到固定规范顺序、分隔/重复/unknown/missing/multiple-section、全 profile/单字段 fail-closed、frozen-text digest 和 provenance。
- legacy inference 只接受 allowlist token，canonical 存在时不运行；自然语言不得产生关系、authority、actionable 或 candidate。
- dependency registry 的 8 个轴逐一覆盖 satisfied/unsatisfied/missing/invalid/conflicting/duplicate、AND 聚合、存储/显示方向和稳定 ID。
- dangling reference、自依赖、dependency cycle、replace cycle、多父冲突和边去重。
- 动作矩阵做正交状态笛卡尔测试；双 Needs Fix、非法高阶状态、unsupported release/repair/commit authority 和 merge/close authority 分支必须符合 fail-closed 规则。
- Windows 路径覆盖 `src/a` vs `src/ab`、大小写、NFC、空格/点、保留名、file/dir overlap、junction/symlink、逃逸和不存在尾部。
- Worktree 覆盖 branch 零/多匹配、detached、locked/prunable、untracked、rename/copy 双路径、submodule、dirty ownership、同 Worktree 与不同 Worktree。
- canonical JSON、稳定排序、相同输入产生相同 revision；仅 `generated_at` 变化不得改变 revision，current error/stale digest 变化必须改变 revision。

### 集成测试

- 临时项目中 TASK/TASK_BOARD/Git/Worktree 合并为单个原子 snapshot。
- TASK 保存、连续保存、1 秒 max-wait、解析失败、恢复成功和删除/新增 TASK 的 SSE revision / changed IDs。
- last-known-good、stale/partial、ETag/304、400/404/405/503、结构化错误和 health degraded。
- SSE 初连、相同/不同 Last-Event-ID、直接后继、revision 跳跃、heartbeat、慢客户端断开与重新 GET snapshot。
- 8 组 JSON fixtures 与 SSE transcript 使用同一 strict schema validator，额外/缺失字段和非法 enum 必须失败。
- Git 不可用、detached HEAD、dirty worktree、路径含空格/中文和命令超时。
- 旧 TASK 无 Scheduling 时继续显示且不产生伪并行结论。
- benchmark generator 两次 manifest/dataset digest 一致，30 样本 nearest-rank 和结果 JSON shape 可复算。

### 安全测试

- 非 loopback bind 被拒绝或要求显式高风险配置。
- Host、CORS、CSP、path traversal、task ID 注入、HTML 注入和项目根逃逸。
- API 与 watcher 全程不产生 TASK/Git 写入。
- 测试前后对目标项目运行 `git status --porcelain=v1 --untracked-files=all`，除测试临时目录外应保持一致。

## 后续实施拆分

用户于 2026-07-28 确认本规划并授权创建以下 TASK；它们已经独立 Review Passed 并进入 Ready，但 Ready 和任务文档本身不构成 execution authority：

1. [`DASHBOARD-BE-001`](DASHBOARD-BE-001.md)：可交由 Kimi 实现 Scheduling Profile Adapter、领域模型、关系/动作/并行引擎、共享 schema / fixtures 与单元测试；该后端开发角色可修改其 TASK allowlist 内的代码/测试。
2. [`DASHBOARD-BE-002`](DASHBOARD-BE-002.md)：可交由 Kimi 实现 Git/Worktree snapshot、原子协调器、HTTP/SSE、安全与集成测试；交付的服务保持对项目事实源只读。
3. [`DASHBOARD-FE-001`](DASHBOARD-FE-001.md)：交由 Kimi 实现关系图优先前端、状态/错误覆盖和浏览器验证；前端运行时只消费只读 API。
4. [`DASHBOARD-INTEGRATE-001`](DASHBOARD-INTEGRATE-001.md)：前后端合同集成、性能、安全、独立 Review 和用户 UA。

所有实施任务都可以交给 Kimi，但每个 TASK 的角色、allowlist 和 Worktree 独立。`BE-001` 先冻结核心与共享 schema / fixtures；随后 `BE-002` 与 `FE-001` 才是安全的候选并行任务；最终 `INTEGRATE-001` 必须串行。Draft、候选并行和任务文档的存在均不代表已经授权执行。

## 完成标准与验证

- 完成标准：本规划的用户偏好、前端边界和后端实施合同冻结；独立 Review 无开放 P0/P1；用户完成 UA2。规划初审的 5 个 P1 已关闭，1 个不阻塞 UA2 的 P2 已在 BE-001 冻结单字节测试 oracle；UA2 已完成。四份实施 TASK 的 4 个 P1 也已全部关闭。
- 验证命令或检查：运行 targeted / project `workflow_lint.py`、TASK_BOARD drift、tracked/untracked whitespace、链接与敏感值检查；每次方案修订后重新执行隔离、只读 Review。
- [x] 已记录本地使用、完整关系优先、无参考界面、前端交给 Kimi 的用户偏好。
- [x] 前端范围只冻结产品结果、风格建议、状态表达和前后端边界，没有指定具体组件实现。
- [x] 后端定义了真相源、Scheduling Profile、领域模型、关系/动作/并行算法、Git/Worktree、实时刷新、API、安全、性能和测试合同。
- [x] 明确候选建议不产生 authority，浏览器和 Snapshot 都不是事实源。
- [x] 规划阶段未直接实施代码或增加依赖；四份后续实施任务使用独立合同、Review 和授权边界。
- [x] 已完成当前 Codex Harness 的隔离、只读 Review；结论为 `Needs Fix`，`P0/P1/P2/P3=0/5/1/0`。
- [x] 当前 TASK 完成隔离、只读 Review 且无 P0/P1。
- [x] 用户完成 UA2，确认产品方向、前端自由度和后端合同。
- [x] 定向 lint、TASK_BOARD drift、tracked/untracked whitespace 和范围检查完成；整仓 lint 的 19 个既有 Legacy error 单独记录，不归因于本 TASK。

## Review 重点

- 是否在任何路径把 TASK_BOARD、Snapshot 或浏览器状态提升成事实源。
- `ActionRecommendation` 是否混淆 Review、UA、Accepted、delivery、Closed。
- `ParallelAssessment=candidate` 是否可能被前端误报成已经授权。
- dependency condition 是否能表达正交状态门禁，是否存在自然语言猜测。
- stale/partial/last-known-good 是否会隐藏当前错误或丢失任务。
- API 是否真正只读并只绑定本机。
- “前端运行时只读”是否已与“Kimi 可承担后端开发角色”明确分离。
- Kimi 的前端自由度是否足够，同时不会破坏状态语义和后端合同。

## 独立 Review（2026-07-28）

- Reviewer：当前 Codex Harness 的独立 `codex exec --ephemeral --sandbox read-only` 上下文；最终成功审查使用冻结证据包且禁止工具调用，Reviewer 前后 TASK / Board 哈希一致，`Workspace writes=None`。
- 冻结基线：`main@fb16bc50f02023aad4a51acd8bf495231fe65f63`。
- 冻结输入：TASK SHA256 `E87E6888A3580FA56ADE9F2D7D9665BD5710CA659D6E3282AA236ECB5EE13D92`；Board SHA256 `062B3852E7A64ED0C755185C4749D0C9400D43864410AF3408C8E6F43EE0C306`。
- 结论：`Needs Fix`；不允许进入 UA2；最高严重度 `P1`；`P0/P1/P2/P3=0/5/1/0`。
- 审查范围：冻结 TASK 全文、TASK_BOARD diff、当前 Reader 枚举与 canonical parser、Board projection、公开 `WorkflowContract.inspect`；既有 19 个 Legacy parse error 未计入本任务 findings。

### DASHBOARD-001-P1-001：Scheduling Profile 缺少可执行 canonical 合同

- 严重度：`P1`。
- 证据：冻结 TASK `:152`、`:156`、`:163`、`:187`；`skills/ai-dev-flow/scripts/_workflow_contract.py:238`、`:248`。
- 问题与影响：当前只有“建议字段”表，没有独立 schema/version、逐行 grammar、列表编码、基数、重复/未知字段、规范化、错误恢复和 provenance 规则；现有 canonical parser 只解析受限的 `## Workflow Contract`。后端 Adapter、revision 与前端 fixture 无法得到唯一实现。
- 关闭标准：冻结 Scheduling schema/version、完整语法和 fail-closed 规则，明确 Adapter 的唯一输入入口。
- 验证：canonical / invalid / legacy / conflict fixtures 对规范化结果、diagnostics、provenance 与 digest 给出确定 oracle。

### DASHBOARD-001-P1-002：依赖条件 registry 与方向未冻结

- 严重度：`P1`。
- 证据：冻结 TASK `:166`、`:178`、`:181`、`:187`；`skills/ai-dev-flow/scripts/_workflow_contract.py:59`、`:69`。
- 问题与影响：`TASK-ID#axis=value` 只给出示例，没有冻结允许轴、枚举来源、缺失/default/非法值、重复条件组合、canonical 排序及 source/target 方向。同一依赖可能被不同实现判为满足、未满足或 unknown，可能误报可执行。
- 关闭标准：建立 dependency-condition registry；未知轴一律 fail closed 为 error/unknown，并冻结方向、组合和冲突规则。
- 验证：覆盖每个允许轴的 satisfied / unsatisfied / missing / invalid / conflicting / duplicate，以及环检测、下游计数和稳定 edge ID。

### DASHBOARD-001-P1-003：动作与 authority 缺少对应事实输入

- 严重度：`P1`。
- 证据：冻结 TASK `:197`、`:198`、`:220`、`:224`、`:255`、`:265`、`:266`、`:268`；`skills/ai-dev-flow/scripts/_workflow_contract.py:63`。
- 问题与影响：规划承诺判断 repair、commit、release、close，但 Reader / TaskNode 没有 commit authority、release 状态/authority 或 repair chain/authority；`Needs Fix` 也未说明使用 lifecycle 还是 review_status。后端只能猜测或长期返回 unknown。
- 关闭标准：逐动作冻结唯一事实输入和 authority 来源；补齐领域字段与合法状态，或明确首版删除无法证明的动作；定义双 `Needs Fix` 轴冲突优先级。
- 验证：正交状态笛卡尔测试证明 Review、UA、Accepted、commit、merge、release、Closed 不互相推导，缺 authority 只能返回 `needs_authority` 或 `unknown`。

### DASHBOARD-001-P1-004：API / SSE 嵌套 schema 不足以独立实施

- 严重度：`P1`。
- 证据：冻结 TASK `:241`、`:247`、`:337`、`:344`、`:402`。
- 问题与影响：端点只冻结顶层字段，未定义 worktrees、diagnostics、provenance、summary、stale sources、Git 错误等嵌套结构和 nullability；SSE 缺少 wire format、初连、心跳、重连与 revision 跳跃语义；ETag 与 stale/partial 的关系未定义。Kimi 与后端可能分别实现出不兼容合同。
- 关闭标准：提供版本化 JSON Schema / OpenAPI 或等价规范和完整示例，冻结枚举、必选/可选/null、HTTP 状态、ETag 与 SSE 重取规则。
- 验证：后端响应和前端 fixtures 使用同一 schema 校验，覆盖 fresh/stale/partial、304、断线重连、revision 跳跃、404/405 与结构化错误。

### DASHBOARD-001-P1-005：Windows 路径与 Worktree 冲突算法不确定

- 严重度：`P1`。
- 证据：冻结 TASK `:172`、`:298`、`:300`、`:305`、`:306`、`:317`、`:319`。
- 问题与影响：`write_scope` 未冻结分隔符、大小写、Unicode、路径段边界、尾随分隔符、文件/目录及 junction/symlink 规范化；相关 dirty 变更和 Worktree 映射也没有算法。路径前缀碰撞或链接逃逸可能误报并行候选。
- 关闭标准：冻结 Windows canonicalization 与 segment-aware prefix 算法，逐 Worktree 采集；定义多 branch match、detached HEAD、untracked/rename/submodule 和无法归属 dirty 的 fail-closed 结果。
- 验证：含空格、中文、大小写差异、前缀碰撞、junction/symlink、多 Worktree、detached HEAD 与 dirty rename 的 fixtures 中，任何不确定情况均不得返回 `candidate`。

### DASHBOARD-001-P2-006：性能验收不可复现

- 严重度：`P2`。
- 证据：冻结 TASK `:364`、`:365`、`:371`、`:380`。
- 问题与影响：缺少参考机规格、合成数据规则、随机种子、预热、重复次数、计时边界、百分位算法和 payload 定义，现有 2 秒 / 1 秒目标无法跨实施者比较。
- 关闭建议：固定 benchmark generator、环境记录模板、冷/热缓存条件、计时与报告格式。
- 验证：同一参考机连续两次生成相同规模和 digest，并输出可比较的 P50/P95。

## Repair Round 1（2026-07-28）

- `repair_chain_id`: `DASHBOARD-001-RC-001`
- `finding_ids`: `DASHBOARD-001-P1-001;DASHBOARD-001-P1-002;DASHBOARD-001-P1-003;DASHBOARD-001-P1-004;DASHBOARD-001-P1-005;DASHBOARD-001-P2-006`
- `closure_contract_hash`: `06648B95CF0B908D33EDE1E283E22972E03D1E8092E1438A50FDDACDF62BB583`
- `allowed_files_hash`: `B20B939C275221792EB9642EFE25AF6555DAEB25521C4AFABFE574ADB3FE225E`
- 允许文件：`docs/tasks/DASHBOARD-001-local-task-relationship-dashboard.md`、`docs/TASK_BOARD.md`。
- Authority：用户在收到 finding 摘要和“Kimi 只读”歧义说明后明确回复“授权”；仅允许本轮规划修订、验证、独立复审和收据同步。
- RED：独立 Review 为 `Needs Fix`，`P0/P1/P2/P3=0/5/1/0`，不允许进入 UA2。
- 修订内容：冻结 Scheduling v1 grammar/读取入口/legacy 规则、8 轴 dependency registry、动作与 authority 矩阵、Windows 路径和 Worktree fail-closed 算法、完整 JSON/SSE wire contract、可复现 benchmark protocol，并把前端运行时只读与 Kimi 后端开发角色分离。
- GREEN：上述 6 个 finding 的 closure criteria 在文档中均有对应 normative contract 和测试 oracle；GREEN 是否成立只能由下一次独立 Review 判定。
- SIGNAL：targeted/project workflow lint、TASK_BOARD drift、diff hygiene、结构关键字/fixture 合同检查和冻结哈希；修订后 Reviewer 前后工作区状态必须一致。
- 当前处置：独立复审仍为 `Needs Fix`，`P0/P1/P2/P3=0/2/1/0`；`P1-001`、`P1-002`、`P1-005` 已判定 Closed，`P1-003`、`P1-004`、`P2-006` 保持 Open；无新 finding。

## Repair Round 1 独立复审（2026-07-28）

- Reviewer：当前 Codex Harness 独立 `codex exec --ephemeral --sandbox read-only` 上下文；冻结证据包、禁止工具调用，`Workspace writes=None`。
- 冻结输入：TASK SHA256 `83AC8970151C7350D747261EDFC1341BD4537F268B5BC4A874C2CDA478E89C0B`；Board SHA256 `CFB5D11B0DCB36E09B60CB64AFE7EEB8115B2182402DA9F123226AAB249D10AF`。
- 结论：`Needs Fix`；不允许进入 UA2；`P0/P1/P2/P3=0/2/1/0`；无新增 finding。
- 已关闭：`DASHBOARD-001-P1-001`、`DASHBOARD-001-P1-002`、`DASHBOARD-001-P1-005`。
- 保持开放：`DASHBOARD-001-P1-003`（authority_state 未逐分支唯一）、`DASHBOARD-001-P1-004`（关键 wire enum/error registry 未完全冻结）、`DASHBOARD-001-P2-006`（generator 算法和实际 fixture 模板不足）。

## Repair Round 2（2026-07-28）

- `attempt_id`: `DASHBOARD-001-RC-001-A2`
- `repair_chain_id`: `DASHBOARD-001-RC-001`
- `finding_ids`: `DASHBOARD-001-P1-003;DASHBOARD-001-P1-004;DASHBOARD-001-P2-006`
- `closure_contract_hash`: `06648B95CF0B908D33EDE1E283E22972E03D1E8092E1438A50FDDACDF62BB583`
- `allowed_files_hash`: `B20B939C275221792EB9642EFE25AF6555DAEB25521C4AFABFE574ADB3FE225E`
- RED：Round 1 复审仍有 2 个 P1、1 个 P2。
- 修订内容：动作矩阵为每个分支冻结 action/eligibility/required_authority/authority_state/主 reason；wire schema 增加完整 enum、edge direction mapping 和 error-code/details registry；benchmark 增加逐语句确定的 edge 算法、实际 TASK/TASK_BOARD 模板、padding 和五 Worktree/Git fixture。
- GREEN：三个残留 finding 的复审缺口均有对应 normative 输入和测试 oracle；是否 Closed 仍由下一次独立 Review 判定。
- 当前处置：独立复审仍为 `Needs Fix`，`P0/P1/P2/P3=0/2/1/0`；无新 finding。三个残留 finding 均有部分 closure criterion 转绿，但仍保持 Open。

## Repair Round 2 独立复审（2026-07-28）

- Reviewer：当前 Codex Harness 独立只读上下文；冻结证据包、禁止工具调用，`Workspace writes=None`。
- 冻结输入：TASK SHA256 `67BF996AF38203E5C36AA302D2E61273FD1BC104D206A248189545ECDBF7EFC1`；Board SHA256 `45DEDCFFCFA6041681DC947530F9D6431F4FDEDC048A5F30C308A3A8686780AD`。
- 结论：`Needs Fix`；不允许进入 UA2；`P0/P1/P2/P3=0/2/1/0`；无新增 finding，已关闭的 `P1-001/002/005` 未回归。
- `P1-003` 进展：合法状态动作矩阵、unsupported action 和 merge/close 映射已转绿；仅非法 Contract 状态的完整动作元组未冻结。
- `P1-004` 进展：wire enum、edge direction、error registry 已转绿；仅 reason code/diagnostic ID 类型冲突与 disclaimer 字面值未冻结。
- `P2-006` 进展：随机算法、AXES、TASK 模板、padding、Git identity/base 和五 Worktree 已转绿；仅 TASK_BOARD separator、worktrees JSON serialization 和 digest entry delimiter 未冻结。

## Repair Round 3 Progress Gate 与修订（2026-07-28）

- `attempt_id`: `DASHBOARD-001-RC-001-A3`
- `repair_chain_id`: `DASHBOARD-001-RC-001`
- `finding_ids`: `DASHBOARD-001-P1-003;DASHBOARD-001-P1-004;DASHBOARD-001-P2-006`
- Progress gate：至少三个冻结子标准 RED→GREEN；`P1-001/002/005` 无 GREEN→RED；无新 blocking finding；最高严重度仍为 P1；动作、wire、benchmark 三个证据向量均严格增加；Round 3 target 已冻结为上一段三个剩余字节/字段歧义。
- 机械资格：`MechanicallyEligible / eligible_mode=ExtendRound3`；当前 Orchestrator 基于用户已授权的同一 repair chain、两次独立复审收据和上述 progress evidence，提升为 `ExtendRound3`。该提升不授权第四轮、UA2 或实现。
- 修订内容：非法 Contract 状态固定完整 action tuple；reason code 与 condition/diagnostic ID 分字段并冻结 disclaimer 字面值；冻结 TASK_BOARD separator、worktrees JSON 和 dataset digest 的逐字节分隔。
- 当前处置：最终独立复审为 `Passed`，`P0/P1/P2/P3=0/0/1/0`；允许进入 UA2，但本轮没有代替用户执行 UA2，也没有开始第四轮修订。

## Repair Round 3 最终独立复审（2026-07-28）

- Reviewer：当前 Codex Harness 独立 `codex exec --ephemeral --sandbox read-only` 上下文；使用冻结证据包、禁止工具调用，`Workspace writes=None`。
- 冻结输入：TASK SHA256 `5CFDFA751988B67FA76AF55C882D104FB85EB5316E459E9ED750DCF7ED9499B0`；Board SHA256 `5F710884CDB49745C06975CA53B4A6A46A7BBB7AC0B22FCDDA1D31626AC1D56A`。
- 结论：`Passed`；允许进入 UA2；最高严重度 `P2`；`P0/P1/P2/P3=0/0/1/0`。
- 已关闭：`DASHBOARD-001-P1-001`、`DASHBOARD-001-P1-002`、`DASHBOARD-001-P1-003`、`DASHBOARD-001-P1-004`、`DASHBOARD-001-P1-005`。
- 保持开放：`DASHBOARD-001-P2-006`。最终 Reviewer 认为 dataset entry 公式中的 `b"\\0"` / `b"\\n"` 与前文“单个 NUL / LF byte”的 `b"\0"` / `b"\n"` 表达仍有字面歧义；该问题不会让当前架构规划产生 P0/P1，但实施 benchmark generator 前必须由后续 TASK 明确选定单字节 `0x00` / `0x0A` oracle。
- 新增 finding：无；已关闭 P1 无回归；Kimi 前端运行时只读、Kimi 可承担独立后端开发任务、以及本轮 authority 边界均未回归。
- 状态边界：这里只记录 `Review Passed`。UA2、Accepted、实现、commit、merge、push、release 和 Closed 均未发生。

<a id="dashboard-001-ua2-2026-07-28"></a>
## 用户 UA2 确认（2026-07-28）

- 用户动作：用户在收到 `Review Passed`、`P0/P1/P2/P3=0/0/1/0` 和后续四任务的简明开发顺序后明确回复“确认，并创建文档”。
- 确认范围：本地关系图优先的产品方向、Kimi 前端自由度、Kimi 可承担后端开发角色、后端只读运行时合同，以及 `BE-001 → (BE-002 ∥ FE-001) → INTEGRATE-001` 的实施拆分。
- UA 动作与结果：`UA2 Passed / User Confirmed`。
- 未扩展 authority：该确认只授权记录 Accepted 和创建四份 Draft TASK 文档，不授权执行代码、增加依赖、创建 Worktree、Review 子任务、commit、merge、push、release 或 Closed。

## 四份实施 TASK 初始独立 Review（2026-07-28）

- Reviewer：当前 Codex Harness 的独立 Reviewer 子上下文；只收到 NTFS `RX` 冻结证据副本，主工作区六份规划文件前后哈希一致，`Workspace writes=None`。
- 冻结基线：`main@fb16bc50f02023aad4a51acd8bf495231fe65f63`。
- 冻结输入：父 TASK `6F92E4C3E565541D85DEA21C728D5CF2D988AC7BDC92F0430DF64586F0668DF3`；Board `935D574AE1ED3D924049C232C2228436FEFCE830BAC22B423DF5372106FB303`；四份子 TASK 哈希记录在各自 Review 段。
- 结论：整体 `Needs Fix`，`P0/P1/P2/P3=0/3/0/0`；`DASHBOARD-BE-001` 单项 Passed，其他三项在 findings 关闭前不得进入 Ready。
- `DASHBOARD-TASKS-P1-001`：BE-002 与 FE-001 的候选并行结论和父 TASK 默认串行算法冲突。
- `DASHBOARD-TASKS-P1-002`：BE-002 原宽范围可修改 BE-001 已验收 core/contracts。
- `DASHBOARD-TASKS-P1-003`：INTEGRATE 原宽范围可修改三个 Accepted 前置实现，且启动说明文件未命名。

## 四份实施 TASK Repair Round 1（2026-07-28）

- `attempt_id`: `DASHBOARD-TASKS-RC-001-A1`
- `repair_chain_id`: `DASHBOARD-TASKS-RC-001`
- `finding_ids`: `DASHBOARD-TASKS-P1-001;DASHBOARD-TASKS-P1-002;DASHBOARD-TASKS-P1-003`
- `closure_contract_hash`: `FFAD4CD3056F5B53ACE52834029CAE725B12BEFA74BE5026D559C02811F8D56C`
- `allowed_files_hash`: `2CC6D9330E0EE012E62E0AB6F893B5201A7A9A865564E22B3E033314C263FC1F`
- Authority：用户明确要求审核四份实施 TASK、发现问题时修复直至可执行，并另行授权提交规划文件；范围只限本 TASK、四份实施 TASK 与 TASK_BOARD。
- RED：初始独立 Review 有 3 个 P1，整体不能进入 Ready。
- 修订：增加 Accepted contract consumer exception v1 和唯一 pair fixture；把 BE-001/BE-002 写范围拆成不重叠命名空间并固定 contracts/core 只读；把集成范围收紧为 `dashboard/integration/**` 与 `dashboard/README.md`，增加前置 artifact hash 门禁。
- GREEN：三个 finding 均有机器可验证的关闭标准和 fail-closed 反例；是否 Closed 只能由下一次独立复审判定。

## 四份实施 TASK Repair Round 1 独立复审（2026-07-28）

- Reviewer：同一独立 Reviewer 子上下文；读取 17 文件 NTFS `RX` 冻结副本，文件数和 SHA256 前后无变化，`Workspace writes=None`。
- 结论：整体 `Needs Fix`，`P0/P1/P2/P3=0/1/0/0`。
- 已关闭：`DASHBOARD-TASKS-P1-001`、`DASHBOARD-TASKS-P1-002`、`DASHBOARD-TASKS-P1-003`。
- 新增：`DASHBOARD-TASKS-P1-004`；父 TASK/TASK_BOARD 的 BE-001 条件执行授权与 BE-001 自身“未授权实施”冲突。
- 单项：BE-002、FE-001、INTEGRATE-001 Passed；BE-001 技术合同无回归，仅 authority 冲突阻止 Ready。

## 四份实施 TASK Repair Round 2（2026-07-28）

- `attempt_id`: `DASHBOARD-TASKS-RC-001-A2`
- `repair_chain_id`: `DASHBOARD-TASKS-RC-001`
- `finding_ids`: `DASHBOARD-TASKS-P1-004`
- `closure_contract_hash`: `FFAD4CD3056F5B53ACE52834029CAE725B12BEFA74BE5026D559C02811F8D56C`
- `allowed_files_hash`: `2CC6D9330E0EE012E62E0AB6F893B5201A7A9A865564E22B3E033314C263FC1F`
- 修订：BE-001 自身明确记录复审 Passed、Ready、规划 baseline commit 三个前置，之后只能由新对话在独立 Worktree 和精确 allowlist 内实施，停在 `Review Passed / UA3 Pending`。
- GREEN：BE-001、父 TASK 与 TASK_BOARD 的 authority、前置条件、执行位置和停止点一致；是否关闭由下一次独立复审判定。

## 四份实施 TASK Repair Round 2 最终独立复审（2026-07-28）

- Reviewer：同一独立 Reviewer 子上下文；读取 17 文件 NTFS `RX` 冻结副本，检查前后 `17 → 17`，SHA256 差异 `None`，`Workspace writes=None`。
- 冻结输入：父 TASK `A7B7E1A4F6BB973DD542B7C6E79D47CAC0E27B99D106423CF19B7CDB4A82EA2`；Board `4AB7D91A9B72CB221E4766C951ECBD9474025FCD311AA673215C9E4DB548FAEA`；四份子 TASK 哈希记录在各自最终 Review 段。
- 结论：`Passed`，`P0/P1/P2/P3=0/0/0/0`；允许四份实施 TASK 从 Draft 推进到 Ready。
- 已关闭：`DASHBOARD-TASKS-P1-001`、`DASHBOARD-TASKS-P1-002`、`DASHBOARD-TASKS-P1-003`、`DASHBOARD-TASKS-P1-004`；无新增 finding，无回归。
- 状态边界：这里只记录实施 TASK Review Passed/Ready；四项均未实施、未 UA、未 Accepted、未形成代码 commit、未 merge、未 push、未 release、未 Closed。

## Outcome

- Base / Diff：`fb16bc50f02023aad4a51acd8bf495231fe65f63` 到六文件规划 baseline `371383f0d93048fa2a31c1ca1306a7e1421650ff`；仅规划文档。
- 修改文件：本 TASK、`docs/TASK_BOARD.md`，以及新建的 `DASHBOARD-BE-001`、`DASHBOARD-BE-002`、`DASHBOARD-FE-001`、`DASHBOARD-INTEGRATE-001` 四份 TASK 文档。
- 验证证据：最终 Ready 状态写回后，本 TASK targeted workflow lint 为 `errors/violations/warnings=0/0/2`，四份子 TASK 各为 `0/0/1`；project lint 为 `19/0/28`，19 个 error 均来自既有 Legacy TASK；TASK_BOARD 无 board diagnostics，DASHBOARD 文件无 error；四份 Scheduling 均为 13/13 字段且无 dangling TASK reference；ai-dev-flow 完整单元测试 `81/81 Passed`；`git diff --check` 通过。
- Review findings：规划 Review 为 `Passed`；四份实施 TASK 最终独立 Review 为 `Passed`，`P0/P1/P2/P3=0/0/0/0`，4 个实施合同 P1 全部 Closed。
- UA 动作与结果：`UA2 Passed / User Confirmed`；用户确认产品方向和任务拆分。
- 状态边界：当前为 `Accepted / Review Passed / UA2 Passed / Committed` 规划；四份子任务均为 `Ready / Review Passed / Uncommitted / Unmerged`，均未实施、未 UA、未 Accepted、未 release、未 Closed。工作区原有两个 `__pycache__/` 未跟踪目录不属于本 TASK，本轮不修改或清理。
- 剩余风险：整仓 19 个 Legacy parse error 为既有历史问题，当前未修复；BE-001 实施后仍需独立 Review 和用户 UA3。
- 下一步：在新对话和独立 Worktree 执行 BE-001，停在 `Review Passed / UA3 Pending`；其他三项仍无 execution authority。
