# DASHBOARD-INTEGRATE-001：集成本地任务仪表盘并完成回归验收

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `DASHBOARD-INTEGRATE-001`
- `task_type`: `test`
- `task_class`: `D`
- `lifecycle`: `Review`
- `review_status`: `Passed`
- `ua_level`: `UA6`
- `ua_status`: `Pending`
- `acceptance_authority`: `None`
- `close_authority`: `None`
- `commit_status`: `Uncommitted`
- `merge_status`: `Unmerged`
- `merge_authority`: `None`

## Scheduling

- `scheduling_schema`: `ai-dev-flow/scheduling/v1`
- `priority`: `high`
- `depends_on`: `DASHBOARD-BE-001#commit_status=Committed;DASHBOARD-BE-001#lifecycle=Accepted;DASHBOARD-BE-001#review_status=Passed;DASHBOARD-BE-001#ua_status=Passed;DASHBOARD-BE-002#commit_status=Committed;DASHBOARD-BE-002#lifecycle=Accepted;DASHBOARD-BE-002#review_status=Passed;DASHBOARD-BE-002#ua_status=Passed;DASHBOARD-FE-001#commit_status=Committed;DASHBOARD-FE-001#lifecycle=Accepted;DASHBOARD-FE-001#review_status=Passed;DASHBOARD-FE-001#ua_status=Passed;DASHBOARD-FE-001-REPAIR-001#commit_status=Committed;DASHBOARD-FE-001-REPAIR-001#lifecycle=Accepted;DASHBOARD-FE-001-REPAIR-001#merge_status=Merged;DASHBOARD-FE-001-REPAIR-001#review_status=Passed;DASHBOARD-FE-001-REPAIR-001#ua_status=Passed`
- `replaces`: `none`
- `discovered_from`: `DASHBOARD-001`
- `parent`: `DASHBOARD-001`
- `conflicts_with`: `none`
- `parallel_intent`: `serial`
- `write_scope`: `file:dashboard/README.md;dir:dashboard/integration`
- `module_locks`: `dashboard-api;dashboard-backend;dashboard-contracts;dashboard-ui`
- `worktree`: `required`
- `branch_hint`: `codex/dashboard-integrate-001`
- `risk_flags`: `architecture;core_execution_path;parallel_writers;public_api;real_environment;security;shared_component;tests_do_not_cover_oracle`

## 目标与边界

- 目标：把已 Accepted 的后端核心、后端服务和前端集成成可在 Windows 本机运行的完整仪表盘，并证明共享合同、实时更新、性能、安全、可访问性和既有 workflow 行为没有回归。
- 目标：形成可重复的本地启动说明、端到端证据、独立只读 Review 和用户 UA6 收据。
- 非目标：不发布公网服务、不创建安装器/自动更新器、不上传项目数据、不自动写 TASK/Git、不进行 release 或外部同步。
- 非目标：不在集成阶段重做架构或更换前后端技术栈；发现合同缺口必须退回对应任务，不在本任务静默兼容。
- 允许修改：未来执行时仅限 `dashboard/integration/**`、`dashboard/README.md`、`docs/tasks/DASHBOARD-INTEGRATE-001.md` 和该任务在 `docs/TASK_BOARD.md` 的投影行。
- 禁止修改：`dashboard/contracts/**`、`dashboard/backend/**`、`dashboard/frontend/**`、`skills/ai-dev-flow/**` 既有行为、其他已 Accepted TASK、版本/发布文件、本机 Skill 和仓库外内容；禁止新增依赖、发布、同步或删除。发现前置实现缺陷必须返回对应前置 TASK repair/re-Review，不得在集成层兼容或改写 Accepted artifact。

## 集成合同

### 固定目录责任

- `dashboard/integration/**`：集成装配胶水、端到端测试、benchmark runner、浏览器证据脚本和只读本地 launcher；不得复制或改写前后端业务实现。
- `dashboard/README.md`：本任务唯一允许修改的启动说明，必须给出 Windows 本地启动、验证、停止和已知限制。
- 执行前记录 `dashboard/contracts/**`、`dashboard/backend/**`、`dashboard/frontend/**` 的基线 hash manifest；执行后逐项复算，不一致即失败并返回对应前置 TASK。

### 合同与数据一致性

- 后端响应、前端类型、Mock、fixtures 和 SSE transcript 必须通过同一个 versioned strict validator。
- 端到端测试必须覆盖 fresh、stale、partial、parse error、dependency cycle、parallel unknown、Git degraded、task detail error 和 API disconnected/reconnect。
- 保存 TASK 或 TASK_BOARD 后，稳定保存到新 revision 的 P95 不超过 1000ms；前端只在收到 event 后重新 GET snapshot。
- revision、ETag、changed_task_ids 和 last-known-good 行为必须用真实本地文件变更验证。

### 用户主流程

1. 从明确的本地命令启动服务并打开 loopback 页面。
2. 首屏看到完整关系图、项目/branch/HEAD、数据健康和当前可行动节点。
3. 筛选下一动作、并行候选、必须串行、需要决定和 diagnostic。
4. 打开任务详情，核对正交状态、依赖、原因、Worktree 和 provenance。
5. 修改测试 TASK 文档，观察 revision 更新、关系变化、stale/partial 和错误恢复。
6. 断开/重启服务，验证前端 disconnected/reconnect/reset 且不保留伪事实。

### 回归与安全

- 运行 ai-dev-flow 现有完整测试，证明没有修改或破坏 WorkflowContract、workflow_lint、TASK_BOARD projection 和 repair gate。
- 对样例仓库和当前仓库运行只读扫描，扫描前后 Git status 必须一致。
- 验证非 GET 方法、非法 Host、CORS、path traversal、项目外路径、HTML/Markdown 注入和敏感值不会越界。
- 验证关闭浏览器或服务后没有后台写操作、残留锁、自动 Worktree 或外部网络连接。

### 性能与可用性

- 参考环境和数据生成严格采用 `DASHBOARD-001` benchmark 合同；500/2000 数据集两次运行均达到 cold snapshot、save-to-revision、API serialize 和 payload 门禁。
- 1366px、1920px、2560px 完成视觉检查；键盘、对比度、非颜色表达、screen-reader label 和 reduced motion 达到 WCAG 2.2 AA 目标。
- 所有性能和浏览器证据必须记录环境、原始样本、截图/日志和可复现命令，不能只写结论。

## 依赖与授权

- 前置依赖：`DASHBOARD-BE-001`、`DASHBOARD-BE-002`、`DASHBOARD-FE-001` 均达到 Review Passed、对应 UA Passed、Accepted，并形成可引用 Git baseline。
- Base commit：规划基线为 `fb16bc50f02023aad4a51acd8bf495231fe65f63`；实际集成 base 必须从三个前置任务的共同最新 baseline 重新冻结。
- 已有 authority：允许本 TASK 实施合同的独立 Review、有限 repair、Ready 写回与规划提交；用户于 2026-07-29 明确要求“执行 DASHBOARD-INTEGRATE-001”，并在前置 P1 修复合并后再次要求“继续完成原始任务，达到可验收标准”；授权在精确 allowlist 内更新集成基线、实施集成、安装锁文件中既有依赖、启动本地服务、运行自动验证、执行隔离 Review 和有限 repair，直到 `Review Passed / UA6 Pending`。
- 未授权动作：新增或升级依赖、commit、merge、push、release、外部同步、删除分支/Worktree和 Closed。
- 执行位置：独立集成 Worktree `D:\open-source\ai-dev-flow-wt\dashboard-integrate-001`，分支 `codex/dashboard-integrate-001`；当前基线 `main@9fe4c4453af1525a6a47adc856575a70c8437911`。

## 路由与风险

- 路由：`Controlled`。
- Policy 输入：`task_class=D`、`ua_level=UA6`、风险包含 `architecture`、`core_execution_path`、`parallel_writers`、`public_api`、`real_environment`、`security`、`shared_component`、`tests_do_not_cover_oracle`。
- Reviewer 闸门：`Required`；端到端证据完成后、请求 UA6 前必须执行隔离、只读 Review。
- 主要风险：前后端合同表面一致但真实响应漂移、实时更新遗漏、集成时修改共享语义、旧 workflow 回归、本机服务越界、性能在真实项目规模下失效。
- 停止条件：任一前置任务未 Accepted；需要改变共享 schema/架构/技术栈；需要未授权依赖、安装器、发布或外部连接；Git status 前后不一致；P0/P1 未关闭。

## 完成标准与验证

- 完成标准：Windows 本机能够从文档化命令启动并完成全部用户主流程，退出后无事实源写入或残留副作用。
- 完成标准：共享 validator、端到端状态矩阵、HTTP/SSE、Git/Worktree、安全、性能和可访问性验证全部通过。
- 完成标准：ai-dev-flow 既有完整测试和 workflow_lint 行为无回归。
- 完成标准：独立 Review 无开放 P0/P1，用户完成 UA6 回归验收。
- 验证命令或检查：运行三个前置任务记录的完整 build/typecheck/lint/test 命令和本任务端到端测试。
- 验证命令或检查：运行 `python -B -X utf8 -m unittest discover -s skills/ai-dev-flow/tests -p "test_*.py" -v` 与 dashboard 全套测试。
- 验证命令或检查：运行 reference benchmark 两次并保留 30 个原始样本、P50/P95、payload 和 RSS。
- 验证命令或检查：运行 `python skills/ai-dev-flow/scripts/workflow_lint.py . --format json`，区分既有 Legacy diagnostics 与本任务新增问题。
- [x] 前后端 strict contract、所有异常状态和真实 revision 更新通过。
- [x] 现有 ai-dev-flow tests、dashboard tests、浏览器、可访问性、安全和性能验证通过。
- [x] 集成前后 Git status 一致，除当前 TASK allowlist 内预期 diff 外无写入。
- [x] 机器检查 implementation diff 只命中 `dashboard/integration/**`、`dashboard/README.md` 和本任务收据；前置 Accepted artifact hash manifest 完全一致。
- [x] 隔离、只读 Review 无开放 P0/P1。
- [ ] 用户完成 UA6，确认新流程与典型旧流程均可用。
- [x] `git diff --check` 通过，diff 只归属当前 TASK。

## 验收建议

- 用户动作等级：UA6（用户在本机运行新仪表盘并回归关键旧 workflow）。
- 是否需要用户实机测试：是。
- 用户需要做什么：启动本地仪表盘，使用真实项目观察关系图和实时更新，再确认现有 workflow_lint/TASK 使用习惯未被破坏。
- agent 已提供的证据：实施时必须包含构建、测试、benchmark、浏览器截图、可访问性、安全、Git 前后状态和独立 Review。
- 不验收的风险：自动证据不能完全替代用户判断关系图是否直观，以及本机真实项目是否保持原工作习惯。
- 是否允许关闭任务：否；当前已 `Review Passed`，但 UA6、Accepted、commit、merge、delivery 与 Closed 均未完成。

## 四份实施 TASK 初始独立 Review（2026-07-28）

