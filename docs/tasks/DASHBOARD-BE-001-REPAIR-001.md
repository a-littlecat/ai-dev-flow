# DASHBOARD-BE-001-REPAIR-001：修复核心快照性能与 dirty ownership 合同

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `DASHBOARD-BE-001-REPAIR-001`
- `task_type`: `repair`
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
- `depends_on`: `DASHBOARD-BE-001#commit_status=Committed;DASHBOARD-BE-001#lifecycle=Accepted;DASHBOARD-BE-001#merge_status=Merged;DASHBOARD-BE-001#review_status=Passed;DASHBOARD-BE-001#ua_status=Passed`
- `replaces`: `none`
- `discovered_from`: `DASHBOARD-BE-002`
- `parent`: `DASHBOARD-BE-001`
- `conflicts_with`: `DASHBOARD-BE-002`
- `parallel_intent`: `serial`
- `write_scope`: `dir:dashboard/backend/src/ai_dev_flow_dashboard/core;dir:dashboard/backend/tests/be001;dir:dashboard/contracts;file:docs/tasks/DASHBOARD-BE-001-REPAIR-001.md;file:docs/TASK_BOARD.md;file:skills/ai-dev-flow/scripts/workflow_contract.py;file:skills/ai-dev-flow/tests/test_workflow_contract_reader.py;file:skills/ai-dev-flow/tests/test_workflow_contract_validation.py;file:skills/ai-dev-flow/tests/test_workflow_lint.py`
- `module_locks`: `dashboard-backend;dashboard-contracts;dashboard-core;dashboard-domain;dashboard-parallel`
- `worktree`: `required`
- `branch_hint`: `codex/dashboard-be-001-repair-001`
- `risk_flags`: `architecture;core_execution_path;public_api;shared_component;tests_do_not_cover_oracle`

## 目标与边界

- 目标：把 BE-001 冷核心读取性能降到足以支撑 BE-002 `500 TASK / 2000 edges` 完整 cold snapshot `p95 <= 2000 ms` 的水平，不跳过输入冻结、公开 Reader、Scheduling 或 schema validation。
- 目标：为 dirty Worktree 增加可验证的 `owned_by_task / unowned / unknown` 证据，使完全落入唯一任务 `write_scope` 的 dirty paths 可以被并行引擎识别，同时任何越界、共享或不确定 dirty 仍 fail closed。
- 非目标：不修改 BE-002 HTTP/SSE/watcher 实现，不新增依赖，不改变 Review/UA/commit/merge 等状态独立性，不放宽现有性能、安全或 schema oracle。
- 允许修改：`dashboard/backend/src/ai_dev_flow_dashboard/core/**`、`dashboard/backend/tests/be001/**`、`dashboard/contracts/**`、`skills/ai-dev-flow/scripts/workflow_contract.py`、`skills/ai-dev-flow/tests/test_workflow_contract_reader.py`、`skills/ai-dev-flow/tests/test_workflow_contract_validation.py`、`skills/ai-dev-flow/tests/test_workflow_lint.py`、本 TASK 和 TASK_BOARD 对应投影。
- 禁止修改：除精确列出的 Reader 文件外的 `skills/ai-dev-flow/**`、`dashboard/backend/pyproject.toml`、BE-002 HTTP/SSE/watcher 实现、前端、其他 TASK、版本/发布文件和本机 Skill；禁止新增依赖、把 dirty 伪装成 clean、删除测试或降低门禁。

## 依赖与授权

- 前置依赖：`DASHBOARD-BE-001` 已 `Accepted / Review Passed / UA3 Passed / Committed / Merged`；`DASHBOARD-BE-002-BLOCK-001/002` 已在 BE-002 Worktree 稳定记录。
- Base commit：`760b40442bcc96f711f12433a2c5d017d118d85c`
- 已有 authority：用户在收到两个阻塞项、所需修复范围和未授权边界后明确回复“授权”；允许创建本修复 TASK/Worktree，在精确 allowlist 内诊断、实现、验证，并执行隔离只读 Review 和最多两轮有限 AutoRepair，直到 `Review Passed / UA3 Pending`。
- 新增 authority：用户在获知公共 Reader 热点、所需精确文件范围和原权限缺口后明确回复“授权，继续修复然后独立审核直至能验收状态”；允许把 `workflow_contract.py` 及三份定向测试纳入 A1，并在原 BE-001 core/schema/tests 与原 BE-002 已授权实现边界内完成组合验证和独立审核。
- 未授权动作：新增第三方依赖、越界修改、commit、merge、push、release、外部同步、代替用户 UA3、记录 Accepted、删除 Worktree/分支或 Closed。
- 执行位置：修复位于 `D:\open-source\ai-dev-flow-wt\dashboard-be-001-repair-001`，BE-002 原授权实现位于 `D:\open-source\ai-dev-flow-wt\dashboard-be-002`；组合验证在临时只读副本执行。

