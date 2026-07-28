# DASHBOARD-BE-002：实现 Git 快照、本地只读 API 与实时更新

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `DASHBOARD-BE-002`
- `task_type`: `code`
- `task_class`: `D`
- `lifecycle`: `Accepted`
- `review_status`: `Passed`
- `ua_level`: `UA3`
- `ua_status`: `Passed`
- `ua_evidence`: `docs/tasks/DASHBOARD-BE-002.md#dashboard-be-002-ua3-2026-07-28`
- `acceptance_authority`: `User Confirmed`
- `close_authority`: `None`
- `commit_status`: `Committed`
- `merge_status`: `Merged`
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
- 已有 authority：用户于 2026-07-28 明确要求“执行 DASHBOARD-BE-002”，允许在本 TASK 精确 allowlist 内创建规定的 Worktree/分支、实现代码、运行测试以及执行隔离 Review/有限 repair，直到 `Review Passed / UA3 Pending`。
- 验收 authority：用户查看组合修复、验证、独立 Review 与尾延迟风险说明后明确回复“验收通过”；允许记录本 TASK `UA3 Passed / Accepted`。
- 提交与合并 authority：用户在 Accepted 写回后明确回复“提交并合并”；允许提交本任务实现，并与 `DASHBOARD-BE-001-REPAIR-001` 组合后合并到本地 `main`。
- 当前未授权动作：新增第三方依赖、越界修改、push、release、外部同步、删除 Worktree/分支和 Closed。
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
- [x] 验证所有 Git 调用均为参数数组且命令族在 allowlist 内，并固定 `GIT_OPTIONAL_LOCKS=0`。
- [x] 验证 405/404/400/503、ETag/304、SSE reset/reconnect/heartbeat 和慢客户端。
- [x] 验证 loopback/Host/CSP/CORS/path traversal/项目外路径/敏感值边界。
- [x] BE-002 implementation diff 只命中本任务精确 allowlist；BE-001 修复保留在独立 repair Worktree。
- [x] `git diff --check` 通过，diff 按 BE-001 repair 与 BE-002 两个任务隔离。

## 验收建议

- 用户动作等级：UA3（用户查看自动测试、HTTP/SSE transcript、安全和性能证据）。
- 是否需要用户实机测试：否；真实本地启动与页面联调统一放到 `DASHBOARD-INTEGRATE-001`。
- 验收结果：用户已查看证据和尾延迟说明并明确回复“验收通过”；`UA3 Passed / User Confirmed`。
- 是否允许关闭任务：否；当前已 Accepted，但 Closed 仍需独立授权。

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

- 用户授权：用户明确要求“执行 DASHBOARD-BE-002”，授权本 TASK 合同内的代码实施、规定 Worktree/分支创建、自动验证、隔离 Review 和有限 repair。
- 实施基线：`main@760b40442bcc96f711f12433a2c5d017d118d85c`，已包含 `DASHBOARD-BE-001` Accepted/Committed/Merged 基线。
- 隔离位置：`D:\open-source\ai-dev-flow-wt\dashboard-be-002`，分支 `codex/dashboard-be-002`。
- 冻结写范围：仅限本 TASK 明确列出的 Git snapshot、snapshot coordinator、server、启动入口、`tests/be002`、本 TASK 和 TASK_BOARD 投影行。
- 状态边界：`In Progress / Review Pending / UA3 Pending / Uncommitted / Unmerged`；commit、merge、push、release、Accepted 和 Closed 仍未授权。

## 实施阻塞（2026-07-28）