- Reviewer：当前 Codex Harness 的独立 Reviewer 子上下文；仅收到 NTFS `RX` 冻结证据副本，`Workspace writes=None`。
- 冻结输入：本 TASK SHA256 `B09901E44BFC29FD556D06BDF6433AAB74A37C9038B57C0AA8F55E009A4FFD7E`；基线 `main@fb16bc50f02023aad4a51acd8bf495231fe65f63`。
- 结论：`Needs Fix`；`P0/P1/P2/P3=0/1/0/0`。
- `DASHBOARD-TASKS-P1-003`：原 `dashboard/**` allowlist 可改写三个已 Accepted 前置实现，且本地启动说明没有唯一文件。

## 四份实施 TASK Repair Round 1（2026-07-28）

- `attempt_id`: `DASHBOARD-TASKS-RC-001-A1`
- `repair_chain_id`: `DASHBOARD-TASKS-RC-001`
- `finding_ids`: `DASHBOARD-TASKS-P1-003`
- 修订：写范围收紧为 `dashboard/integration/**` 与 `dashboard/README.md`；contracts/backend/frontend 固定只读；增加前置 artifact hash manifest 和 diff allowlist 门禁。
- GREEN：关闭标准已有确定文件、失败条件和验证 oracle；是否关闭由下一次独立复审判定。

## 四份实施 TASK 最终独立复审（2026-07-28）

- 冻结输入：本 TASK SHA256 `FC23820DC0884A337C77D9A0D25EA05EA823303B1A5C5B36A449255CA74EB0DE`。
- 结论：`Passed`；`DASHBOARD-TASKS-P1-003` Closed 且最终复审无回归，无新增 finding；整体 `P0/P1/P2/P3=0/0/0/0`。
- Reviewer 确认：E2E、回归、安全、性能、Accepted artifact 保护和 UA6 合同足以进入 Ready。
- 状态边界：`Ready / Review Passed / UA6 Pending / Uncommitted / Unmerged`；没有 execution authority。

## Outcome

- Base / Diff：base=9fe4c4453af1525a6a47adc856575a70c8437911;diff=working-tree
- 修改文件：新增 `dashboard/integration/**` 的 artifact guard、loopback launcher、真实栈 Python/Chrome 测试、Windows bounded atomic replace 和冻结 benchmark runner；新增 `dashboard/README.md`；更新本 TASK 与 TASK_BOARD 投影。三个 Accepted artifact 目录没有 diff。
- 验证证据：artifact guard `100/100`、working/root digest `65e0fae81347f40105ca0bd70900a63fbb06a663641ff0a9e02e39412535f3cf` 且 `added=[] / changed=[] / missing=[]`；Repair 后集成 Python `15/15`，Dashboard backend `130/130`、公共 Reader/治理 `85/85`、前端 unit `81/81`、build/typecheck/lint/codegen 与 Chrome `79/79` 全部通过；真实当前项目 Chrome 三合同视口 `3/3`、临时真实项目异常状态矩阵 `1/1` 通过，退出后 5173/8765 无监听残留。当前 Python 3.13 双跑仅为补充证据；冻结 Python 3.12 正式证据引用已 Accepted 的 BE repair 双跑，是否足以关闭本轮 `P1-002` 等待独立复审。
- Review findings：规划阶段 `DASHBOARD-TASKS-P1-003` Closed；工程阻断 `DASHBOARD-INTEGRATE-P1-001` 已由 `DASHBOARD-FE-001-REPAIR-001` 的独立 Review 与 UA4 关闭；本轮集成实现独立 Review 待执行。
- UA 动作与结果：UA6 Pending；自动验证已经完成，必须等待本轮实现独立 Review Passed 后才向用户发起。
- 隔离位置：`D:\open-source\ai-dev-flow-wt\dashboard-integrate-001`，分支 `codex/dashboard-integrate-001`。
- 回滚方式：当前全部集成实现仍为未提交 diff；如用户明确要求放弃，可在精确确认文件清单后移除本任务新增文件并还原本 TASK 投影，当前未执行任何删除或历史改写。
- 状态边界：In Progress / Review Pending / UA6 Pending / Uncommitted / Unmerged；未 Accepted、未交付、未发布、未 Closed。
- 剩余风险：自动测试与截图不能代替用户判断真实关系图是否直观；本轮实现独立 Review 和用户 UA6 尚未完成。
- 下一步：对冻结 implementation diff 执行隔离只读 Review；无开放 P0/P1 后转为 `Review Passed / UA6 Pending` 并提供实机验收步骤。

## 实施启动收据（2026-07-29）

- 用户授权：用户明确要求“执行 DASHBOARD-INTEGRATE-001”；授权范围仅为本 TASK 精确 allowlist 内的集成实现、既有锁文件依赖安装、本地启动、自动验证、隔离只读 Review 和有限 repair，不包含 commit、merge、push、release、外部同步、删除或 Closed，也不代替 UA6。
- 实施基线：`main@dbbc5e7591a06bc4d381401882c42515a7e05873`，已包含 BE-001、BE-002、FE-001 的 Accepted / Review Passed / UA Passed / Committed / Merged 本地证据。
- 隔离位置：`D:\open-source\ai-dev-flow-wt\dashboard-integrate-001`；分支 `codex/dashboard-integrate-001`。
- 前置 artifact manifest：`dashboard/contracts/**`、`dashboard/backend/**`、`dashboard/frontend/**` 共 99 个 Git 基线文件；逐文件 SHA256 聚合 digest 为 `5453f3ff664e5f7602b3d030fc7250e44530cedb10ec26323378ab91411a3edb`。
- 联调 RED：现有 Vite 代理请求携带 `Host: 127.0.0.1:5173`，真实后端按 loopback Host 合同返回 HTTP 400 `HOST_NOT_ALLOWED`；修复只能位于 `dashboard/integration/**`，不得修改已 Accepted 前端/后端。
- 状态边界：曾进入 `In Progress / Review Pending / UA6 Pending / Uncommitted / Unmerged`；后续真实浏览器阻断见下节。

## 集成阻断收据（2026-07-29）

- `finding_id`: `DASHBOARD-INTEGRATE-P1-001`
- 严重度 / 状态：`P1 / Closed by DASHBOARD-FE-001-REPAIR-001`。
- 现象：真实 `main` 派生快照为 `fresh`，含 21 个任务、210 个 parallel assessments 和 93 条 diagnostics；在合同视口 `1366×768`，工具栏无界展开全部 pair，关系图 `region[aria-label="任务关系图区域"]` 被裁剪为 hidden，用户主流程第 2 步“首屏看到完整关系图”无法执行。
- 根因证据：`Toolbar.renderPairList()` 对 `snapshot.parallel_assessments` 全量渲染；`.pair-list` 位于 flex toolbar 且没有折叠、分页、虚拟化或高度/overflow 上限。现有 mock 浏览器数据仅覆盖少量 pair，`81/81` unit 与 `76/76` mock Chrome 全绿仍未覆盖真实 210 pair。
- 真实证据：`npx playwright test -c ../integration/playwright.config.mjs` 在 1366×768 失败 `1/1`；截图 `dashboard/integration/test-results/real-stack-real-backend-an-3cf40-e-current-read-only-project/test-failed-1.png`，SHA256 `8036156431893EC38EE47DDEC3856A57A52A9223FB917D6494F55E982799973D`；trace 与 error context 位于同一 ignored test-results 目录。进程退出后 `127.0.0.1:5173/8765` 均无监听残留。
- 影响：关系图优先这一核心产品结果在真实项目不可用；不能进入 benchmark 后的最终实现 Review，也不能向用户提出 UA6 验收建议。
- 处置：命中“发现前置实现缺陷必须返回对应前置 TASK repair/re-Review，不得在集成层兼容或改写 Accepted artifact”停止条件。本任务不修改 `dashboard/frontend/**`，保持 `Blocked / Review Pending / UA6 Pending / Uncommitted / Unmerged`。
- 关闭标准：在 `DASHBOARD-FE-001` 受控 repair 中增加真实规模 pair oracle，确保 1366/1920/2560 首屏关系图可见且 pair 仍可访问、键盘可用、候选不被表示为 authority；独立 Review Passed、UA4/Accepted/Committed 新 baseline 形成后，本任务重新冻结并复跑真实栈。
- 最终机器门禁：`git diff --check` 通过；implementation 16 个 changed/untracked 文件全部位于 TASK allowlist，outside `0`；无 conflict marker；Accepted artifact `changed=[] / missing=[]`；真实栈与测试退出后 `127.0.0.1:5173/8765` 均无监听残留。

## 集成恢复与基线重冻结（2026-07-29）

- 恢复授权：用户在确认原始集成任务尚未完成后明确要求“继续完成原始任务，达到可验收标准”；目标仍为 `Review Passed / UA6 Pending`，不包含 commit、merge、push、release、外部同步、删除或 Closed。
- 基线更新：16 个既有任务文件先按 SHA256 清点并放入可恢复 stash；任务分支从 `dbbc5e7` 快进到 `main@9fe4c4453af1525a6a47adc856575a70c8437911`，再恢复任务源文件并仅在 TASK_BOARD 行产生预期冲突，已保留新 repair 投影并恢复本任务 `In Progress` 状态。
- 前置修复：`DASHBOARD-FE-001-REPAIR-001` 已 `Accepted / Review Passed / UA4 Passed / Committed / Merged`；feature=`3c8160f`、merge=`2ac8b3b`、receipt=`9fe4c44`，`DASHBOARD-INTEGRATE-P1-001` 的真实规模关闭标准已具备。
- Artifact 重冻结：`dashboard/contracts/**`、`dashboard/backend/**`、`dashboard/frontend/**` 共 100 个 Git 基线文件；逐文件 SHA256 聚合 digest 为 `65e0fae81347f40105ca0bd70900a63fbb06a663641ff0a9e02e39412535f3cf`。
- 证据保护：旧失败报告、trace 与 Python cache 已另存于未删除的生成物 stash；源文件 stash 在冲突恢复后继续保留，待最终逐文件 SHA256 核对完成前不清理。

## 最终自动验证收据（2026-07-29）