## 路由与风险

- 路由：`Controlled`
- Policy 输入：`task_class=D`；风险包含 `architecture`、`core_execution_path`、`public_api`、`shared_component`、`tests_do_not_cover_oracle`；动作 authority 已明确；验收建议前需要隔离只读 Review。
- Reviewer 闸门：`Required`；实现进入 UA3 建议前必须完成当前 Codex Harness 的隔离、只读 Review，P0/P1 必须关闭。
- 主要风险：为了性能削弱 Windows 文件租约；缓存跨 revision 复用过期输入；ownership 错把越界 dirty 判为 owned；wire schema 与 BE-002 消费者漂移。
- 停止条件：需要新增依赖、放宽门禁、弱化冻结/安全 oracle、无法证明缓存失效、schema 需要破坏性版本迁移、diff 越出 allowlist或出现数据完整性/安全风险。

## 完成标准与验证

- 完成标准：两个 blocker 的冻结 RED 均变为 GREEN，且不削弱输入冻结、strict validator、安全边界或 fail-closed 语义。
- 验证命令或检查：运行 BE-001/BE-002 组合回归、三档 30 样本性能协议、target/project lint、diff scope、`git diff --check` 和隔离只读 Review。
- [ ] 建立可复现 profiler/计时反馈环，分离 Windows lease、公开 Reader、Scheduling/graph、Git、watcher 和 serialization；保留修复前 RED 与修复后 30 样本 GREEN。
- [ ] `50/200`、`500/2000`、`1000/4000` 三档均可运行；参考机 `500/2000 cold snapshot p95 <= 2000 ms`，连续两次 dataset digest 相同。
- [ ] stable save 到 revision 的 30 样本 `p95 <= 1000 ms`；真实原子 rename、watcher idle 和 loopback SSE socket 均计入。
- [ ] dirty ownership 覆盖 clean、唯一 owned、越界、共享 scope、未映射、多映射、detached、locked/prunable、rename/copy 双路径、submodule、Unicode/空格和 Windows casefold。
- [ ] `owned_by_task` 只在 branch/Worktree 唯一且每个 dirty path 完全落入该 TASK canonical `write_scope` 时成立；其他情况为 `unowned/unknown`，不得产生伪 candidate。
- [ ] schema、fixtures、BE-001 和 BE-002 组合测试使用同一 validator 全部通过；公共字段变化有明确兼容与前端影响说明。
- [ ] Python 3.12 完整组合回归通过。
- [ ] `python skills/ai-dev-flow/scripts/workflow_lint.py docs/tasks/DASHBOARD-BE-001-REPAIR-001.md --format json` 无 error/violation。
- [ ] implementation diff 只命中本 TASK 精确 allowlist，`git diff --check` 通过。

## 实施启动（2026-07-28）

- 用户授权：用户明确授权创建本修复 TASK/Worktree，并在冻结范围内诊断、实现、验证及进入隔离 Review。
- 实施基线：`main@760b40442bcc96f711f12433a2c5d017d118d85c`。
- 隔离位置：`D:\open-source\ai-dev-flow-wt\dashboard-be-001-repair-001`，branch `codex/dashboard-be-001-repair-001`。
- 状态边界：`In Progress / Review Pending / UA3 Pending / Uncommitted / Unmerged`。

## Outcome

- Base / Diff：base=760b40442bcc96f711f12433a2c5d017d118d85c;diff=working-tree
- 修改文件：计划在冻结 core/schema/Reader/tests 与本 TASK/TASK_BOARD 范围内实施。
- 验证证据：待实施后运行组合回归、性能协议、lint 与 diff/scope 检查。
- Review findings：`Pending`。
- UA 动作与结果：`UA3 Pending`。
- 隔离位置：`D:\open-source\ai-dev-flow-wt\dashboard-be-001-repair-001`，branch `codex/dashboard-be-001-repair-001`。
- 回滚方式：独立 Worktree，尚无业务提交。
- 状态边界：`In Progress / Review Pending / UA3 Pending / Uncommitted / Unmerged / Not Pushed / Not Released / Not Closed`。
- 下一步：完成冻结实现与验证后进入独立 Review。