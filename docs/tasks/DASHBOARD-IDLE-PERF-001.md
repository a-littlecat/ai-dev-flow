# DASHBOARD-IDLE-PERF-001：降低 Dashboard 常驻扫描 CPU 占用

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `DASHBOARD-IDLE-PERF-001`
- `task_type`: `code`
- `task_class`: `D`
- `lifecycle`: `Accepted`
- `review_status`: `Passed`
- `ua_level`: `UA6`
- `ua_status`: `Passed`
- `ua_evidence`: `#dashboard-idle-perf-001-ua6-2026-07-31`
- `acceptance_authority`: `User Confirmed`
- `commit_status`: `Committed`
- `merge_status`: `Unmerged`
- `merge_authority`: `User Authorized`
- `close_authority`: `None`

## Scheduling

- `scheduling_schema`: `ai-dev-flow/scheduling/v1`
- `priority`: `high`
- `depends_on`: `DASHBOARD-BE-002`
- `replaces`: `none`
- `discovered_from`: `DASHBOARD-IDLE-PERF-001`
- `parent`: `DASHBOARD-001`
- `conflicts_with`: `none`
- `parallel_intent`: `avoid`
- `write_scope`: `dir:dashboard/backend`
- `module_locks`: `dashboard-runtime`
- `worktree`: `required`
- `branch_hint`: `codex/dashboard-idle-perf-001`
- `risk_flags`: `core_execution_path,shared_component,real_environment,business_files_gt_3`

## 目标与边界

- 目标：Dashboard 空闲时不再连续扫描全部 Worktree；Windows 使用标准库原生文件事件触发刷新，其他平台保留低频轮询兜底。
- 目标：同一项目的便携 Dashboard 只保留一个活动实例；浏览器 SSE 连接不重复刷新，Windows 正常事件源不执行周期性 Git 完整性扫描。
- 目标：保留 200ms trailing debounce、连续变化最多 1 秒刷新、完整 dirty ownership、只读 Git 命令和原有 HTTP/SSE 合同。
- 非目标：不改变 Dashboard 前端、合同 schema、调度结论、CADCat 项目内容、Git dirty 语义或外部 Skill 安装；不引入第三方依赖。
- 允许修改：仅限以下精确清单（hash=`0aef54cc059cfb921304949df1b722c892857b43712d36377c1be32f0cda5661`）：
  - `dashboard/backend/src/ai_dev_flow_dashboard/__main__.py`
  - `dashboard/backend/src/ai_dev_flow_dashboard/portable.py`
  - `dashboard/backend/src/ai_dev_flow_dashboard/server/http.py`
  - `dashboard/backend/src/ai_dev_flow_dashboard/snapshot/coordinator.py`
  - `dashboard/backend/src/ai_dev_flow_dashboard/snapshot/events.py`
  - `dashboard/backend/src/ai_dev_flow_dashboard/snapshot/watcher.py`
  - `dashboard/backend/tests/be002/test_http_sse.py`
  - `dashboard/backend/tests/be002/test_native_events.py`
  - `dashboard/backend/tests/be002/test_watcher_performance.py`
  - `dashboard/integration/accepted-artifacts.json`
  - `dashboard/integration/tests/test_artifact_guard.py`
  - `dashboard/integration/tests/test_build_skill_runtime.py`
  - `dashboard/integration/tests/test_portable_runtime.py`
  - `skills/ai-dev-flow/dashboard/backend/src/ai_dev_flow_dashboard/__main__.py`
  - `skills/ai-dev-flow/dashboard/backend/src/ai_dev_flow_dashboard/portable.py`
  - `skills/ai-dev-flow/dashboard/backend/src/ai_dev_flow_dashboard/server/http.py`
  - `skills/ai-dev-flow/dashboard/backend/src/ai_dev_flow_dashboard/snapshot/coordinator.py`
  - `skills/ai-dev-flow/dashboard/backend/src/ai_dev_flow_dashboard/snapshot/events.py`
  - `skills/ai-dev-flow/dashboard/backend/src/ai_dev_flow_dashboard/snapshot/watcher.py`
  - `skills/ai-dev-flow/dashboard/runtime-manifest.json`
  - `docs/tasks/DASHBOARD-IDLE-PERF-001.md`
  - `docs/TASK_BOARD.md`
- 禁止修改：`dashboard/contracts/**`、`dashboard/frontend/**`、`dashboard/backend/src/ai_dev_flow_dashboard/core/**`、CADCat 项目、依赖声明、版本/发布文件和其他 TASK；禁止 commit、merge、push、release、外部同步、删除或 Closed。