- Artifact / scope：`dashboard/contracts/**`、`dashboard/backend/**`、`dashboard/frontend/**` 相对 `9fe4c44` 无 diff；artifact guard 为 `ok=true / 100/100 / changed=[] / missing=[]`，聚合 digest 为 `65e0fae81347f40105ca0bd70900a63fbb06a663641ff0a9e02e39412535f3cf`。实现写入只位于本 TASK allowlist；未执行删除、commit、merge、push、release、同步或 Closed。
- Python 回归：`py -3.13 -B -X utf8 -m unittest discover -s dashboard/integration/tests -p "test_*.py" -v` 为 `11/11`；Dashboard backend 为 `130/130`；`skills/ai-dev-flow/tests` 为 `85/85`，均通过。
- 前端回归：`npm run verify` 通过 codegen check、TypeScript、ESLint、Vitest `81/81`、Vite production build 和 Google Chrome Playwright `79/79`。浏览器矩阵覆盖 8 个 versioned fixtures、task detail error、SSE disconnected/reconnect、键盘、对比度、非颜色表达和 reduced motion。
- 真实栈：`DASHBOARD_PYTHON=C:\Python313\python.exe` 下运行集成 Playwright，当前真实项目在 `1366×768 / 1920×1080 / 2560×1440` 为 `3/3`；均确认 strict snapshot、无 CORS、只读标识、实时连接、关系图首屏可见和 50+ 并行评估折叠。退出后 `127.0.0.1:5173/8765` 监听为 `none`。
- 三视口截图：`real-stack-1366x768.png` SHA256 `EC3DB891BDA4A389D10676E5F6CD91F14DA8EFC3D5BAC424F7184CC8862EE162`；`real-stack-1920x1080.png` SHA256 `E6CBB7EE1C89F6221F695474C1D494E65439773292E811148E6B4175D5080450`；`real-stack-2560x1440.png` SHA256 `6A7B53583587EF4EC62B398A39C24D77FBCBDD58C436932A0F5448E093E60226`。截图位于 ignored `dashboard/integration/artifacts/screenshots/`。
- Supplemental benchmark 环境：Windows 11 build `10.0.26200`、AMD Ryzen 7 7735H、16 logical CPU、29.7GB RAM、SSD、Python 3.13.5、Git 2.50.1.windows.1、Balanced power、Defender real-time enabled；两轮数据集 SHA256 均为 `3934d0f774c1caa83ffa75d18c48107379847b8cda5e5645f49018c23b559eb0`。Python 版本不满足冻结 profile，因此以下两轮不用于正式门禁。
- Supplemental Run 1：cold P50/P95 `1420.8905/1659.8612ms`；stable-save-to-SSE `841.1555/952.1393ms`；API serialize `139.9058/187.1812ms`；payload `2649806` bytes；仅 timing thresholds 通过。`summary.json` SHA256 `84AD222062C10AFC93E1429F203A2891F91B3947086E29258D05509127022042`。
- Supplemental Run 2：cold P50/P95 `1362.2652/1611.2174ms`；stable-save-to-SSE `763.2456/868.7820ms`；API serialize `125.1165/138.8780ms`；payload `2649806` bytes；仅 timing thresholds 通过。`summary.json` SHA256 `74058096477CCEB0B8D10453F9538B67C1B4B4324133E8A0E6282E274E688A68`。
- Qualifying Python 3.12 基线：当前 100 个 Accepted artifacts 所引用的 BE repair 已在同一参考机、同一 dataset SHA256 上完成连续双跑并经独立 Review/UA3/Accepted；cold p95=`1460.0747/1418.6262ms`、stable-save p95=`775.1131/840.7838ms`、API p95=`140.5135/133.4503ms`、payload=`2673648` bytes，六份结果 SHA256 和 nearest-rank 复算记录位于 `DASHBOARD-BE-001-REPAIR-001` 的 Campaign ER-1 收据。
- 安全边界：真实栈验证 GET/ETag/304、POST=405、恶意 Host=400、无 CORS 与真实 revision；后端全量测试覆盖 path traversal、项目外路径、loopback bind、严格 error envelope 与内部敏感错误去除；前端使用 DOM text API 渲染合同字段，浏览器长字段/异常状态测试未发现 HTML/Markdown 越界。
- Workflow lint：单 TASK 当前结构无 error；工作树状态转换因未提交历史会保留 `W_TRANSITION_UNVERIFIABLE`。项目级 `19` 个 errors 属于既有历史任务，本 TASK 未新增 project error；最终 Review 状态写回后再次复核。

## 实现独立 Review Round 1（2026-07-29）

- Reviewer：原生 `codex exec review --uncommitted`，session `019fad53-88b2-7b20-92fb-09bfda5b63d2`，sandbox=`read-only`；审查前后 20 文件 manifest SHA256 均为 `55cc659f94e0235a927e669d80ad340554edc0b61aaf69e84a54edee29b11667`，`Reviewer workspace writes=None`。
- 结论：`Needs Fix`；不允许进入 UA6；`P0/P1/P2/P3=0/3/5/0`。
- `DASHBOARD-INTEGRATE-RVW-001-P1-001`：artifact guard 只枚举 base paths，无法发现 Accepted roots 中新增的非忽略文件。
- `DASHBOARD-INTEGRATE-RVW-001-P1-002`：benchmark 只检查 Windows，不拒绝偏离冻结 reference profile 的结果；本机 Python 3.13 双跑只能作为补充证据。
- `DASHBOARD-INTEGRATE-RVW-001-P1-003`：TASK 提前勾选异常状态端到端矩阵，但当时只有既有 fixture/mock 浏览器证据，没有真实 backend-to-frontend 覆盖。
- `DASHBOARD-INTEGRATE-RVW-001-P2-001`：stable-save 的 t0 位于原子 rename 之前，与冻结计时边界不符。
- `DASHBOARD-INTEGRATE-RVW-001-P2-002`：README 把 Python 3.13 写死，和 Python 3.11/3.12 支持/性能合同冲突。
- `DASHBOARD-INTEGRATE-RVW-001-P2-003`：frontend `Popen` 启动失败时 backend 尚未进入 cleanup finally。
- `DASHBOARD-INTEGRATE-RVW-001-P2-004`：真实栈测试 `setUp` 超时失败时 `tearDown` 不会执行。
- `DASHBOARD-INTEGRATE-RVW-001-P2-005`：cold child 超时未 kill/wait，可能残留进程并阻止临时目录清理。
- 状态边界：`Needs Fix / Review Needs Fix / UA6 Pending / Uncommitted / Unmerged`；自动验证不能覆盖 Review，Round 1 的 finding 是否关闭只能由下一轮独立复审判定。

## 实现 Repair Round 1（2026-07-29）

- `P1-001` 定向修复：新增 current tracked + non-ignored untracked 路径枚举与 `added[]` 失败门禁，并增加“新增文件”回归 oracle。
- `P1-002` 定向修复：新增 `DASHBOARD-001/windows-reference-v1` 全字段资格检查，summary 单独记录 `reference_profile`，最终 `passed` 必须同时满足 profile 与性能 gates；Python 3.13 会确定失败，不能再被报告为正式门禁 GREEN。
- `P1-003` 定向修复：新增临时真实 Git 项目状态驱动器和真实 Chrome matrix；首个快照覆盖 partial，随后通过真实文件/SSE 覆盖 fresh、parallel unknown、dependency cycle、parse error、last-known-good stale、Git degraded、真实 404 task-detail error 和断线/reconnect，定向测试 `1/1` 通过。
- `P2-001..005` 定向修复：t0 移到 rename 返回之后；README 改为通用 Python 3.11+ launcher 与 Python 3.11/3.12 benchmark；launcher 从首个子进程起统一 finally 回收；测试用 `addCleanup` 覆盖 setup failure；cold child 超时执行 kill + communicate。
- 定向验证：artifact/launcher/benchmark/atomic `13/13`、真实 HTTP/revision `1/1`、真实 backend-to-frontend abnormal matrix `1/1` 均通过。
- 未关闭边界：当前机器只安装 Python 3.13；旧 Run 1/2 已降级为 supplemental。冻结 profile 下两轮正式 benchmark 尚未重跑，`P1-002` 不能由实施者自批关闭，也不能进入 UA6。

## 实现独立 Review Round 2（2026-07-29）

- Reviewer：原生 `codex exec review --uncommitted`，session `019fad67-b80f-7c22-a140-113c920446dc`，sandbox=`read-only`；冻结输入 24 文件 manifest SHA256 `29d19ec4f8867b2b3aa4b7699f770ff89bc0a917b185a6689eb7d134f35889b1`，`Reviewer workspace writes=None`。
- 结论：`Needs Fix`；不允许进入 UA6；`P0/P1/P2/P3=0/2/3/0`。Round 1 的 artifact addition、Python version、真实异常状态矩阵、计时边界、README 和三类既有 cleanup findings 未重新开放。
- `DASHBOARD-INTEGRATE-RVW-002-P1-001`：profile 只检查 `Windows-11-`，未强制 build >= Windows 11 23H2，也未记录/拒绝虚拟机。
- `DASHBOARD-INTEGRATE-RVW-002-P1-002`：磁盘类型读取 PhysicalDisk 0，而 benchmark 实际运行于 `%TEMP%`；多磁盘机器可能误判资格。
- `DASHBOARD-INTEGRATE-RVW-002-P2-001`：launcher readiness 使用环境代理感知的 `urlopen`，可能把 loopback 探测发给代理。
- `DASHBOARD-INTEGRATE-RVW-002-P2-002`：stable-save watcher/server 已启动后，部分 setup 失败点仍位于 cleanup try/finally 之外。
- `DASHBOARD-INTEGRATE-RVW-002-P2-003`：state-matrix 的 `subprocess.run(timeout=...)` 只保证终止 Node CLI，不能保证 Windows 下回收 launcher/backend/Vite 整棵进程树。
- 状态边界：`Needs Fix / Review Needs Fix / UA6 Pending / Uncommitted / Unmerged`；Round 2 findings 的关闭只由下一轮独立复审判定。

## 实现 Repair Round 2（2026-07-29）

- `P1-001` 定向修复：新增 `os_build >= 10.0.22631` 门禁；记录 manufacturer/model/HypervisorPresent，并用明确 VM manufacturer/model markers 得出 `virtual_machine_detected`，profile 要求 physical machine。HypervisorPresent 单独留证但不把启用 VBS/Hyper-V 的物理机误判为 VM。
- `P1-002` 定向修复：从 `%TEMP%` drive 解析 `Get-Partition -> Get-Disk -> Get-PhysicalDisk`，记录 `temporary_volume`、实际 backing media type 与 filesystem；`local_ntfs_ssd` 只对该真实卷判定。
- `P2-001` 定向修复：readiness 使用固定 `ProxyHandler({})` opener；HTTP_PROXY/ALL_PROXY 不参与 loopback health。
- `P2-002` 定向修复：从 watcher/server 启动前进入统一 cleanup scope；connection/watcher/server/thread 按实际启动状态关闭，fixture 仅在有原始 bytes 时恢复。
- `P2-003` 定向修复：state-matrix 改用独立 Windows process group 的 `Popen`；超时后以精确 PID 调用 shell-free `taskkill /T /F` 回收整棵测试进程树，再 `communicate()` 回收句柄。
- 定向验证：profile 的 23H2/VM/Python 拒绝 oracle、真实 temp volume 环境报告、proxy-disabled opener、benchmark setup cleanup 和 Playwright timeout tree cleanup 共 `12/12` 通过；真实 backend-to-frontend matrix 再次 `1/1` 通过。当前环境报告只因 Python `3.13` 使 `reference_profile.passed=false`，其余 9 项 profile checks 全部为 true。

## 实现独立 Review Round 3（2026-07-29）

- Reviewer：原生 `codex exec review --uncommitted`，session `019fad76-a1a1-7761-a0b5-5646dbe4a32d`，sandbox=`read-only`；冻结输入 25 文件 manifest SHA256 `c621e7de81c1773abd52791c8bf34ecba89311f093a0e8c1be7072835cece1c1`，`Reviewer workspace writes=None`。
- 结论：`Needs Fix`；不允许进入 UA6；`P0/P1/P2/P3=0/1/2/0`。Findings 连续从 Round 1 的 `3/5`、Round 2 的 `2/3` 降至本轮 `1/2`，无 GREEN 回归、严重度未升、固定 evidence vector 增加，满足 policy `round_3_progress`；用户已有“继续直至可验收”任务级连续修复授权，Orchestrator 提升为 `ExtendRound3`。
- `DASHBOARD-INTEGRATE-RVW-003-P1-001`：仅“未命中已知 VM marker”仍可能把未知云虚拟机或 CIM unknown 当物理机，资格判断必须 fail-closed 三态。
- `DASHBOARD-INTEGRATE-RVW-003-P2-001`：t0 虽移到 `atomic_replace_bytes()` 返回之后，但 watcher 可在函数返回与 caller 取时钟之间运行；时间戳必须由原子替换函数在 rename 返回点直接返回。
- `DASHBOARD-INTEGRATE-RVW-003-P2-002`：matrix 只在 TimeoutExpired 回收进程树；KeyboardInterrupt/其他 communicate 异常仍可能残留。
- 状态边界：`Needs Fix / Review Needs Fix / UA6 Pending / Uncommitted / Unmerged`；第三轮仅处理上述冻结 finding，不扩大 scope。

