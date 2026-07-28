# DASHBOARD-BE-002：实现 Git 快照、本地只读 API 与实时更新

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `DASHBOARD-BE-002`
- `task_type`: `code`
- `task_class`: `D`
- `lifecycle`: `In Progress`
- `review_status`: `Pending`
- `ua_level`: `UA3`
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
- `write_scope`: `file:dashboard/backend/src/ai_dev_flow_dashboard/__main__.py;dir:dashboard/backend/src/ai_dev_flow_dashboard/git_snapshot;dir:dashboard/backend/src/ai_dev_flow_dashboard/server;dir:dashboard/backend/src/ai_dev_flow_dashboard/snapshot;dir:dashboard/backend/tests/be002`
- `module_locks`: `dashboard-api;dashboard-backend;dashboard-git;dashboard-snapshot`
- `worktree`: `required`
- `branch_hint`: `codex/dashboard-be-002`
- `risk_flags`: `core_execution_path;public_api;security;shared_component`

## 目标与边界

- 目标：把 `DASHBOARD-BE-001` 的纯领域核心接入真实本地 TASK、TASK_BOARD、Git 和 linked Worktree，原子生成 `fresh / stale / partial` DashboardSnapshot。
- 目标：提供只绑定本机的只读 HTTP/SSE 服务，使前端可以获取完整快照、任务详情、健康状态和 revision 变更通知。
- 非目标：不修改项目事实源，不提供写接口或执行按钮，不实现前端布局，不构建数据库、远程服务、遥测、认证系统或自动调度器。
- 非目标：不改变 `dashboard/contracts/**` 已验收 schema；如实现发现合同不足，停止并返回 `DASHBOARD-BE-001` / `DASHBOARD-001` 重新 Review。
- 允许修改：未来执行时仅限 `dashboard/backend/src/ai_dev_flow_dashboard/__main__.py`、`dashboard/backend/src/ai_dev_flow_dashboard/git_snapshot/**`、`dashboard/backend/src/ai_dev_flow_dashboard/server/**`、`dashboard/backend/src/ai_dev_flow_dashboard/snapshot/**`、`dashboard/backend/tests/be002/**`、`docs/tasks/DASHBOARD-BE-002.md` 和该任务在 `docs/TASK_BOARD.md` 的投影行。
- 禁止修改：`skills/ai-dev-flow/**`、`dashboard/frontend/**`、`dashboard/contracts/**`、`dashboard/backend/pyproject.toml`、`dashboard/backend/src/ai_dev_flow_dashboard/__init__.py`、`dashboard/backend/src/ai_dev_flow_dashboard/core/**`、`dashboard/backend/tests/be001/**`、其他 TASK、版本/发布文件和本机 Skill；禁止新增依赖或改变安全边界，除非用户另行明确授权。实现发现上述只读基线需要修改时必须停止，并返回 `DASHBOARD-BE-001` 重新 Review。

## 实施合同

### 固定目录责任

- `dashboard/backend/src/ai_dev_flow_dashboard/git_snapshot/**`：Git/Worktree 只读命令执行、解析和 provenance。
- `dashboard/backend/src/ai_dev_flow_dashboard/snapshot/**`：watcher、冻结输入协调、last-known-good 和 revision 发布。
- `dashboard/backend/src/ai_dev_flow_dashboard/server/**`：loopback HTTP/SSE、安全 header、路由和静态资源边界。
- `dashboard/backend/src/ai_dev_flow_dashboard/__main__.py`：最小本地启动入口，只负责装配上述模块。
- `dashboard/backend/tests/be002/**`：本任务 Git、snapshot、HTTP/SSE、安全和性能测试。

### Git / Worktree 只读采集

- Git 只能使用参数数组调用 `DASHBOARD-001` 冻结的 `rev-parse`、`worktree list --porcelain -z` 和 `status --porcelain=v1 -z` 命令族；不得经过 shell。
- 每条命令 5 秒超时，严格解析 UTF-8 与 NUL 分隔；timeout、非零退出、decode error 和 capability 不足映射为稳定 diagnostic。
- 收集 root、HEAD、branch、detached、locked、prunable、dirty paths 和任务 branch/worktree 映射。
- rename/copy 双路径、submodule、Unicode/空格路径、linked Worktree `.git` 文件和 dirty ownership 必须有测试。
- 禁止 checkout、switch、stash、clean、reset、commit、merge、push、worktree add/remove 或删除。

### Snapshot Coordinator