- `blocker_id`: `DASHBOARD-BE-002-BLOCK-001`
- 已形成实现候选：完成只读 Git/linked Worktree 采集、fresh/stale/partial 原子快照、200ms trailing debounce/1s max-wait watcher、loopback HTTP/SSE、严格 wire validation、安全边界和 BE-002 测试。
- 自动验证：dashboard backend 完整回归 `109/109 Passed`；三档 `50/200`、`500/2000`、`1000/4000` dataset 可生成且 digest 可复算；500 TASK API schema validation + serialization 的 30 样本门禁通过。
- 阻塞证据：当前真实项目完整 fresh 构建实测约 `12521 ms`；冻结 `50 TASK / 200 edges` 数据集仅 `DashboardCore.inspect()` 冷核心读取已为 `4899.208 ms`，而冻结 `500/2000` 完整 cold snapshot 的总预算为 `p95 <= 2000 ms`。
- 判断：完整 cold snapshot 必须包含前述 BE-001 核心读取；更小数据集的前置核心阶段已经超过更大数据集的总预算。满足门禁需要修改 `dashboard/backend/src/ai_dev_flow_dashboard/core/**` 的读取/冻结性能或重新 Review 性能合同，均越出本 TASK allowlist。
- `blocker_id`: `DASHBOARD-BE-002-BLOCK-002`
- 合同缺口：规划要求 dirty path 可在唯一 Worktree/branch 映射且完全落入任务 `write_scope` 时形成 `owned_by_task` 证据并允许候选并行；冻结 `WorktreeSnapshot.dirty_state` 只有 `clean / dirty / unknown`，BE-001 `ParallelEngine` 对任何非 `clean` 证据固定返回 `DIRTY_OWNERSHIP_UNKNOWN`。BE-002 无法在不修改 core/schema 的情况下表达真实 ownership，把 dirty 伪装成 clean 又会破坏证据真实性。
- 停止处置：命中“只读基线需要修改时停止并返回 DASHBOARD-BE-001 重新 Review”的合同条件；不越界修改 core/contracts，不把 API/序列化局部 GREEN 写成任务完成，也不进入验收建议或独立最终 Review。
- 恢复条件：为 `DASHBOARD-BE-001` 建立并通过性能与 dirty ownership 合同修复/复审，提供满足 BE-002 cold snapshot、stable save 和 ownership 语义的 Accepted baseline；随后本 TASK 才能从当前实现候选继续完整性能验证和独立 Review。
- 状态边界：`Blocked / Review Pending / UA3 Pending / Uncommitted / Unmerged`；未 Accepted、未提交、未交付、未 Closed。

## 阻塞解除与组合验证（2026-07-28）

- `DASHBOARD-BE-002-BLOCK-001`：由 `DASHBOARD-BE-001-REPAIR-001` A1 的批量 Reader、冻结并发、内容键缓存、候选缓存、watcher 清单索引和线性 changed-task 计算解除；未放宽 2 秒/1 秒/250ms/10MiB 门禁。
- `DASHBOARD-BE-002-BLOCK-002`：BE-001 core/schema 已增加 `clean / owned_by_task / unowned / unknown`，并由唯一 branch/Worktree、canonical `write_scope` 和完整 dirty paths 决定；不确定证据继续 fail closed。
- 自动回归：Python 3.12 组合 dashboard suite `121/121 Passed`；公共 Reader/治理 suite `83/83 Passed`；没有新增第三方依赖。
- 冷启动：同一 `500/2000` dataset SHA256 `3934d0f774c1caa83ffa75d18c48107379847b8cda5e5645f49018c23b559eb0` 连续两组 30 样本，`p95=1771.5024 ms` 与 `1595.1023 ms`。
- 稳定保存：原子 rename 返回到对应 SSE event 写入 loopback socket，30 样本 `p50/p95=712.3870/784.1541 ms`。
- API/体积：strict validation + canonical bytes + ETag + Content-Length，30 样本 `p50/p95=149.2886/167.0993 ms`；payload `2687116 bytes`。
- 原始结果 SHA256：cold-r9 `C4601C53A79B836459B5E5AF4761AD0A7E067B2041674DCB61194854C5F7F48C`；cold-r10 `49E86DB579F1FFEC0EAA9861BEE18B8B96A4B8747446D0976B8148F9549B1200`；stable-r2 `603B9604CB85D0CBD50CFE11066BBEC6D133410A2293DD1C44088EFA75DA16DE`；api-r1 `FF967403984346D18F978CE378EB276668D4683191C8B22FCDE2A0FB6B2E1250`。

## A1 独立代码 Review 与 A2 入口（2026-07-28）

- Reviewer：独立 `codex exec --ephemeral --sandbox read-only`，同时读取本 Worktree 与 BE-001 repair 未提交 diff；未获写权限。
- Decision：`Needs Fix`；`P0/P1/P2/P3=0/8/1/1`；receipt SHA256 `1CA2DB73FB89E93E4C0A40EC85ECF9FF5DC4A2866DE19DB8B45793D328A272F7`。
- 本任务 P1：linked Worktree 纯 unstaged 变化未触发刷新、refresh 后 manifest 重置吞事件、schema 变化未使 candidate cache 失效、缓存/已发布 snapshot 暴露可变 dict、TRACE/CONNECT/未知方法绕过统一安全响应。
- 组合 P1：canonical scope 缓存未随 reparse 拓扑失效、v1 wire 新增 required 字段破坏兼容、公共 Reader Git transition 无 timeout 且非 strict UTF-8。
- A2 closure：为全部 8 个 P1 增加确定 oracle，重跑组合回归与三项 30 样本性能协议，再执行第二次独立只读 Review；A2 后不得自动进入第三轮。
- 状态边界：`Needs Fix / A2 In Progress / UA3 Pending / Uncommitted / Unmerged`。