## 实现 Repair Round 3（2026-07-29）

- `P1-001` 定向修复：机器资格改为 `physical / virtual / unknown` 三态；CIM unknown、未识别 manufacturer/model 和已知云/VM marker 全部 fail-closed，只有显式 allowlisted 物理 OEM（含本机 LENOVO）或 Surface 才能进入 physical。
- `P2-001` 定向修复：`atomic_replace_bytes()` 在成功 `os.replace` 返回后的同一函数内立即采集并返回 `perf_counter_ns()`；stable-save 直接以该值作为 t0，消除 caller 调度窗口。
- `P2-002` 定向修复：matrix 的 process-tree 清理进入 `finally`；TimeoutExpired、KeyboardInterrupt 和其他异常只要 child 未退出都执行精确 PID tree termination + communicate reap。
- 定向验证：三态 physical/virtual/unknown fail-closed、rename completion timestamp、timeout 与 interruption tree cleanup 共 `10/10`；真实 backend-to-frontend matrix `1/1` 再次通过。当前环境明确报告 `LENOVO / 21HY / classification=physical`，仍只因 Python 3.13 使 profile 总结果 false。

## 实现独立 Review Round 4（2026-07-29）

- Reviewer：原生 `codex exec review --uncommitted`，session `019fad8d-0d35-75f2-bc4d-b3e77fdf7857`，sandbox=`read-only`；冻结输入 25 文件 manifest SHA256 `462e4079fa9a98e898aa300c3cd6ea974685d5fa142ab5480e9e16c4c30b089c`，Reviewer 最终消息单独保存于 ignored evidence 目录。
- 结论：`Needs Fix`；不允许进入 UA6；`P0/P1/P2/P3=0/2/1/0`。Round 3 的机器三态、rename 返回点计时和任意异常进程树清理未重新开放。
- `DASHBOARD-INTEGRATE-RVW-004-P1-001`：Vite 5.4 默认 CORS middleware 位于 API proxy 之前；未显式 `cors: false` 时，其他 localhost/127.0.0.1 端口页面可能读取只读 API。
- `DASHBOARD-INTEGRATE-RVW-004-P1-002`：电源方案资格依赖本地化显示名称；中文输出在 Reviewer 读取路径中出现 mojibake，可能拒绝本应合格的参考机，必须优先使用稳定 Balanced scheme GUID。
- `DASHBOARD-INTEGRATE-RVW-004-P2-001`：Vite 提供的 HTML/静态资源没有 CSP、`X-Content-Type-Options` 和 `Referrer-Policy`；API 安全头不能保护静态页。
- 状态边界：`Needs Fix / Review Needs Fix / UA6 Pending / Uncommitted / Unmerged`；仅修复上述冻结 findings。

## 实现 Repair Round 4（2026-07-29）

- `P1-001` 定向修复：Vite 明确设置 `cors: false`；真实 HTTP oracle 现在携带来自另一 loopback 端口的 `Origin`，并验证代理响应不包含 `Access-Control-Allow-Origin`。
- `P1-002` 定向修复：Balanced 资格优先匹配 Windows 稳定 GUID `381b4222-f694-41f0-9685-ff5bb260df2e`，同时保留中英文显示名兼容；新增实际中文 `powercfg` 形状的资格测试。
- `P2-001` 定向修复：静态响应增加 CSP、`nosniff`、`no-referrer` 和 `private, no-cache`。CSP 只允许同源资源、当前 loopback Vite WebSocket、data image 与 Vite 注入样式；因已 Accepted 前端的 Ajv 必须运行时编译 schema，`script-src` 保留同源并显式允许 `unsafe-eval`，不开放外部脚本源。
- 定向验证：launcher/benchmark/真实 HTTP 共 `13/13` 通过；第一次真实 Chrome `0/3` 明确失败于 Ajv 被 CSP 拦截，按 trace 定向补充同源 `unsafe-eval` 后三合同视口 `3/3` 通过。失败属于本轮修复引入且已形成回归 oracle；退出后 5173/8765 无监听残留。

## 实现独立 Review Round 5（2026-07-29）

- Reviewer：原生 `codex exec review --uncommitted`，session `019fad98-c405-7f31-8aa1-54c544d40111`，sandbox=`read-only`；冻结输入 25 文件 manifest SHA256 `0e0202664d370463f06201759f57ad49de4f4c45bcb34c979f8ee78a1657c638`，Reviewer 最终消息单独保存于 ignored evidence 目录。
- 结论：`Needs Fix`；不允许进入 UA6；`P0/P1/P2/P3=0/2/5/0`。
- `DASHBOARD-INTEGRATE-RVW-005-P1-001`：Round 4 已超过自主三轮上限，但 TASK 没有完整、chain/history/scope-bound 的 `RepairCampaignAuthority` 收据；Round 4 候选不得用于推进状态。
- `DASHBOARD-INTEGRATE-RVW-005-P1-002`：异常矩阵只在浏览器侧 abort SSE，没有让真实后端收到过期 `Last-Event-ID`，未覆盖真实 `reset_required` 分支及 selection/detail/focus 清空。
- `DASHBOARD-INTEGRATE-RVW-005-P2-001`：中文 Windows 下 `taskkill` 输出使用本机代码页，强制 UTF-8 text decode 可能在 finally 中掩盖原始异常并跳过回收。
- `DASHBOARD-INTEGRATE-RVW-005-P2-002`：cold benchmark 超时只 kill Python 根进程，可能遗留其 Git 后代。
- `DASHBOARD-INTEGRATE-RVW-005-P2-003`：launcher 启动 readiness 循环不观察 Ctrl+C stop event，最坏仍等待 60 秒。
- `DASHBOARD-INTEGRATE-RVW-005-P2-004`：真实栈测试 teardown 超时只 terminate launcher，可能遗留 backend/Vite。
- `DASHBOARD-INTEGRATE-RVW-005-P2-005`：真实 HP 机器 Manufacturer 精确值 `HP` 未命中带尾空格的 marker，会被误判为 unknown。
- 状态边界：`Needs Fix / Review Needs Fix / UA6 Pending / Uncommitted / Unmerged`。

## RepairCampaignAuthority 激活（2026-07-29）

- 历史纠正：Round 4 候选及其 Round 5 复审不用于任何状态晋级；它们保留为本次 ER-1 的输入差异与 RED 证据，不被追认为合规自主修复轮次。
- 用户授权原文：`授权你继续，直至可验收为止`，随后再次明确 `那继续完成原始任务，达到可验收标准`；当前 Orchestrator 基于本对话 trusted context，将其记录为仅绑定 `DASHBOARD-INTEGRATE-001`、冻结验收合同与外层 write scope 的连续修复授权，不包含 commit、merge、push、release、外部同步、删除、Accepted 或 Closed。
- Campaign：`campaign_id=DASHBOARD-INTEGRATE-RCAMPAIGN-002`；`profile=core_product`；`task_id=DASHBOARD-INTEGRATE-001`；`acceptance_contract_hash=0bb233a618ea3daf3998e1cec059f1ec56abe5a78af40c749d291331e050b76a`。
- Acceptance canonical vector：Accepted artifact `100/100` 零增删改；真实当前项目与异常状态浏览器矩阵通过；冻结 reference profile 性能证据满足全部 gates；独立只读 Review 无开放 P0/P1；最终状态严格为 `Review Passed / UA6 Pending / Uncommitted / Unmerged`。
- Scope manifest：`allowed_exact_files=[dashboard/README.md, docs/TASK_BOARD.md, docs/tasks/DASHBOARD-INTEGRATE-001.md]`；`allowed_path_prefixes=[dashboard/integration/]`；`allowed_scope_hash=5df30b755364ac03eca324998dc7ef89ee32177b5f0601e771108f5dff53cfd9`。
- Activation chain：`repair_chain_id=DASHBOARD-INTEGRATE-RC-005`；target findings 为 Round 5 的 7 个 IDs；`closure_contract_hash=98f700d2a27374636c9adcd8231ac9e573e293fd8b6bc34b37bff213aec382d1`；`allowed_files_hash=4ef222ce2b1a1c080facbd95d2a318c79764d2d675926f16cecd3b41102cfa6f`；`activation_chain_digest=7c14b66e6ebbb923657a5ac7aa0514ce47c456d271124c3b178f8c529eddfce9`。
- Chain allowed files：`dashboard/integration/benchmark.py`、`dashboard/integration/launcher.py`、`dashboard/integration/process_tree.py`、`dashboard/integration/state_matrix.py`、`dashboard/integration/tests/browser/state-matrix.spec.mjs`、`dashboard/integration/tests/test_benchmark.py`、`dashboard/integration/tests/test_launcher.py`、`dashboard/integration/tests/test_process_tree.py`、`dashboard/integration/tests/test_real_stack.py`、`dashboard/integration/tests/test_state_matrix_runner.py`、`docs/tasks/DASHBOARD-INTEGRATE-001.md`；均为完整、规范化的仓库相对路径并按字典序进入 hash。
- Closure canonical vector：campaign receipt 完整绑定；真实过期 SSE ID 进入后端 reset 并清 selection/detail/focus；Windows taskkill 不解码输出；cold timeout 回收完整树；启动等待响应 stop；真实栈 teardown 回收完整树；HP OEM 判为 physical。
- History binding：Round 5 session、冻结 manifest、`Needs Fix` 与 `0/2/5/0` canonical head 为 `activation_history_head_hash=39f908e521c0b808e7b4321c2c06a34b7670cc5e402bfdda6986c1aa00189440`。
- Authority receipt：`authority_id=authority-DASHBOARD-INTEGRATE-RCAMPAIGN-002`；`authority_mode=repair_campaign`；`source_kind=user_message`；`source_ref=conversation:current-thread#continue-until-acceptance-ready`；`source_text_sha256=2ce228b8750572c8800f0c5b2372ff56315bd44ae4540de0ace00cb1213b72c1`；`target=reach Review Passed / UA6 Pending inside the frozen task scope without delivery actions`；canonical `receipt_hash=d88a72bb70e6f1874a0928a086faf40af9a61546ccf1a9c77bdbfaba07c2ee84`。
- Initial campaign state：`attempt_count=0`、`consecutive_no_progress=0/4`、`latest_outcome=NotStarted`、`history_head_hash=d88a72bb70e6f1874a0928a086faf40af9a61546ccf1a9c77bdbfaba07c2ee84`、`latest_review_receipt_hash=null`；state `receipt_hash=c9ea9682eca680ff0f520c1d728242f53b9180a166125d1ed7aafda8cf7d2169`。
- Safety snapshot：`p0_finding / security_boundary_change / data_integrity_risk / scope_outside_campaign / irreversible_action / external_side_effect / test_oracle_weakened / unapproved_dependency_change / required_evidence_missing` 全部为 `false`；`safety_hash=1051bbfa558883f7dc6c4d3377d6a69fbf1ad133fe001aa0f6e6772ae1757a26`。
- Hash 规则：所有 canonical hash/receipt hash 均为 UTF-8、`ensure_ascii=false`、对象键字典序、JSON separators `(',', ':')`；receipt hash 排除自身 `receipt_hash` 字段。
- Orchestrator promotion：trusted context、TASK、验收合同、scope、activation chain/history head 与 safety 已冻结；提升为 `EscalatedRepairAllowed / authority_mode=repair_campaign / next_attempt_id=ER-1`。每次 patch 后仍必须独立只读 Review；campaign 有进展清零 streak，连续 4 次无进展或任一 hard stop 立即停止。

