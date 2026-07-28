# DASHBOARD-INTEGRATE-001：集成本地任务仪表盘并完成回归验收

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `DASHBOARD-INTEGRATE-001`
- `task_type`: `test`
- `task_class`: `D`
- `lifecycle`: `Ready`
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
- `depends_on`: `DASHBOARD-BE-001#commit_status=Committed;DASHBOARD-BE-001#lifecycle=Accepted;DASHBOARD-BE-001#review_status=Passed;DASHBOARD-BE-001#ua_status=Passed;DASHBOARD-BE-002#commit_status=Committed;DASHBOARD-BE-002#lifecycle=Accepted;DASHBOARD-BE-002#review_status=Passed;DASHBOARD-BE-002#ua_status=Passed;DASHBOARD-FE-001#commit_status=Committed;DASHBOARD-FE-001#lifecycle=Accepted;DASHBOARD-FE-001#review_status=Passed;DASHBOARD-FE-001#ua_status=Passed`
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
- 已有 authority：允许本 TASK 实施合同的独立 Review、有限 repair、Ready 写回与规划提交。
- 未授权动作：集成实现、依赖安装、启动服务、Worktree/分支创建、commit、merge、push、release、外部同步、删除和 Closed。
- 执行位置：未来必须使用独立集成 Worktree 与 `codex/dashboard-integrate-001` 分支；前置任务合入集成 baseline 后串行执行。

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
- [ ] 前后端 strict contract、所有异常状态和真实 revision 更新通过。
- [ ] 现有 ai-dev-flow tests、dashboard tests、浏览器、可访问性、安全和性能验证通过。
- [ ] 集成前后 Git status 一致，除当前 TASK allowlist 内预期 diff 外无写入。
- [ ] 机器检查 implementation diff 只命中 `dashboard/integration/**`、`dashboard/README.md` 和本任务收据；前置 Accepted artifact hash manifest 完全一致。
- [ ] 隔离、只读 Review 无开放 P0/P1。
- [ ] 用户完成 UA6，确认新流程与典型旧流程均可用。
- [ ] `git diff --check` 通过，diff 只归属当前 TASK。

## 验收建议

- 用户动作等级：UA6（用户在本机运行新仪表盘并回归关键旧 workflow）。
- 是否需要用户实机测试：是。
- 用户需要做什么：启动本地仪表盘，使用真实项目观察关系图和实时更新，再确认现有 workflow_lint/TASK 使用习惯未被破坏。
- agent 已提供的证据：实施时必须包含构建、测试、benchmark、浏览器截图、可访问性、安全、Git 前后状态和独立 Review。
- 不验收的风险：自动证据不能完全替代用户判断关系图是否直观，以及本机真实项目是否保持原工作习惯。
- 是否允许关闭任务：否；当前只是 Ready，尚未实施或验收。

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

- Base / Diff：`base=fb16bc50f02023aad4a51acd8bf495231fe65f63`；当前仅新增任务文档，integration diff 尚不存在。
- 修改文件：`docs/tasks/DASHBOARD-INTEGRATE-001.md` 和 TASK_BOARD 投影；集成文件尚未创建。
- 验证证据：任务文档 targeted lint 为 `errors/violations/warnings=0/0/1`，唯一 warning 是文件尚未形成 Git transition history；Scheduling 为 13/13 字段、引用均存在；TASK_BOARD 无 drift/missing/orphan/parse；链接、范围、whitespace 与敏感值检查通过。
- Review findings：最终独立 Review `Passed`；`DASHBOARD-TASKS-P1-003` Closed，无开放 finding。
- UA 动作与结果：UA6 Pending；用户尚未执行本地回归验收。
- 隔离位置：待三个前置任务 Accepted 且取得 execution authority 后创建独立集成 Worktree。
- 回滚方式：未实施；当前仅可删除本次新建 Draft 文档，但删除仍需用户明确授权。
- 状态边界：Ready / Review Passed / UA6 Pending / Uncommitted / Unmerged；未实施、未 Accepted、未交付、未 Closed。
- 剩余风险：三个前置实现均未开始，当前没有可执行的集成 baseline。
- 下一步：等待三个前置任务 Accepted，并由用户另行授权 execution；本轮不得创建 Worktree 或执行代码。