## 依赖与授权

- 前置依赖：`DASHBOARD-BE-002`、`DASHBOARD-PORTABLE-001`、`REL-004` 已 Accepted/Committed/Merged；当前实现基线 `main@36aae03e944c3b8b7d5ec52d1417190012d1a6d1`。
- Base commit：`36aae03e944c3b8b7d5ec52d1417190012d1a6d1`
- 已有 authority：用户于 2026-07-31 在确认“事件驱动 + 低频兜底 + 单实例”方案及 CPU 目标后明确回复“可以”，授权在精确清单内实现、测试、启动/停止临时本地验收实例并执行独立只读 Review。用户随后明确回复“性能验收通过，并启动自动落地目标”，授权记录 UA6 Passed / Accepted，精确提交、推送、集成至最新 `main`、重建 runtime、本机 Skill 同步、任务关闭及已完全合并任务分支删除。
- 未授权动作：tag、release、deploy、强制推送、历史改写、删除未完全合并分支或覆盖主工作区用户改动。
- 执行位置：`D:\open-source\ai-dev-flow-wt\dashboard-idle-perf-001`，分支 `codex/dashboard-idle-perf-001`。

## 路由与风险

- 路由：`Controlled`
- Policy 输入：D 类；请求实现；命中 `core_execution_path`、`shared_component`、`real_environment` 和多文件风险；需要真实 CADCat CPU/事件更新证据与用户 UA6。
- Reviewer 闸门：`Required`；验收建议前必须完成同 Harness、上下文隔离且文件系统只读的独立 Review。
- 停止条件：需要改变公共 schema/只读安全边界、增加生产依赖、修改精确清单外文件、无法保持 dirty ownership 正确性、真实 CPU 门禁或事件更新门禁失败。

## 完成标准与验证

- 完成标准：事件驱动、空闲暂停、单实例、运行时一致性、真实 CADCat CPU 门禁和用户 UA6 均形成可定位证据。
- 验证命令或检查：运行 backend、integration、frontend、Skill 全量测试，bundle parity、Artifact Guard、workflow lint、Git/diff 检查和真实 CADCat 30 秒 CPU/子进程采样。
- [x] Windows 原生事件 watcher 在文件变化时唤醒；无第三方依赖；非 Windows 有低频轮询 fallback。
- [x] 无文件变化时不执行周期性完整 Git probe；真实文件事件始终刷新；SSE 连接不重复启动完整扫描；非 Windows 或原生事件不可用时使用不调用 Git 的低频 manifest fallback。
- [x] 文件事件继续满足 200ms trailing debounce 和连续变化最多 1 秒刷新；变化期间不并发重入 refresh。
- [x] 同一项目便携运行时第二次启动不创建第二个后台，并能报告已有实例 URL；不同项目仍可并行。
- [x] 单元/集成/前端/Skill 验证通过，运行时 bundle 与源码一致，Artifact Guard candidate 一致。
- [x] 真实 CADCat 单实例空闲 30 秒平均 CPU 低于 `1%` 单逻辑核心；没有持续 Git 子进程波次。
- [x] 修改 TASK 文件、tracked/untracked 文件和 Git/Worktree 后，Dashboard 数据可在规定窗口内刷新且 dirty ownership 不回归。
- [x] `git diff --check` 通过，diff 只属于精确清单。

## Outcome

<a id="dashboard-idle-perf-001-ua6-2026-07-31"></a>
### 用户 UA6 确认（2026-07-31）

- 用户动作：用户在收到页面、性能与 Goal 的真实合并状态、CPU 证据和本机同步门禁后明确回复“性能验收通过”。
- 确认范围：Windows 原生文件事件、空闲无周期性完整 Git probe、便携单实例，以及真实 CADCat 25 秒进程树 CPU / Git 子进程证据。
- UA 动作与结果：`UA6 Passed / User Confirmed`。
- authority 边界：允许提交、推送、集成、runtime 重建、本机 Skill 同步、Closed 写回和完全合并后分支删除；不包含 tag、release、deploy、强制推送或历史改写。