## Campaign ER-1 候选（2026-07-29）

- `P1-001` 治理修复：Round 4 明确降级为未晋级候选；以上 `RepairCampaignAuthority` 在本轮 patch 前完成 task/acceptance/scope/chain/history/safety 绑定，ER-1 不依赖追认。
- `P1-002` 功能修复：异常矩阵新增第二个真实 Chrome 用例。它先建立 selection/detail/downstream focus，再以过期 64 位 `Last-Event-ID` 直接请求真实 backend SSE，验证原始帧包含 `reset_required=true` 后原样交给浏览器，最终断言 selection、detail、focus 全部清空。初版只观察 browser abort 为旧 RED；Vite 长连接首分块未刷新形成两次新 RED；最终真实 backend frame bridge 为 GREEN。
- `P2-001 / P2-002 / P2-004` 清理修复：新增统一 `process_tree` helper；Windows `taskkill /T /F` 输出全部送入 DEVNULL，不做本地代码页解码；cold benchmark、state matrix 和真实栈 teardown 均回收精确根 PID 的完整树并由 caller `communicate/wait` 回收根句柄。
- `P2-003` 停止修复：launcher readiness 循环在 health probe 前及 200ms bounded wait 中观察 stop event；启动阶段 Ctrl+C 会立即进入 finally 清理，不再等待完整 startup timeout。
- `P2-005` profile 修复：Manufacturer 规范化后精确 `HP` 判为 physical；保留其他 OEM marker 与 virtual/cloud 优先 fail-closed 规则。
- 定向与完整验证：过程中的测试命名/fixture mock 两个问题均形成明确 RED 并已纠正；最终集成 Python `24/24` 通过，其中真实异常矩阵含 `2/2` Chrome 用例；当前真实项目 `1366×768 / 1920×1080 / 2560×1440` 为 `3/3`。服务退出后 5173/8765 无监听残留。
- Campaign progress candidate：7 个 closure criteria 均由 RED 转 GREEN，未发现 GREEN→RED、严重度上升、scope 外文件、依赖变化、外部副作用或 hard-stop；最终 `attempt_count/consecutive_no_progress` 只能在 ER-1 独立复审后写为 `1/0`。

## Campaign ER-1 独立 Review（2026-07-29）

- Reviewer：原生 `codex exec review --uncommitted`，session `019fadb1-2e7d-74c1-a5ea-1e7b754ee7b4`，sandbox=`read-only`；冻结输入 27 文件 manifest SHA256 `a08bde6b46b990a877463c5b482fdd383a1863c84d27edbc7d37d795ddf905ae`，最终消息 SHA256 `630f67ef9d46ded221e6a40a09d4d7ed11b3507a2e0a789b33b0de060782c023`。
- 结论：`Needs Fix`；`P0/P1/P2/P3=0/0/3/0`。Round 5 的两个 P1 与五个实现 P2 均未重新开放；高优先级 findings 从 `2` 降至 `0`，属于 `MeasurableProgress`。
- `DASHBOARD-INTEGRATE-RVW-006-P2-001`：launcher 自身 `_stop()` 仍只 terminate 直接 backend/Vite PID，正常停止可能遗留 Git/esbuild 后代。
- `DASHBOARD-INTEGRATE-RVW-006-P2-002`：ER-1 chain allowed-files 列表除首项外使用缩写，不能无猜测复算 hash。
- `DASHBOARD-INTEGRATE-RVW-006-P2-003`：TASK_BOARD 仍停留在 Round 3，没有投影 Round 4/5、campaign 与 ER-1 当前状态。
- ER-1 receipts：review `receipt_hash=64c18ce6672e32fccc10a8e0a902e69dfc40e605420a83af89a2bf878f1a36e4`；attempt `receipt_hash=1f0ea4cb63caff3ea4f809ce2cf989d70930b5032f1a81ee33cfa73b4d0ddfea`。
- Campaign state：`attempt_count=1`、`consecutive_no_progress=0/4`、`latest_outcome=MeasurableProgress`、`history_head_hash=1f0ea4cb63caff3ea4f809ce2cf989d70930b5032f1a81ee33cfa73b4d0ddfea`、`latest_review_receipt_hash=64c18ce6672e32fccc10a8e0a902e69dfc40e605420a83af89a2bf878f1a36e4`；state `receipt_hash=d8d50a90b6d4652e3d3a7e74275b0df3626107f12b191348c4239bd94b92c08f`；hard-stop snapshot 仍全部 false。

## Campaign ER-2 候选（2026-07-29）

- Orchestrator promotion：同一 task-bound campaign 继续有效；`next_attempt_id=ER-2 / EscalatedRepairAllowed`。新 chain 为 `DASHBOARD-INTEGRATE-RC-006`，绑定 Round 6 三个 P2；`closure_contract_hash=96fee54c365bfe4a4acd2b9b7e84e2776af5a0cc4265f3ee8ec34276cecac07e`、`allowed_files_hash=313bab1585b9e94b40ea274df1bd4729da25b3d1393ebef5af81ed6013c339ef`、`chain_digest=dc09fb36455c554c47ce91ed235c041de7c395d3ebd0cb1638a07b7a248d20c7`。
- ER-2 exact allowed files：`dashboard/integration/launcher.py`、`dashboard/integration/tests/test_launcher.py`、`docs/TASK_BOARD.md`、`docs/tasks/DASHBOARD-INTEGRATE-001.md`。
- `P2-001` 修复：launcher 两个 child 以独立 process group 启动；`_stop()` 在正常停止和 5 秒超时兜底都调用统一整树终止 helper，再 `wait()` 回收根句柄。
- `P2-002` 修复：ER-1 chain 11 个 allowed files 全部展开为完整仓库相对路径，hash 规则不变。
- `P2-003` 修复：TASK_BOARD 投影更新为 R4/R5、campaign ER-1 `0P1/3P2` 与 ER-2 待独立复审；lifecycle/review/UA/commit/merge 仍严格为 `Needs Fix / Needs Fix / Pending / Uncommitted / Unmerged`。
- 验证：launcher 定向 `7/7`、完整集成 Python `25/25`、当前真实项目三合同视口 Chrome `3/3` 均通过；退出后 5173/8765 无监听残留。
- Campaign progress candidate：三个 P2 closure criteria 均已进入 GREEN 候选，未修改依赖、Accepted roots 或 campaign 外文件；等待 ER-2 独立只读复审。

## Campaign ER-2 独立 Review（2026-07-29）

- Reviewer：原生 `codex exec review --uncommitted`，session `019fadbe-d17d-7e51-9096-bc2aa38bfd54`，sandbox=`read-only`；冻结输入 27 文件 manifest SHA256 `1f99b3cde903d3314385ab868e5f9be8ffaa9b6f572ef7937bce3264f88ee103`，最终消息 SHA256 `ca6a7f4b50b96f9c6298b6351d11a2229c586efb50a18943c1a920dcf21e7b9c`。
- 结论：`Needs Fix`；`P0/P1/P2/P3=0/0/3/0`。ER-1 的 launcher tree cleanup、完整 chain paths 与看板投影三个 P2 均未重新开放。
- `DASHBOARD-INTEGRATE-RVW-007-P2-001`：launcher 只等待 health HTTP 200；首个 snapshot 尚未发布时可能过早开页面。
- `DASHBOARD-INTEGRATE-RVW-007-P2-002`：Playwright webServer 与 `RealStackTests.setUp` 同样只等 health 200，慢 checkout 下首次 snapshot 请求可能 503。
- `DASHBOARD-INTEGRATE-RVW-007-P2-003`：cold benchmark 的非 TimeoutExpired 异常（含 Ctrl+C）未终止并回收独立 process group。
- ER-2 receipts：review `receipt_hash=18ea7dada87d1f25c71a4c4155c8bfe0ddfb5695f72b4e978f469460f4192ac2`；attempt `receipt_hash=07129543ffae46fe162b15f3a75feb63baa9848abf5844bc71f24f8c7704687a`。
- Campaign state：`attempt_count=2`、`consecutive_no_progress=0/4`、`latest_outcome=MeasurableProgress`、`history_head_hash=07129543ffae46fe162b15f3a75feb63baa9848abf5844bc71f24f8c7704687a`、`latest_review_receipt_hash=18ea7dada87d1f25c71a4c4155c8bfe0ddfb5695f72b4e978f469460f4192ac2`；state `receipt_hash=038393146c396e0ba94b1510457244f1dfeb2cfa1a10f4a499aeea666a8dd19e`；hard-stop snapshot 仍全部 false。

## Campaign ER-3 候选（2026-07-29）

- Orchestrator promotion：task-bound campaign 继续有效；`next_attempt_id=ER-3 / EscalatedRepairAllowed`。新 chain 为 `DASHBOARD-INTEGRATE-RC-007`；`closure_contract_hash=ce8cf1feb13146ef3c40eb9ca8966bb66a4bc5a9fbe0e6b22d882d1bb8854afd`、`allowed_files_hash=7dd7e1eb797312004107a34ceb6b691a20e95050715188a872e70eebad436c74`、`chain_digest=e32aa6c7a2bd6035a81da0bea2e69b12ba8de598d721fcf84370b1be7f1b4ae7`。
- ER-3 exact allowed files：`dashboard/integration/benchmark.py`、`dashboard/integration/launcher.py`、`dashboard/integration/playwright.config.mjs`、`dashboard/integration/tests/test_benchmark.py`、`dashboard/integration/tests/test_real_stack.py`、`docs/TASK_BOARD.md`、`docs/tasks/DASHBOARD-INTEGRATE-001.md`。
- `P2-001 / P2-002` 修复：launcher readiness、Playwright webServer 与 Python real-stack setup 全部统一等待 `/api/v1/snapshot` HTTP 200；该状态只在 coordinator 已发布首快照后成立，partial/stale/fresh 均可立即进入 UI，不再以 health 的早期 200 误判 ready。
- `P2-003` 修复：cold child 的 TimeoutExpired 保持整树终止与回收；新增 `BaseException` 路径，在 Ctrl+C/SystemExit/其他 communicate 异常时同样终止完整 process group、二次 communicate 回收，并重新抛出原始异常。
- 验证：定向 readiness/benchmark/真实 HTTP `18/18`、完整集成 Python `26/26`、当前真实项目三合同视口 Chrome `3/3` 均通过；退出后 5173/8765 无监听残留。
- Campaign progress candidate：三个新 P2 closure criteria 已进入 GREEN 候选；无依赖、Accepted roots、scope 或 hard-stop 变化，等待 ER-3 独立只读复审。