## A2 修复与最终验证候选（2026-07-28）

- A2 候选为 8 个 A1 P1 增加了确定 oracle：linked Worktree unstaged 变化、refresh 后 source/Git 二次变化、Scheduling topology、schema content cache、公开 snapshot 不可变边界、未知 HTTP method、安全 v1 wire 兼容和 Reader Git timeout/strict UTF-8；最终独立 Review 关闭其中 7 个，v1 wire 兼容仍 Open。
- Git/watcher：周期性只读 Git fingerprint 捕获纯 unstaged 变化；refresh 后 source manifest 或实际候选 Git fingerprint 不一致时保留 pending 并再次刷新，不吞掉竞态保存。
- snapshot/API：candidate key 包含 schema content digest；缓存仅保存进程内 strict-validated canonical payload，公开 `current/refresh/wait` 返回独立对象；HTTP method 保持冻结行为：已知路由不支持的方法返回 405，未知路由返回 404，均带严格 JSON 与安全 header。
- 最终回归：Python 3.12 组合 dashboard suite `128/128 Passed`；公共 Reader/治理 suite `85/85 Passed`；三档 dataset 可运行且 `500/2000` digest 固定为 `3934d0f774c1caa83ffa75d18c48107379847b8cda5e5645f49018c23b559eb0`。
- 最终性能：cold snapshot 两组 `p50/p95=1653.3866/1826.8364 ms`、`1632.2923/1812.1910 ms`；stable save 两组 `760.0730/894.8890 ms`、`739.0891/907.7692 ms`；API serialize 两组 `149.4765/199.9184 ms`、`139.6867/159.3188 ms`；payload 均为 `2673648 bytes`。
- 原始结果 SHA256：cold `23B9330A9AD47B9B295EEF70A449FE3D02002E2CE6C5DAB03A114DD7A3FBC1B2` / `291B13B3A89DFDDCA9C59ACD61D935C086C5CC9C887DB675D7987FC96E51FCC6`；stable `4A3CEDF4F1D1CB18B5171415319FD9A1586E2135B2DD7D6C805A4974E7E514F4` / `69DA03F67C9D7C9C645021CF058F43216A63657E0AF2358127698D6D28092477`；API `6F7E937950F3077BE904EA8270BE9938158022908E3BE6A4A42B186F9FE8763F` / `9B4C41470DE6D4020B3543E626E2A2779F0BF85CFBD6CB5E9D318603E5AB46D0`。
- 状态边界：A2 实现与自动门禁形成了 Review candidate；最终独立 Review 判定 `Needs Fix / Stop`，不得进入 UA3。

## A2 独立 Review 与 Stop（2026-07-28）

- Reviewer：独立只读子任务同时检查本 Worktree 与 BE-001 repair 未提交 diff；审核前后输入 manifest 不变，本 Worktree 为 `58C2002EF75AD51FAD5D0C2BEC83F6FFF80CB62E67575B049BC78BC0BF30F593`，repair 为 `A56621C14F2FA402AEA7E9B0CFD8459BC04B291E2D25DEF30BDA9579C746616E`。
- Decision：`Needs Fix / Stop`；`P0/P1/P2/P3=0/2/2/0`；独立审核回执 `C:\Users\92336\AppData\Local\Temp\dashboard-be-a2-independent-review.final.txt`，SHA256 `BAB89BB40FD80A2C85861FF91982896A8947A80BA663B806A1C0345CE66C35B3`。
- A1 closure：`DASHBOARD-BE-A1-P1-001`～`006` 与 `008` Closed；`DASHBOARD-BE-A1-P1-007` Open。
- P1 `DASHBOARD-BE-A1-P1-007`：公共 `canonical_bytes(dataclass)` 忽略 `wire=False` metadata，仍可把内部 `dirty_ownership` 输出到 canonical payload；冻结 v1 wire 兼容未闭合。
- P1 `DASHBOARD-BE-A2-P1-001`：无环图有 Kahn 快速路径，但环图仍使用递归 Tarjan；1000/1100 节点环触发 `RecursionError`，不能在冻结的 1000 TASK 支持规模内稳定返回确定性环诊断。
- P2 `DASHBOARD-BE-A2-P2-001`：A2 候选文档曾误写未知方法统一 501，现按冻结实现与测试更正为“已知路由 405、未知路由 404”。
- P2 `DASHBOARD-BE-A2-P2-002`：compiled schema validator cache 使用无界强引用，需改为有界 content-digest cache 并增加淘汰测试。
- Review 边界：三次原生 Review 尝试均未形成完整回执，只记为 Review 未完成；上述 Decision 来自随后完成的独立只读审核。
- Stop：A2 是当前授权链最后一轮自动修复。继续处理必须取得绑定 `repair_chain_id=DASHBOARD-BE-BASELINE-RC-001` 与开放 finding IDs 的新 `EscalatedRepair` authority；attempt count 保持 2。