- Base / Diff：base=36aae03e944c3b8b7d5ec52d1417190012d1a6d1;diff=2963353a33e3717202b91ba6b0bebcbbc994d88a
- 隔离位置：`D:\open-source\ai-dev-flow-wt\dashboard-idle-perf-001`，分支 `codex/dashboard-idle-perf-001`。
- 回滚方式：对候选提交 `2963353` 使用普通 `git revert`；不删除 Worktree、不 reset、不改写历史。
- 修改文件：Dashboard watcher/事件源、SSE 客户端计数、便携单实例锁、对应 backend/integration 测试、Artifact Guard 候选、内置 Skill runtime、本 TASK 与 TASK_BOARD。
- 验证证据：Python 3.13 backend `174/174`、integration `51/51`、frontend codegen/typecheck/lint/build + unit `82/82` + browser `83/83`、Skill `85/85`、runtime bundle `--check` 与 Artifact Guard candidate 均通过。
- 验证证据：Round 11 Review Passed 最终候选的真实 CADCat 页面保持 SSE 已连接；连续 `25.025s` 整棵验收进程树采样平均约 `0.125%` 单逻辑核心、约 `0.0078%` 整机 CPU，20ms 轮询观察到 Git 进程 `0`，`last_refresh_at` 与 revision 全程不变，watcher 与 server 保持 `ready`；相对原始约 `103.3%` 单逻辑核心占用，降幅约 `99.88%`。
- 验证命令与结果：本任务 workflow lint 为 `0 errors / 0 violations / 1 warning`（未提交导致 transition unverifiable）；`git diff --cached --check` 通过；22 个暂存文件与 22 个精确允许文件完全一致。
- Review findings：Round 1 独立只读 Review（session `019fb418-0754-73a2-a6b9-85492747edc8`）为 `Needs Fix`，发现 `IDLE-PERF-P1-001` 至 `005`；`P1-002/004/005` 已由 Round 2 确认关闭。
- Review findings：Round 2 独立只读 Review（session `019fb429-7dcb-7860-baab-503f6d4327d8`）为 `Needs Fix`：`P1-001` 补充合法 tracked 点文件、`P1-003` 改为 overlapped I/O 在内核登记完成后才返回；`P2-006` 的首次修复在 Round 3 被判定仍有停止/重新设防竞态。
- Review findings：Round 3 独立只读 Review（session `019fb441-e528-7b21-b839-de5daa1227f2`）确认 `P1-001/P1-003` Closed，但保持 `P2-006` Open，并新增 `P1-007/P2-008`：当前已将 Worktree 内容目录与精确 Git/schema 路径分离、剪枝 `.git/**`，以 per-root I/O 锁串行停止与重新设防，并对线程启动失败执行 cancel-and-drain 完整回滚；新增非递归、外部 Git 路径、object database 剪枝、并发 remove 与启动失败回归，等待 Round 4 独立复核。
- Review findings：Round 4 独立只读 Review（session `019fb454-f628-77e3-b0bd-5d9feb487a58`）确认 `P1-007/P2-008` Closed，但保持 `P2-006` Open，并新增 `P1-009/P2-010`：当前每轮 refresh 前先把当前 desired requests 幂等同步到事件源；watch thread 对每个已登记 read 必定 wait/drain 后才退出；coordinator 显式暴露 resolved Git metadata 排除根，内容监听与 fallback 都按实际 metadata 路径剪枝。新增真实 native 新顶层目录二次变化、rearm/remove drain、内部自定义 Git 目录回归，等待 Round 5 独立复核。
- Review findings：Round 5 独立只读 Review（session `019fb466-dc81-74e2-9bae-b1fc3d01e19c`）确认 `P1-009/P2-010` Closed、无新 P1，但保持 `P2-006` Open 并新增 `P2-011`：异常 wait failure 的真实反例显示 cancel 后未 drain；自定义 Git metadata 测试未经过真实 Coordinator 接线。当前以显式 pending 所有权保证 stop/remove 在关闭句柄前完成 `GetOverlappedResult(wait=True)`，并新增 wait failure 回归；另以真实 `git init --separate-git-dir`、实际 SnapshotBuilder/Coordinator 端到端验证 metadata 根及其子目录从内容根、fallback manifest 与递归监听中剔除，同时保留 HEAD/index/refs 精确监听，等待 Round 6 独立复核。
- Review findings：Round 6 独立只读 Review（session `019fb47f-6cdd-7252-b569-6b761d4ce9c3`）确认 `P2-006` Closed、无新 P1，但保持 `P2-011` Open 并新增 `P2-012`：真实 Git 回归还需显式断言 refs 精确递归监听与合法外部 linked worktree；并发 `update()`/`stop()` 可重复关闭同组 Win32 handles。当前真实 separate-git-dir 测试已增加 refs 与外部 linked worktree 断言；原生事件源用 `_closing/_adding` 状态与 Condition 原子认领关闭责任、阻止关闭/启动交叠，并新增强制并发回归验证每个 handle 仅关闭一次，等待 Round 7 独立复核。
- Review findings：Round 7 独立只读 Review（session `019fb493-6995-7890-88a8-1bf7e710e027`）确认 `P2-011` Closed、无新 P1，但保持 `P2-012` Open：`update()` 在 `ReadDirectoryChangesW` 内阻塞时，`stop()` 超时后可迟到登记没有活动线程的 watch；`start()` 与 `stop()` 交叠时可由迟到的 `start()` 清除停止信号并留下已退出线程。当前以 `_start_stop_lock` 串行 start/stop 生命周期；新增 watch 发布前停止状态复核与 cancel/drain/close 回滚；活动态 `ERROR_OPERATION_ABORTED` 改为重新设防；新增两个确定性竞态回归，等待 Round 8 独立复核。
- Review findings：Round 8 独立只读 Review（session `019fb4a5-7e52-7592-891c-a0b66ac9e109`）为 `Needs Fix`，无 P0/P1，但保持 `P2-012` Open 并新增测试覆盖项 `P2-013`：watch 在线程启动前公开时并发 remove 可关闭其 handles，活动态 `ERROR_OPERATION_ABORTED` 重新设防缺少确定性回归。当前用 `_update_lock` 串行 update 生命周期，改为线程启动成功且再次确认未停止后才公开 watch；启动取消/失败由单一 owner 执行 cancel、join、drain、close；新增启动成功/失败期间并发 remove 的 close-once 回归，以及真实活动 read 被 `CancelIoEx` 后重新设防并观察下一次变化的回归，等待 Round 9 独立复核。
- Review findings：Round 9 独立只读 Review（session `019fb4b5-dd52-7c21-9beb-4d8110a61659`）在 CLI 包装器 10 分钟超时后产生迟到 `Needs Fix` 收据：确认 `P2-013` Closed、无新 P0/P1/P2，但保持 `P2-012` Open；watch 发布后到外层 `_adding` 清除前若 `stop()` 等待超时，第一次停止可遗留活动线程和句柄。当前将再次检查 stop、发布 `_watches`、清除 `_adding` 与 Condition 通知合并为同一原子状态转换；新增 `_add_reserved()` 已返回但 `_add()` 尚未返回期间的 stop 回归，断言第一次停止即无线程/watch 残留且每个 handle 只关闭一次，等待 Round 10 独立复核。
- Review findings：Round 10 独立只读 Review（session `019fb4c6-2893-7051-a579-849a492ff839`）为 `Needs Fix`，无新 P0/P1，但新增 `P2-014/P2-015`：上一轮 stop 回归的 2 秒 barrier 可能先于 stop 超时自行释放，无法构成真实 RED→GREEN 保护；`ERROR_NOTIFY_ENUM_DIR` 后重新设防异常未上报，可能阻止上层切换 fallback。当前 stop 回归改为独立 stopper，必须在 barrier 未释放且 updater 仍阻塞时由第一次 stop 无异常收敛；目录通知溢出后的 `_rearm()` 与其他分支一致捕获异常并调用 `_fail()`，新增真实事件完成后注入溢出与 ResetEvent 失败的确定性回归，等待 Round 11 独立复核。
- Review findings：Round 11 独立只读 Review（session `019fb4d3-4ea7-70e1-99e4-4032062383d7`）为 `Passed`，确认 `P2-014/P2-015` Closed，P2-011～013 与全部更早 P1/P2 保持关闭，无开放或新增 P0/P1/P2；22 个暂存文件与精确清单一致，源码与内置 Skill 运行时对应 blob 一致。
- UA 动作与结果：`UA6 Passed`；用户于 2026-07-31 明确确认性能验收通过。
- 状态边界：`Accepted / Committed 2963353a33e3717202b91ba6b0bebcbbc994d88a / Pushed origin/codex/dashboard-idle-perf-001@cfcf23c / Unmerged / Not Released / Not Closed`。
- 剩余风险：非 Windows fallback 仅有自动回归，未做真实非 Windows 性能采样。
- 下一步：候选提交、推送和用户 UA6 确认已完成；正在独立集成 Worktree 与页面候选串行集成、重建 runtime 并完成合并后验证。