## Campaign ER-3 独立 Review（2026-07-29）

- Reviewer：原生 `codex exec review --uncommitted`，session `019fadcd-25bb-7e82-93e0-c4a3c81ffc6b`，sandbox=`read-only`；冻结输入 27 文件 manifest SHA256 `6efbb511382df975662c28532bd15075e89aa5fe9401266d4caffd5cdcfd6f8f`，最终消息 SHA256 `ceae26cf507a549b95652fa58cbd5e98b9ebed436546e6ddc1c4851fe35294d1`。
- 结论：`Needs Fix`；`P0/P1/P2/P3=0/1/1/0`。ER-2 的首快照 readiness 与 benchmark interruption 三个 P2 均未重新开放；本轮发现两个新的可复现问题，仍不允许进入 UA6。
- `DASHBOARD-INTEGRATE-RVW-008-P1-001`：`launcher.py`、`benchmark.py`、`state_fixture.py`、`state_matrix.py` 直接以文档命令或脚本路径启动时，解释器初始搜索路径没有仓库根，新增的 `dashboard.integration.*` 导入可在干净环境中失败。
- `DASHBOARD-INTEGRATE-RVW-008-P2-001`：Accepted artifact 基线使用 `git cat-file --filters`，摘要受调用方 `core.autocrlf` 影响；在另一种合法 checkout 配置下，同一 Git baseline 可能被误报为不匹配。
- Campaign state：`attempt_count=3`、`consecutive_no_progress=0/4`、`latest_outcome=MeasurableProgress`；高优先级 finding 从 ER-2 的 `0` 暂时重新出现为 `1`，但 ER-2 三项全部关闭且固定 evidence vector 继续增加；hard-stop snapshot 仍全部 false。

## Campaign ER-4 候选（2026-07-29）

- Orchestrator promotion：同一 task-bound campaign 与外层 scope 继续有效；`next_attempt_id=ER-4 / EscalatedRepairAllowed`。新 chain 为 `DASHBOARD-INTEGRATE-RC-008`；`closure_contract_hash=392632fb616868a0ffb925197a18bbbeb2db70ee50e67d62d1cf7f35bf0a493d`、`allowed_files_hash=88f0bcca5f751268f96aafa163e9a0e8c7e1adf430246f0992b42c44db7fff7b`、canonical repair `chain_digest=afe2ef911370bae7e56624081958a257d896361faf771618ea23e56d0c40fd9c`。
- ER-4 exact allowed files：`dashboard/README.md`、`dashboard/integration/accepted-artifacts.json`、`dashboard/integration/artifact_guard.py`、`dashboard/integration/benchmark.py`、`dashboard/integration/launcher.py`、`dashboard/integration/state_fixture.py`、`dashboard/integration/state_matrix.py`、`dashboard/integration/tests/test_artifact_guard.py`、`dashboard/integration/tests/test_launcher.py`、`docs/TASK_BOARD.md`、`docs/tasks/DASHBOARD-INTEGRATE-001.md`。
- `P1-001` 修复：四个直接入口在导入 `dashboard.integration.*` 之前，从自身绝对路径确定仓库根并显式加入模块搜索路径；回归测试从临时目录清空 `PYTHONHOME/PYTHONPATH`，以 safe-path 模式逐一加载入口。
- `P2-001` 修复：基线摘要改为直接读取 canonical Git blob bytes；工作树是否变更改由 Git diff/clean-filter 语义判定。物理 CRLF/LF 不再改变 pristine checkout 的报告摘要，同时真实 tracked change、删除和新增仍分别 fail closed。
- Manifest 更新：Accepted roots 仍是 baseline `9fe4c4453af1525a6a47adc856575a70c8437911` 的同一 `100/100` 文件，未修改任何 Accepted artifact；仅将 guard 的记录摘要更新为 canonical blob root `830e6ebc359a41916e6b9d8a840f1f0799afd6698db270711f77e584feb9bdf5`。
- 验证：artifact guard 与 launcher 定向 `11/11`、完整集成 Python `28/28`、Dashboard backend `130/130`、既有 workflow `85/85`、当前真实项目三个合同视口 Chrome `3/3` 均通过；单 TASK workflow lint 为 `0 error / 0 violation / 1 expected uncommitted-history warning`。
- 边界复核：Accepted roots 相对 `9fe4c44` 的 Git diff 为零，artifact guard 为 canonical `100/100` 且零 missing/changed/added；三个直接文档入口 `--help` 成功；验证退出后 `127.0.0.1:5173/8765` 无监听残留；未新增依赖。
- Campaign progress candidate：两个 closure criteria 已进入 GREEN 候选；无依赖、Accepted roots、scope、外部副作用或 hard-stop 变化，等待 ER-4 独立只读复审。

## Campaign ER-3 收据链补录（2026-07-29）

- 补录性质：仅把 ER-3 当时已存在的冻结 chain、patch manifest 与独立 Review 结果封装为 canonical receipts；不改变 review 结论、不追认新 authority、不消耗新 attempt，也不用于状态晋级。
- Policy 与 chain：`policy_digest=ec3ff867bb72d1a6dcb763b653d528018fc79ece1121e95638071d70da72f2fe`；`repair_chain_digest=e32aa6c7a2bd6035a81da0bea2e69b12ba8de598d721fcf84370b1be7f1b4ae7`；subject/patch manifest=`6efbb511382df975662c28532bd15075e89aa5fe9401266d4caffd5cdcfd6f8f`。
- Review receipt：`review_id=review-er-3`；`reviewer_ref=review:isolated-readonly:019fadcd-25bb-7e82-93e0-c4a3c81ffc6b`；`subject_id=ER-3`；`decision=Needs Fix`；`context_isolated/write_isolated=true/true`；`finding_ids=[DASHBOARD-INTEGRATE-RVW-007-P2-001,DASHBOARD-INTEGRATE-RVW-007-P2-002,DASHBOARD-INTEGRATE-RVW-007-P2-003]`；`receipt_hash=c2cce34a5bb93b579d82462d0ee23767ed94f8b42f76b9f061e245979a6e89b9`。
- Attempt receipt：`attempt_id=ER-3`；`mode=EscalatedRepair`；`gate_decision=EscalatedRepairAllowed`；`previous_receipt_hash=07129543ffae46fe162b15f3a75feb63baa9848abf5844bc71f24f8c7704687a`；`authority_receipt_hash=d88a72bb70e6f1874a0928a086faf40af9a61546ccf1a9c77bdbfaba07c2ee84`；嵌入上述完整 review receipt；`receipt_hash=d9d30f577f621a037f72366e871aea78c9739ead5444186553c74f9898d43e8f`。
- Campaign state receipt：schema=`ai-dev-flow/repair-campaign-state-v1`；`attempt_count=3`；`consecutive_no_progress=0`；`latest_outcome=MeasurableProgress`；`history_head_hash=d9d30f577f621a037f72366e871aea78c9739ead5444186553c74f9898d43e8f`；`latest_review_receipt_hash=c2cce34a5bb93b579d82462d0ee23767ed94f8b42f76b9f061e245979a6e89b9`；`safety_hash=1051bbfa558883f7dc6c4d3377d6a69fbf1ad133fe001aa0f6e6772ae1757a26`；`source_text_sha256=b6f076dd62e7c31375441586c277d215f7175ffef4dfdeaf9438dec530d3d1d7`；`receipt_hash=86e0aa6079c5385b19037f5c85800235d5b1e9a53b4cdcbe58eb43e27dbae30c`。
- Complete canonical campaign-state receipt（以下单行 JSON 是 hash 输入的完整记录，不含隐藏字段）：

```json
{"attempt_count":3,"authority_receipt_hash":"d88a72bb70e6f1874a0928a086faf40af9a61546ccf1a9c77bdbfaba07c2ee84","campaign_id":"DASHBOARD-INTEGRATE-RCAMPAIGN-002","consecutive_no_progress":0,"history_head_hash":"d9d30f577f621a037f72366e871aea78c9739ead5444186553c74f9898d43e8f","latest_outcome":"MeasurableProgress","latest_review_receipt_hash":"c2cce34a5bb93b579d82462d0ee23767ed94f8b42f76b9f061e245979a6e89b9","receipt_hash":"86e0aa6079c5385b19037f5c85800235d5b1e9a53b4cdcbe58eb43e27dbae30c","safety_hash":"1051bbfa558883f7dc6c4d3377d6a69fbf1ad133fe001aa0f6e6772ae1757a26","schema_version":"ai-dev-flow/repair-campaign-state-v1","source_ref":"task:docs/tasks/DASHBOARD-INTEGRATE-001.md#repair-campaign-state","source_text_sha256":"b6f076dd62e7c31375441586c277d215f7175ffef4dfdeaf9438dec530d3d1d7"}
```

## Campaign ER-4 独立 Review（2026-07-29）

- Reviewer：原生 `codex exec review --uncommitted`，session `019faddc-3aa2-79a1-8dde-dcecb6c8c796`，sandbox=`read-only`；冻结输入 27 文件 manifest SHA256 `0266ce19be8c164f9893a5441bdcc205302b755ad86b28dfad8f2745cc1dbf10`，最终消息 SHA256 `4ed8e5e64e4110d4e3062a752c36693950a2d1ba6ab65a796fe79f631edd6f4d`。
- 结论：`Needs Fix`；`P0/P1/P2/P3=0/2/1/0`。ER-3 的 direct-entry 与 `core.autocrlf` 两项均未重新开放，但出现两个新的 blocking findings，因此本轮保守记录为 `NoProgress`，不允许进入 UA6。
- `DASHBOARD-INTEGRATE-RVW-009-P1-001`：ER-4 promotion 之前缺少 ER-3 review/attempt/campaign-state canonical receipts，Campaign 当前状态无法无猜测验证。
- `DASHBOARD-INTEGRATE-RVW-009-P1-002`：artifact guard 只比较 baseline 与工作树；若受保护文件已暂存修改、工作树又恢复为 baseline，门禁可能错误返回 GREEN。
- `DASHBOARD-INTEGRATE-RVW-009-P2-001`：TASK_BOARD 仍写“待完整验证”，但 TASK 已记录完整验证通过，投影不准确。
- Review receipt：`review_id=review-er-4`；`reviewer_ref=review:isolated-readonly:019faddc-3aa2-79a1-8dde-dcecb6c8c796`；`subject_id=ER-4`；subject/patch manifest=`0266ce19be8c164f9893a5441bdcc205302b755ad86b28dfad8f2745cc1dbf10`；`decision=Needs Fix`；`context_isolated/write_isolated=true/true`；`finding_ids=[DASHBOARD-INTEGRATE-RVW-008-P1-001,DASHBOARD-INTEGRATE-RVW-008-P2-001]`；`policy_digest=ec3ff867bb72d1a6dcb763b653d528018fc79ece1121e95638071d70da72f2fe`；`repair_chain_digest=afe2ef911370bae7e56624081958a257d896361faf771618ea23e56d0c40fd9c`；`receipt_hash=eb10603d9165bc140e895fa810d13a895aab06c51dc12cb8d0ccb774a890c259`。
- Attempt receipt：`attempt_id=ER-4`；`mode=EscalatedRepair`；`gate_decision=EscalatedRepairAllowed`；`previous_receipt_hash=d9d30f577f621a037f72366e871aea78c9739ead5444186553c74f9898d43e8f`；`authority_receipt_hash=d88a72bb70e6f1874a0928a086faf40af9a61546ccf1a9c77bdbfaba07c2ee84`；嵌入上述完整 review receipt；`receipt_hash=b536e17553be1246a74e0b86c89a5b880e23757ee82e88ac6cf4c9da966e7ef8`。
- Campaign state receipt：schema=`ai-dev-flow/repair-campaign-state-v1`；`attempt_count=4`；`consecutive_no_progress=1/4`；`latest_outcome=NoProgress`；`history_head_hash=b536e17553be1246a74e0b86c89a5b880e23757ee82e88ac6cf4c9da966e7ef8`；`latest_review_receipt_hash=eb10603d9165bc140e895fa810d13a895aab06c51dc12cb8d0ccb774a890c259`；`safety_hash=1051bbfa558883f7dc6c4d3377d6a69fbf1ad133fe001aa0f6e6772ae1757a26`；`source_text_sha256=81ba63a8eed3c25985d146777a2d0b268dd09be80fbeebf2fedd4039fd7b5cbc`；`receipt_hash=995a1726e9ae3e0aab0340b7616c1f8c1a07c8e1f70701cff571065b91d40b35`；全部 hard-stop flags 仍为 false。
- Complete canonical campaign-state receipt（以下单行 JSON 是 ER-5 promotion 依赖的完整记录）：