## RepairCampaignAuthority 激活（2026-07-28）

- 用户授权原文：`授权，继续直至可验收为止`；按 policy 记录为任务级连续修复授权，绑定本 TASK、冻结验收合同与外层 scope；不授权 commit、merge、push、release、Accepted 或 Closed。
- Campaign：`campaign_id=DASHBOARD-BE-002-RCAMPAIGN-001`；`profile=core_product`；`acceptance_contract_hash=2fc2863341d8e25b27f81deb372079767d0d073775c84669f6ab5d5f7d439cd8`；`allowed_scope_hash=9d148c410b5bd7a4e58b0a90dc343d14c34bc28fcdf6f8e400ddef9518c0c010`。
- Activation：`repair_chain_digest=2f86621cd9e3f8dac5169ff0ae14e7287d1d9b9f34b175699d03b46de9693441`；`activation_history_head_hash=bab89bb40fd80a2c85861ff91982896a8947a80ba663b806a1c0345ce66c35b3`；A2 后 repair/BE2 manifest 为 `7C71BAEEE526F0E4E61CA4C0AB430F79434C24C54DA20C1B0E7F6CAB9BB7EAD8` / `08E0924106B0902CBF7F006BF0702B3FEC8F4EFC94550AA314A0E1A55298ACA9`。
- Authority receipt：`C:\Users\92336\AppData\Local\Temp\dashboard-be-002-repair-campaign-authority.json`；canonical receipt hash `ff64874bc24ac2b1670a68b874721fe3121ee8e95e79f0be7de3a2778b7c9dcb`；file SHA256 `32A6DA14CCDCF1641323129E92D14C2F7146AC0DABDA16DB96860AC4B4A597A3`。
- Target findings：`DASHBOARD-BE-A1-P1-007`、`DASHBOARD-BE-A2-P1-001`、`DASHBOARD-BE-A2-P2-002`；`closure_contract_hash=d658bb29bbcd13b8fdf4e92ce1ac65278b42d83e65916a681da08ff0c87c70d9`；`allowed_files_hash=5b0ecf08d2d0cf215509d0c6d5c3a6d0c3efaa2ae4f4305711fb4075903c6107`。
- RED/GREEN/SIGNAL：修复 canonical `wire=False`、1000+ 节点环递归和 compiled cache 无界三个 RED；以定向 oracle、完整组合回归、性能双跑和独立只读 Review 证明 GREEN。
- Activation state：`attempt_count=0`、`consecutive_no_progress=0/4`、hard-stop flags 全 false；Orchestrator 已提升为 `EscalatedRepairAllowed / authority_mode=repair_campaign`。ER-1 最终 state 见独立 Review 段。
- 当前状态：`Review / Campaign ER-1 / Review Passed / UA3 Pending / Uncommitted / Unmerged`。

## Campaign ER-1 修复与验证候选（2026-07-28）