- 每次刷新在后台构建完整不可变候选；Core Reader、Scheduling、TASK_BOARD 和 Git 输入全部验证后才原子替换当前 revision。
- 保存事件使用 200ms trailing debounce，连续事件最多 1 秒强制构建；临时文件不进入 manifest。
- 有 last-known-good 时，当前解析失败必须发布包含当前 diagnostic/digest 的 `stale`；首次失败发布 `partial`。
- `changed_task_ids` 比较 TaskNode、相邻 edges、actions 和 pair assessments；不得只按文件名猜变化。
- watcher 和 last-known-good 只在进程内存中存在，不成为事实源。

### 本地 HTTP / SSE

- 实现 `GET /api/v1/snapshot`、`GET /api/v1/tasks/{task_id}`、`GET /api/v1/health`、`GET /api/v1/events`，响应必须通过 `dashboard/contracts/**` 的同一 strict validator。
- 支持 canonical revision、`ETag: "sha256-<revision>"`、`If-None-Match`、304、固定 error envelope 和已冻结 HTTP 状态。
- SSE 实现初连、`Last-Event-ID`、reset、直接后继 revision、15 秒 heartbeat、2 秒 retry、慢客户端断开和重连语义。
- SSE 只做失效通知；客户端仍需重新 GET snapshot，不在 event stream 中复制或拼接完整状态。

### 本地安全

- 默认只绑定 `127.0.0.1`；禁止 `0.0.0.0`、非本机暴露和 CORS。
- Host allowlist、CSP、nosniff、no-referrer、固定静态/API 路由、path traversal 和 method allowlist 必须有反例测试。
- 不读取 `.env`、密钥、证书、用户目录或项目根外路径；不记录 TASK 全文、环境变量、命令行或堆栈到外部日志。
- 优先使用 Python 标准库；若必须增加 HTTP/watcher 等第三方依赖，立即 Stop，提交依赖理由、体积、许可证和无依赖替代方案，等待用户确认。

## 依赖与授权

- 前置依赖：`DASHBOARD-BE-001` 必须达到 `Review Passed / UA3 Passed / Accepted`，共享 schema/validator/fixtures 已形成可引用 Git baseline。
- Base commit：规划基线为 `fb16bc50f02023aad4a51acd8bf495231fe65f63`；实际实施必须基于 `DASHBOARD-BE-001` Accepted commit 重新冻结。
- 已有 authority：允许本 TASK 实施合同的独立 Review、有限 repair、Ready 写回与规划提交。
- 未授权动作：代码实现、依赖安装、启动监听服务、Worktree/分支创建、commit、merge、push、release、外部同步和 Closed。
- 执行位置：未来必须使用独立 Worktree 与 `codex/dashboard-be-002` 分支；可与 `DASHBOARD-FE-001` 候选并行，但两者不得写同一业务路径。

## 路由与风险

- 路由：`Controlled`。
- Policy 输入：`task_class=D`、`ua_level=UA3`、风险包含 `core_execution_path`、`public_api`、`security`、`shared_component`；当前无 execution authority。
- Reviewer 闸门：`Required`；TASK 合同进入 Ready 前和代码进入验收建议前均需隔离、只读 Review。
- 主要风险：Git 命令注入、误写 Worktree、本地服务暴露、半更新快照、stale 数据伪装 fresh、SSE 丢 revision、错误详情泄露路径或敏感信息。
- 停止条件：需要写入 TASK/Git；需要公网/CORS/认证；需要改变共享 schema；需要未授权依赖；无法证明进程退出后可完全重建。

## 完成标准与验证

- 完成标准：Git/Worktree 快照只读、可降级且所有未知证据保持 `unknown`。
- 完成标准：原子 snapshot、last-known-good、revision、ETag、HTTP 和 SSE 与冻结合同一致。
- 完成标准：服务仅绑定 loopback，没有写接口、CORS、项目外读取或外部日志。
- 完成标准：50/200、500/2000 与 1000/4000 fixtures 均可运行；500/2000 达到规划中的首版性能门禁。
- 验证命令或检查：执行 `python -B -X utf8 -m unittest discover -s dashboard/backend/tests -p "test_*.py" -v`。
- 验证命令或检查：运行只读 Git fixture、HTTP/SSE transcript、安全反例、稳定保存到 revision 与 30 样本性能协议。
- 验证命令或检查：运行 `python skills/ai-dev-flow/scripts/workflow_lint.py docs/tasks/DASHBOARD-BE-002.md --format json`。
- [ ] 验证所有 Git 调用均为参数数组且命令族在 allowlist 内。
- [ ] 验证 405/404/400/503、ETag/304、SSE reset/reconnect/heartbeat 和慢客户端。
- [ ] 验证 loopback/Host/CSP/CORS/path traversal/项目外路径/敏感值边界。
- [ ] 机器检查 implementation diff 只命中本任务精确 allowlist；`dashboard/contracts/**`、BE-001 core/package foundation 和 `tests/be001/**` 任一变化都必须失败。
- [ ] `git diff --check` 通过，diff 只归属当前 TASK。