```json
{"attempt_count":4,"authority_receipt_hash":"d88a72bb70e6f1874a0928a086faf40af9a61546ccf1a9c77bdbfaba07c2ee84","campaign_id":"DASHBOARD-INTEGRATE-RCAMPAIGN-002","consecutive_no_progress":1,"history_head_hash":"b536e17553be1246a74e0b86c89a5b880e23757ee82e88ac6cf4c9da966e7ef8","latest_outcome":"NoProgress","latest_review_receipt_hash":"eb10603d9165bc140e895fa810d13a895aab06c51dc12cb8d0ccb774a890c259","receipt_hash":"995a1726e9ae3e0aab0340b7616c1f8c1a07c8e1f70701cff571065b91d40b35","safety_hash":"1051bbfa558883f7dc6c4d3377d6a69fbf1ad133fe001aa0f6e6772ae1757a26","schema_version":"ai-dev-flow/repair-campaign-state-v1","source_ref":"task:docs/tasks/DASHBOARD-INTEGRATE-001.md#repair-campaign-state","source_text_sha256":"81ba63a8eed3c25985d146777a2d0b268dd09be80fbeebf2fedd4039fd7b5cbc"}
```

## Campaign ER-5 候选（2026-07-29）

- Orchestrator promotion：ER-3/ER-4 receipts 与当前 Campaign state 已先行冻结；`consecutive_no_progress=1/4` 尚未触发 core-product hard limit，且 hard-stop flags 全 false，因此同一 task-bound authority 允许 `next_attempt_id=ER-5 / EscalatedRepairAllowed`。
- 新 chain：`repair_chain_id=DASHBOARD-INTEGRATE-RC-009`；target findings 为 ER-4 的三个 IDs；`closure_contract_hash=af02dab1cc5d8b667bf111165bcbfdc66a701df9e079f7c5c14a2dcb7cfeee21`；`allowed_files_hash=28ca366b3d525c882112992b8cc97a3c6f8cb94c46e3c35163f45cd2cdaa6176`；canonical `repair_chain_digest=204ab196e8909f7fed9631be1fe5a9a3e06688690433eb0e476ed9a9fcf0b919`。
- ER-5 exact allowed files：`dashboard/integration/artifact_guard.py`、`dashboard/integration/tests/test_artifact_guard.py`、`docs/TASK_BOARD.md`、`docs/tasks/DASHBOARD-INTEGRATE-001.md`。
- Closure vector：ER-3/ER-4 receipt chain 可按 canonical JSON 规则复算；artifact guard 对 index 或 worktree 任一偏离都 fail closed；TASK_BOARD 准确投影“完整验证已通过、ER-4 Review Needs Fix、ER-5 修复待复审”。
- 验证：staged-index 专项复现与 artifact guard 定向 `4/4`、完整集成 Python `29/29`、当前真实项目三个合同视口 Chrome `3/3`、artifact canonical `100/100`、单 TASK workflow lint `0 error / 0 violation / 1 expected uncommitted-history warning`、`git diff --check` 全部通过；receipt hashes 使用当前 `repair_gate.py` 的 canonical hash/receipt hash 实现复算一致。
- 状态边界：`Needs Fix / Review Needs Fix / UA6 Pending / Uncommitted / Unmerged`；等待 ER-5 独立只读复审。

## Campaign ER-5 独立 Review（2026-07-29）

- Reviewer：原生 `codex exec review --uncommitted`，session `019fadeb-7ee8-73e1-b639-e7b1a0b47502`，sandbox=`read-only`；冻结输入 27 文件 manifest SHA256 `d6c2b1e819a0e1d92f084982eaa34afaf81e1e411117dbe2740f8ea9c0224d1f`，最终消息 SHA256 `f1706cc52a01d0e233cc27de0634e798850a013c70b476ae324f1895f3e067d1`。
- 结论：`Needs Fix`；`P0/P1/P2/P3=0/1/2/0`。ER-4 的 index 暂存差异和看板投影 findings 未重新开放；由于 complete canonical state 仍需补齐且出现两个新 cleanup/integrity findings，本轮记录为 `NoProgress`，不允许进入 UA6。
- `DASHBOARD-INTEGRATE-RVW-010-P1-001`：ER-4 campaign-state 只以 prose 列出部分字段，缺 `source_ref`、`campaign_id`、`authority_receipt_hash`，不能无猜测复算 receipt。
- `DASHBOARD-INTEGRATE-RVW-010-P2-001`：受保护文件若设置 `assume-unchanged` 或 `skip-worktree` 后被修改，两次 Git diff 均可能隐藏路径，guard 会错误覆盖 raw mismatch。
- `DASHBOARD-INTEGRATE-RVW-010-P2-002`：root process 已退出时 tree helper 提前返回，Git/esbuild 等仍存活的后代可能残留。
- Review receipt：`review_id=review-er-5`；`reviewer_ref=review:isolated-readonly:019fadeb-7ee8-73e1-b639-e7b1a0b47502`；`subject_id=ER-5`；subject/patch manifest=`d6c2b1e819a0e1d92f084982eaa34afaf81e1e411117dbe2740f8ea9c0224d1f`；`decision=Needs Fix`；`context_isolated/write_isolated=true/true`；`repair_chain_digest=204ab196e8909f7fed9631be1fe5a9a3e06688690433eb0e476ed9a9fcf0b919`；`policy_digest=ec3ff867bb72d1a6dcb763b653d528018fc79ece1121e95638071d70da72f2fe`；`receipt_hash=ffc93a80ebca3519df312715745913607c2cd743330b0dec1026d490bf8578e9`。
- Attempt receipt：`attempt_id=ER-5`；`mode=EscalatedRepair`；`gate_decision=EscalatedRepairAllowed`；`previous_receipt_hash=b536e17553be1246a74e0b86c89a5b880e23757ee82e88ac6cf4c9da966e7ef8`；`authority_receipt_hash=d88a72bb70e6f1874a0928a086faf40af9a61546ccf1a9c77bdbfaba07c2ee84`；嵌入上述 review receipt；`receipt_hash=c6320a5562fb17120fe7f258591c766bfea598c68bd334fc84091fc384a1eb1d`。
- Complete canonical campaign-state receipt：

```json
{"attempt_count":5,"authority_receipt_hash":"d88a72bb70e6f1874a0928a086faf40af9a61546ccf1a9c77bdbfaba07c2ee84","campaign_id":"DASHBOARD-INTEGRATE-RCAMPAIGN-002","consecutive_no_progress":2,"history_head_hash":"c6320a5562fb17120fe7f258591c766bfea598c68bd334fc84091fc384a1eb1d","latest_outcome":"NoProgress","latest_review_receipt_hash":"ffc93a80ebca3519df312715745913607c2cd743330b0dec1026d490bf8578e9","receipt_hash":"1da13e46c3d135e0d48259124d9767dd2c6b06eb009b26f92213cb34d01f630a","safety_hash":"1051bbfa558883f7dc6c4d3377d6a69fbf1ad133fe001aa0f6e6772ae1757a26","schema_version":"ai-dev-flow/repair-campaign-state-v1","source_ref":"task:docs/tasks/DASHBOARD-INTEGRATE-001.md#repair-campaign-state","source_text_sha256":"9c6268562b1bbdc9f83181e0518845830dbd9061f67bceedbc14eb7ae3a5a16e"}
```

## Campaign ER-6 候选（2026-07-29）

- Orchestrator promotion：ER-5 complete canonical state 已先行冻结；`consecutive_no_progress=2/4` 未触发 core-product hard limit，且 hard-stop flags 全 false，因此同一 task-bound authority 允许 `next_attempt_id=ER-6 / EscalatedRepairAllowed`。
- 新 chain：`repair_chain_id=DASHBOARD-INTEGRATE-RC-010`；target findings 为 ER-5 的三个 IDs；`closure_contract_hash=37cd1c9b4bab14e56e47f9491a2f35bfbf711b5a45a4f545f83593b595b333ba`；`allowed_files_hash=f57df79c9d0dbd64e1d5fc88b2792d33efdf8b876ad2653dd2b690b6c1061073`；canonical `repair_chain_digest=cefd7963cef5e6ff19ccd1e8a4c4f38c6a57b411ce8556763a91e4fb684c8829`。
- ER-6 exact allowed files：`dashboard/integration/artifact_guard.py`、`dashboard/integration/benchmark.py`、`dashboard/integration/launcher.py`、`dashboard/integration/process_tree.py`、`dashboard/integration/state_matrix.py`、`dashboard/integration/tests/test_artifact_guard.py`、`dashboard/integration/tests/test_benchmark.py`、`dashboard/integration/tests/test_launcher.py`、`dashboard/integration/tests/test_process_tree.py`、`dashboard/integration/tests/test_real_stack.py`、`dashboard/integration/tests/test_state_matrix_runner.py`、`docs/TASK_BOARD.md`、`docs/tasks/DASHBOARD-INTEGRATE-001.md`。
- `P1-001` 修复：ER-3、ER-4、ER-5 state 均记录完整 canonical JSON；字段集合与当前 `repair_gate.py` 的 `ai-dev-flow/repair-campaign-state-v1` 一致，可直接移除 `receipt_hash` 后复算。
- `P2-001` 修复：除 index/worktree Git diff 外，对每个 protected path 直接执行带 `--path` clean filter 的 `git hash-object` 并与 base blob OID 比较；不信任 index flags，同时保持合法 CRLF/LF checkout 等价。
- `P2-002` 修复：每个 Windows child 启动后立即绑定独立 Job Object 并保留 handle，设置 `KILL_ON_JOB_CLOSE`；cleanup 无论 root 是否已退出都终止并关闭 job。POSIX 同样在启动时保留 process-group ID，不再依赖 root 存活时查询。
- 验证：隐藏 index flags、staged index、EOL canonicalization、Job Object root-exited cleanup、launcher/benchmark/state-matrix cleanup 定向 `27/27`，完整集成 Python `32/32`，当前真实项目三个合同视口 Chrome `3/3`，artifact canonical `100/100`，单 TASK workflow lint `0 error / 0 violation / 1 expected uncommitted-history warning`，`git diff --check` 全部通过。
- 状态边界：`Needs Fix / Review Needs Fix / UA6 Pending / Uncommitted / Unmerged`；等待 ER-6 独立只读复审。