- canonical wire：公共 dataclass canonical serialization 复用 `primitive()`，`wire=False` 的 `dirty_ownership` 不再泄漏；完整 v1 snapshot schema、bytes 等价和字段缺失均有直接 oracle。
- Git 内部 fingerprint：为避免公开 wire 修复削弱内部 candidate invalidation，`GitCollection.fingerprint` 显式纳入 ownership；`watch_fingerprint` 与公开 API 仍排除 ownership，原有 watch-path/fingerprint 测试通过。
- 大环图：递归 Tarjan 改为显式栈的迭代 Kosaraju SCC；depends_on/replaces 的 1000 节点环都形成完整、稳定的 cycle diagnostic。
- Schema cache：compiled validator 按真实 content digest/content 寻址并限制为 8 项；32-schema 淘汰 oracle 证明 `currsize=8`。
- RED→GREEN：旧实现上的 canonical bytes mismatch、两类 `RecursionError`、无有界 compiled cache 均被相同定向测试关闭；修复后 `3/3 Passed`。
- 完整回归：Python 3.12 组合 dashboard suite `130/130 Passed`；公共 Reader/治理 suite `85/85 Passed`；没有新增第三方依赖。
- 性能双跑：cold p95=`1460.0747/1418.6262 ms`；stable-save p95=`775.1131/840.7838 ms`；API p95=`140.5135/133.4503 ms`；payload=`2673648 bytes`，均通过 2 秒/1 秒/250ms/10MiB 门禁。
- 性能结果 SHA256：cold `D6397A7F67A038083C3953D5B1A5464CB105A30CF477260B25397870703A0651` / `274CA4AAB1576BDAB521AB475FABDEA2C2D502C2F89CDDF90F9799B770B31B78`；stable `D32BEB7E6F094C9F328641848CACA58F3F66B07FDFDC55675FED9F9DEDD33208` / `7FB5ED50CDF8FBA75ADF987EA0694222BD08627195BF7B84AFF770D0BD014DEC`；API `7E2E84E6BF04011A8EF821B7B9A24BD4A639021F8FC401A25663A95D0326B884` / `62BB1285BB9C64C3F6A6F30A52628CDF6981C14940FB6BBB6A8B7F2CE1FE2A80`。
- 样本披露：stable-save run2 的最大值为 `5187.3041 ms`，冻结 nearest-rank p95 仍为 `840.7838 ms`；原始样本完整保留。
- ER-1 chain：`allowed_files_hash=e67379512aaf6c1633e7961c97502a5859f3aee16c1eedc9744d522aee3af799`；`repair_chain_digest=27767f31a0b4c5293fba3c143c2c46cb3fa8a9f92ce7379ef43eff8a095ee9d1`；新增 collector 文件为 campaign outer scope 子集，历史不重置。
- Candidate progress：三个冻结 RED 均有直接 GREEN oracle；Campaign `attempt_count=1`、`consecutive_no_progress=0/4` 的最终状态等待独立 Review receipt。

## Campaign ER-1 独立 Review（2026-07-28）

- Decision：`Passed`；`P0/P1/P2/P3=0/0/1/0`；允许进入 `UA3` 可验收建议。
- Target closure：`DASHBOARD-BE-A1-P1-007`、`DASHBOARD-BE-A2-P1-001`、`DASHBOARD-BE-A2-P2-002` 全部 Closed；独立 Reviewer 的 1100 节点图、cache eviction、canonical/v1 和 ownership fingerprint 边界验证均为 GREEN。
- 唯一新 finding `DASHBOARD-BE-ER1-P2-001`：Outcome 使用旧测试计数；本次更正为 `130/130 Passed`。该项为 `record_only_correction`，不消耗 repair round，无需再次独立 Review。
- Review receipt：`C:\Users\92336\AppData\Local\Temp\dashboard-be-002-campaign-er1-independent-review.final.txt`；SHA256 `A2BA0E8E2239952F7BE31DB6FBAD4488228E682C8E78E7BCA331FC7EDC972AC2`。
- 输入不可变：审核结束时 repair/BE2 manifest 分别保持 `CFBB10234F273BF8473245C966A17A9B620E8709D544648A162B1644DA4CBF44` / `F05A73E415D0382E595CE42C398E3EB7CE045A1B59B878BAC9A25F3FE24F54E0`；Reviewer 未修改输入。
- Campaign state：`attempt_count=1`、`meaningful_progress=true`、`consecutive_no_progress=0/4`、hard-stop flags 全 false。
- Review 边界：`Review Passed` 只允许邀请 UA3，不等于 `UA Passed / Accepted / commit / merge / push / release / Closed`。

## DASHBOARD-BE-002 UA3 2026-07-28