## 验收建议

- 用户动作等级：UA3（用户查看自动测试、HTTP/SSE transcript、安全和性能证据）。
- 是否需要用户实机测试：否；真实本地启动与页面联调统一放到 `DASHBOARD-INTEGRATE-001`。
- 不验收的风险：后端可能读取正确但向前端发布过期、半更新或暴露范围过大的数据。
- 是否允许关闭任务：否；当前只是 Ready，尚未实施或验收。

## 四份实施 TASK 初始独立 Review（2026-07-28）

- Reviewer：当前 Codex Harness 的独立 Reviewer 子上下文；仅收到 NTFS `RX` 冻结证据副本，`Workspace writes=None`。
- 冻结输入：本 TASK SHA256 `7C5715574CD83981CC7225A6E9A47EA1C331A257FC937B6A80CCEC77B31024C9`；基线 `main@fb16bc50f02023aad4a51acd8bf495231fe65f63`。
- 结论：`Needs Fix`；`P0/P1/P2/P3=0/2/0/0`。
- `DASHBOARD-TASKS-P1-001`：与 FE-001 的候选并行缺少能覆盖默认串行规则的机器可验证例外。
- `DASHBOARD-TASKS-P1-002`：原 `dashboard/backend/**` allowlist 可改写 BE-001 已验收 core 与 package foundation。

## 四份实施 TASK Repair Round 1（2026-07-28）

- `attempt_id`: `DASHBOARD-TASKS-RC-001-A1`
- `repair_chain_id`: `DASHBOARD-TASKS-RC-001`
- `finding_ids`: `DASHBOARD-TASKS-P1-001;DASHBOARD-TASKS-P1-002`
- 修订：前置条件增加 Accepted/Review/UA/Committed 四个正交轴；后端写范围拆为 Git、snapshot、server、启动入口和 `tests/be002`；BE-001 core、contracts 和 foundation 固定只读；增加 diff-scope 拒绝测试。
- GREEN：每项关闭标准均已有确定路径和测试 oracle；是否关闭由下一次独立复审判定。

## 四份实施 TASK 最终独立复审（2026-07-28）

- 冻结输入：本 TASK SHA256 `5B155E46314C1E41360464944E45DF23BD614B3F11797B99ADF1A1CA489753E9`。
- 结论：`Passed`；`DASHBOARD-TASKS-P1-001/002` Closed 且最终复审无回归，无新增 finding；整体 `P0/P1/P2/P3=0/0/0/0`。
- Reviewer 确认：Git、HTTP/SSE、安全、性能、只读边界、精确路径和停止条件足以进入 Ready。
- 状态边界：`Ready / Review Passed / UA3 Pending / Uncommitted / Unmerged`；没有 execution authority。

## 实施启动（2026-07-28）

- 用户授权：用户明确要求“执行 DASHBOARD-BE-002”，授权本 TASK 合同内代码实施、规定 Worktree/分支、自动验证、隔离 Review 和有限 repair。
- 实施基线：`main@760b40442bcc96f711f12433a2c5d017d118d85c`。
- 隔离位置：`D:\open-source\ai-dev-flow-wt\dashboard-be-002`，branch `codex/dashboard-be-002`。
- 冻结写范围：仅限 Git snapshot、snapshot coordinator、server、启动入口、`tests/be002`、本 TASK 和 TASK_BOARD 投影行。
- 状态边界：`In Progress / Review Pending / UA3 Pending / Uncommitted / Unmerged`。

## Outcome

- Base / Diff：base=760b40442bcc96f711f12433a2c5d017d118d85c;diff=working-tree
- 修改文件：计划在冻结 `git_snapshot/**`、`snapshot/**`、`server/**`、`__main__.py` 与 `tests/be002/**` 范围内实施。
- 用户可见行为：待实现 loopback snapshot/task/health/SSE。
- 验证证据：待运行完整回归、Git/HTTP/SSE/security oracle、三档 dataset、性能协议、lint 与 diff/scope 检查。
- Review findings：`Pending`。
- UA 动作与结果：`UA3 Pending`。
- 隔离位置：`D:\open-source\ai-dev-flow-wt\dashboard-be-002`，branch `codex/dashboard-be-002`。
- 回滚方式：独立 Worktree，尚无业务提交。
- 状态边界：`In Progress / Review Pending / UA3 Pending / Uncommitted / Unmerged / Not Pushed / Not Released / Not Closed`。
- 下一步：完成冻结实现和验证后进入独立 Review。