## Campaign ER-6 独立 Review（2026-07-29）

- Reviewer：原生 `codex exec review --uncommitted`，session `019fadfc-4a0e-7630-97c5-84935b0458c6`，sandbox=`read-only`；冻结输入 27 文件 manifest SHA256 `f66072b6096703b18308ad0f36e1b5a280d1c386b70923a6d8fcead204ad50b3`，最终消息 SHA256 `a460159461ec38d6b5dc38972cba7349eb2fea1972e5e496af264fc4ae23ddeb`。
- 结论：`Needs Fix`；`P0/P1/P2/P3=0/0/3/0`。ER-5 的完整 campaign-state、隐藏 index flags 与 root-exited tree cleanup 三项均未重新开放；blocking findings 降至零且 evidence vector 增长，本轮记录为 `MeasurableProgress`，但仍不允许进入 UA6。
- `DASHBOARD-INTEGRATE-RVW-011-P2-001`：Windows child 先运行后 Assign Job 存在竞态；快速后代可能在绑定前生成且不会被追溯加入 Job。
- `DASHBOARD-INTEGRATE-RVW-011-P2-002`：真实栈 `urllib.request.urlopen` 受环境代理影响，缺少 `NO_PROXY` 时本地请求可能被发送到代理。
- `DASHBOARD-INTEGRATE-RVW-011-P2-003`：真实文件更新只检查 revision/lifecycle，未断言 successor ETag 变化和 SSE `changed_task_ids`。
- Review receipt：`review_id=review-er-6`；`reviewer_ref=review:isolated-readonly:019fadfc-4a0e-7630-97c5-84935b0458c6`；`subject_id=ER-6`；subject/patch manifest=`f66072b6096703b18308ad0f36e1b5a280d1c386b70923a6d8fcead204ad50b3`；`decision=Needs Fix`；`repair_chain_digest=cefd7963cef5e6ff19ccd1e8a4c4f38c6a57b411ce8556763a91e4fb684c8829`；`policy_digest=ec3ff867bb72d1a6dcb763b653d528018fc79ece1121e95638071d70da72f2fe`；`receipt_hash=e6acbf25c6215e596f20ac701be77c00c2c4563c681537fe77ff4b15e2825a82`。
- Attempt receipt：`attempt_id=ER-6`；`mode=EscalatedRepair`；`gate_decision=EscalatedRepairAllowed`；`previous_receipt_hash=c6320a5562fb17120fe7f258591c766bfea598c68bd334fc84091fc384a1eb1d`；`authority_receipt_hash=d88a72bb70e6f1874a0928a086faf40af9a61546ccf1a9c77bdbfaba07c2ee84`；`receipt_hash=e0db556dd5e4645335d1341feb4a0340d78955f042eb4a0e045dd6ffb34eac83`。
- Complete canonical campaign-state receipt：

```json
{"attempt_count":6,"authority_receipt_hash":"d88a72bb70e6f1874a0928a086faf40af9a61546ccf1a9c77bdbfaba07c2ee84","campaign_id":"DASHBOARD-INTEGRATE-RCAMPAIGN-002","consecutive_no_progress":0,"history_head_hash":"e0db556dd5e4645335d1341feb4a0340d78955f042eb4a0e045dd6ffb34eac83","latest_outcome":"MeasurableProgress","latest_review_receipt_hash":"e6acbf25c6215e596f20ac701be77c00c2c4563c681537fe77ff4b15e2825a82","receipt_hash":"00673c665f1e30ae14a33ef1480a5d1969e41b5d56b98d007339ce1f9995c04e","safety_hash":"1051bbfa558883f7dc6c4d3377d6a69fbf1ad133fe001aa0f6e6772ae1757a26","schema_version":"ai-dev-flow/repair-campaign-state-v1","source_ref":"task:docs/tasks/DASHBOARD-INTEGRATE-001.md#repair-campaign-state","source_text_sha256":"ca2a5b87b8ca92b9dd601e37cdfe62cbbd9931b8f3d861b3f4181cd1333011b8"}
```

## Campaign ER-7 候选（2026-07-29）

- Orchestrator promotion：ER-6 complete canonical state 已冻结；`consecutive_no_progress=0/4` 且 hard-stop flags 全 false，同一 task-bound authority 允许 `next_attempt_id=ER-7 / EscalatedRepairAllowed`。
- 新 chain：`repair_chain_id=DASHBOARD-INTEGRATE-RC-011`；target findings 为 ER-6 的三个 P2；`closure_contract_hash=48eef1ebad73ddb9f2a22350aa943d170b3f5c1919f1bfa4ea92cb8ce6bf266b`；`allowed_files_hash=ffd6281b98e09fff84073f7e1ef1f06153c624cc301d2fb56995f8e7534e0c9d`；canonical `repair_chain_digest=ba20d70ca3d4e722a4d9d4fe66333c0a8019c9fd3970087390ad85f3068a2474`。
- ER-7 exact allowed files：`dashboard/integration/process_tree.py`、`dashboard/integration/tests/test_process_tree.py`、`dashboard/integration/tests/test_real_stack.py`、`docs/TASK_BOARD.md`、`docs/tasks/DASHBOARD-INTEGRATE-001.md`。
- `P2-001` 修复：Windows `Popen` 统一带 `CREATE_SUSPENDED`；`track_process_tree()` 先创建/配置 Job、Assign root，再枚举该 PID 的 suspended thread 并 Resume。任一步失败都会关闭/终止 Job 并 fail closed，不留未跟踪 child。
- `P2-002` 修复：真实栈所有 urllib loopback 请求统一使用 `ProxyHandler({})` opener，并增加无 proxy handler 的合同断言；直连 Host allowlist 与 SSE 仍使用显式 `127.0.0.1` socket。
- `P2-003` 修复：更新轮询携带首次 ETag 的 `If-None-Match`，成功后断言 successor ETag 不同；再以首次 revision 作为 `Last-Event-ID` 连接真实 frontend→backend SSE，断言 `reset_required=false` 且 `changed_task_ids` 包含 `STACK-001`。
- 验证：suspended→assign→resume、proxy-disabled opener、successor ETag/SSE 定向 `7/7`，完整集成 Python `34/34`，当前真实项目三个合同视口 Chrome `3/3`，artifact canonical `100/100`，单 TASK workflow lint `0 error / 0 violation / 1 expected uncommitted-history warning`，`git diff --check` 全部通过。
- 状态仍为 `Needs Fix / Review Needs Fix / UA6 Pending / Uncommitted / Unmerged`；等待 ER-7 独立只读复审。

## Campaign ER-7 独立 Review 与可验收收据（2026-07-29）

- Reviewer：原生 `codex exec review --uncommitted`，session `019fae0e-4f28-7ad1-b7d8-871609190eb4`，sandbox=`read-only`；冻结输入 27 文件 manifest SHA256 `1b592aa144896e65de18828c7498fe4c9ba2f1f61441410a5962efe0ea5321ed`，最终消息 SHA256 `81a4e7fc0fd406546157f5642e6103f08779b8767362dd4cf38bf94825b8e6f7`。
- 结论：`Passed`；`P0/P1/P2/P3=0/0/0/0`。Reviewer 明确“未发现明确且可操作的正确性、安全性或回归问题”；只读 sandbox 无法创建临时目录导致其不能完整复跑集成测试，属于 Reviewer 环境限制，不是补丁缺陷；repairer 可写隔离环境的同一冻结候选 `34/34` 证据仍有效。
- ER-6 三个 P2 全部关闭：Windows child 在 Resume 前绑定 Job；loopback urllib 绕过环境代理；真实 successor 同时验证 ETag 与 SSE changed IDs。
- Review receipt：`review_id=review-er-7`；`reviewer_ref=review:isolated-readonly:019fae0e-4f28-7ad1-b7d8-871609190eb4`；`subject_id=ER-7`；subject/patch manifest=`1b592aa144896e65de18828c7498fe4c9ba2f1f61441410a5962efe0ea5321ed`；`decision=Passed`；`context_isolated/write_isolated=true/true`；`repair_chain_digest=ba20d70ca3d4e722a4d9d4fe66333c0a8019c9fd3970087390ad85f3068a2474`；`policy_digest=ec3ff867bb72d1a6dcb763b653d528018fc79ece1121e95638071d70da72f2fe`；`receipt_hash=a4b7de5d1249e48c080989f84d9fae77659be19a738f6a470470c13c6cc980e9`。
- Attempt receipt：`attempt_id=ER-7`；`mode=EscalatedRepair`；`gate_decision=EscalatedRepairAllowed`；`previous_receipt_hash=e0db556dd5e4645335d1341feb4a0340d78955f042eb4a0e045dd6ffb34eac83`；`authority_receipt_hash=d88a72bb70e6f1874a0928a086faf40af9a61546ccf1a9c77bdbfaba07c2ee84`；`receipt_hash=5634ae027cc2c3848b0290652fbd04de8c6621fe7750859a8d211fe6ddc6a255`。
- Complete canonical campaign-state receipt：

```json
{"attempt_count":7,"authority_receipt_hash":"d88a72bb70e6f1874a0928a086faf40af9a61546ccf1a9c77bdbfaba07c2ee84","campaign_id":"DASHBOARD-INTEGRATE-RCAMPAIGN-002","consecutive_no_progress":0,"history_head_hash":"5634ae027cc2c3848b0290652fbd04de8c6621fe7750859a8d211fe6ddc6a255","latest_outcome":"MeasurableProgress","latest_review_receipt_hash":"a4b7de5d1249e48c080989f84d9fae77659be19a738f6a470470c13c6cc980e9","receipt_hash":"1759069a466fd73b4d6c380ec3e231edc1026453be47a2d265dfb175cf3ada84","safety_hash":"1051bbfa558883f7dc6c4d3377d6a69fbf1ad133fe001aa0f6e6772ae1757a26","schema_version":"ai-dev-flow/repair-campaign-state-v1","source_ref":"task:docs/tasks/DASHBOARD-INTEGRATE-001.md#repair-campaign-state","source_text_sha256":"d660cb6096dc18599449c8a1626f0c1429bb90721e286daa083d9a5f3fbe8479"}
```

- 最终状态边界：`Review / Review Passed / UA6 Pending / Uncommitted / Unmerged`；未 Accepted、未 commit、未 merge、未 push、未 release、未 Closed。下一步仅允许用户执行 UA6；后续状态与交付动作必须另行授权。