- 用户反馈：用户在查看 BE-002 与依赖修复的组合验证、独立 Review 和尾延迟风险说明后明确回复“验收通过”。
- 验收范围：确认 loopback snapshot/task/health/SSE、Git 与 source 失效、原子发布、安全边界、三档数据集、完整回归和冻结性能门禁。
- 验收结果：`UA3 Passed / User Confirmed`；据此将 lifecycle 推进为 `Accepted`。
- 已知风险：用户在验收说明中已获知 stable-save run2 存在一个 `5187.3041 ms` 最大样本；冻结 nearest-rank p95 为 `840.7838 ms` 并通过门禁。
- 权限边界：本次用户反馈只构成 UA3 与 Acceptance authority，不授权 commit、stage、merge、push、release、删除 Worktree/分支或 Closed。

## 提交与合并授权 2026-07-28

- 用户授权：用户在 `UA3 Passed / Accepted` 写回后明确回复“提交并合并”。
- 提交策略：先由独立生命周期提交保存 `In Progress` 与 `Review`，本功能提交保存已审查实现树和 `Accepted / Committed / Unmerged` 状态。
- 合并策略：先合入 `codex/dashboard-be-001-repair-001` 形成组合树，复验后再合并到本地 `main`。
- 权限边界：不包含 push、release、外部同步、删除分支/Worktree或 Closed。

## 提交与合并结果 2026-07-28

- 生命周期提交：`9f96a86` 保存 `In Progress`，`1692a6d` 保存 `Review`，功能提交 `3cc22abbe06d8797f36f5fb0ada7dbbc044effd0` 保存已审查实现和 `Accepted / Committed`。
- 组合合并：`codex/dashboard-be-001-repair-001` 通过 no-ff merge 纳入本分支，组合提交为 `64312291d9579f3f712e120f5dbd9b0fb3b0995f`。
- main 合并：本地 `main` 从 `760b40442bcc96f711f12433a2c5d017d118d85c` 使用 `git merge --ff-only codex/dashboard-be-002` 快进到组合提交。
- 合并前组合复验：Dashboard `130/130 Passed`、Reader/治理 `85/85 Passed`，共享 TASK_BOARD 冲突只保留两条 Accepted 真值行。
- 权限边界：未 push、未 release、未删除分支/Worktree、未 Closed。

## Outcome

- Base / Diff：base=760b40442bcc96f711f12433a2c5d017d118d85c;diff=64312291d9579f3f712e120f5dbd9b0fb3b0995f
- 合并目标与事实证据：本地 `main`；feature=`3cc22abbe06d8797f36f5fb0ada7dbbc044effd0`；combined/main=`64312291d9579f3f712e120f5dbd9b0fb3b0995f`；repair no-ff 合入 BE-002 后由 main ff-only 合并。
- 修改文件：新增 `git_snapshot/**`、`snapshot/**`、`server/**`、`__main__.py` 与 `tests/be002/**`；同步本 TASK 和 TASK_BOARD。BE-001 repair 已通过同一组合提交进入本地 `main`。
- 用户可见行为：服务只绑定 loopback并提供 snapshot/task/health/SSE；source、Git、schema 与公开对象均纳入完整缓存失效和独立对象边界。
- 验证证据：组合回归 `130/130 Passed`、Reader/治理回归 `85/85 Passed`；六份 Campaign ER-1 30 样本结果的 nearest-rank 与 SHA256 已由 Engineer 和独立 Reviewer 分别复算，Git、安全、原子发布、三档 dataset 和四项性能门禁均有通过证据。
- Review findings：Campaign ER-1 独立 Review `Passed`，`P0/P1/P2/P3=0/0/1/0`；三个目标 finding Closed，唯一 P2 已作为纯记录纠错随 receipt 写回。
- UA 动作与结果：用户明确回复“验收通过”；`UA3 Passed / User Confirmed / Accepted`。
- 隔离位置：实现来源为 `D:\open-source\ai-dev-flow-wt\dashboard-be-002` 和 branch `codex/dashboard-be-002`；已合并到本地 `main`。
- 回滚方式：本功能提交及独立分支作为恢复点；删除、reset 或清理仍需用户明确授权。
- 状态边界：`Accepted / Passed / Campaign ER-1 / UA3 Passed / User Confirmed / Committed / Merged / Not Pushed / Not Released / Not Closed`。
- 剩余风险：stable-save run2 有一个 `5187.3041 ms` 最大样本；冻结 nearest-rank p95 为 `840.7838 ms` 并通过门禁，但这不代表最大延迟低于 1 秒；该风险已在 UA3 前披露并由用户接受。
- 下一步：没有自动后续动作；push、release、删除分支/Worktree 与 Closed 继续保持未授权。
