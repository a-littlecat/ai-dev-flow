# DASHBOARD-BE-001：实现任务关系与调度核心

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `DASHBOARD-BE-001`
- `task_type`: `code`
- `task_class`: `C`
- `lifecycle`: `Accepted`
- `review_status`: `Passed`
- `ua_level`: `UA3`
- `ua_status`: `Passed`
- `ua_evidence`: `docs/tasks/DASHBOARD-BE-001.md#dashboard-be-001-ua3-2026-07-28`
- `acceptance_authority`: `User Confirmed`
- `close_authority`: `None`
- `commit_status`: `Committed`
- `merge_status`: `Unmerged`
- `merge_authority`: `None`

## Scheduling

- `scheduling_schema`: `ai-dev-flow/scheduling/v1`
- `priority`: `high`
- `depends_on`: `DASHBOARD-001#lifecycle=Accepted`
- `replaces`: `none`
- `discovered_from`: `DASHBOARD-001`
- `parent`: `DASHBOARD-001`
- `conflicts_with`: `none`
- `parallel_intent`: `serial`
- `write_scope`: `file:dashboard/backend/pyproject.toml;file:dashboard/backend/src/ai_dev_flow_dashboard/__init__.py;dir:dashboard/backend/src/ai_dev_flow_dashboard/core;dir:dashboard/backend/tests/be001;dir:dashboard/contracts`
- `module_locks`: `dashboard-backend;dashboard-contracts;dashboard-domain;workflow-contract-reader`
- `worktree`: `required`
- `branch_hint`: `codex/dashboard-be-001`
- `risk_flags`: `architecture;core_execution_path;public_api;shared_component;tests_do_not_cover_oracle`

## 目标与边界

- 目标：实现本地任务仪表盘的后端核心，使冻结 TASK 文本能够稳定转换为任务节点、关系边、下一动作和并行评估，并生成前后端共用的 versioned schema、validator 与 fixtures。
- 目标：只通过公开 `WorkflowContract.inspect(project_root)` 读取 Core Contract；Scheduling Parser 读取同一份冻结 UTF-8 文本，不复制或分叉现有 Workflow Contract 状态机。
- 非目标：不实现 Git/Worktree 采集、文件 watcher、HTTP/SSE 服务、静态资源托管、前端页面、安装器或任务执行器。
- 非目标：不修改 TASK、TASK_BOARD、Git 或 Worktree；不把建议动作、并行候选或浏览器状态转换成 authority。
- 允许修改：未来执行时仅限 `dashboard/backend/pyproject.toml`、`dashboard/backend/src/ai_dev_flow_dashboard/__init__.py`、`dashboard/backend/src/ai_dev_flow_dashboard/core/**`、`dashboard/backend/tests/be001/**`、`dashboard/contracts/**`、`docs/tasks/DASHBOARD-BE-001.md` 和该任务在 `docs/TASK_BOARD.md` 的投影行。
- 禁止修改：`skills/ai-dev-flow/**` 既有 Reader/Writer、其他 TASK、前端目录、版本/发布文件和本机 Skill；禁止新增第三方依赖，除非用户另行明确授权。

## 实施合同

### 固定目录责任

- `dashboard/backend/pyproject.toml` 与 `dashboard/backend/src/ai_dev_flow_dashboard/__init__.py`：Python 3.11/3.12 后端包的最小基础入口；不得放入 Git、watcher、HTTP/SSE 或集成逻辑。
- `dashboard/backend/src/ai_dev_flow_dashboard/core/**`：本任务独占的 Contract Gateway、Frozen Input、Scheduling、领域模型、关系/动作/并行引擎和 canonical serialization。
- `dashboard/backend/tests/be001/**`：本任务单元测试、无 Git/网络副作用的集成测试和 benchmark generator 测试。
- `dashboard/contracts/`：版本化 JSON Schema（或能力等价且可机器校验的严格 schema）、共享 validator、至少 8 组 JSON fixtures 与一份 SSE transcript。
- 本任务先冻结 `dashboard/contracts/**`；`DASHBOARD-BE-002` 和 `DASHBOARD-FE-001` 后续只消费该基线，任何 schema 语义变化都必须返回本任务重新 Review。

### 必须实现的模块

1. `Contract Gateway`
   - 调用公开 `WorkflowContract.inspect(project_root)`。
   - 保存 ReaderReport 的 normalized values、diagnostics、projections 与 provenance。
   - 不导入 `_workflow_contract.py` 私有状态表，不从 TASK_BOARD 反向覆盖 TASK。
2. `Frozen Input Loader`
   - 一次读取 TASK 的 UTF-8 bytes、路径、mtime 与 SHA256。
   - Core Reader 和 Scheduling Parser 必须针对同一冻结内容；发布结果前发现 digest 改变则废弃候选。
3. `Scheduling Profile Adapter`
   - 严格实现 `ai-dev-flow/scheduling/v1` 的 13 字段、基数、排序、引用、Windows 路径和 fail-closed 规则。
   - 缺失/非法/冲突只产生 `unknown` 与 diagnostic，不从自然语言猜关系、authority 或并行结论。
4. `Domain Model`
   - 实现 `TaskNode`、`RelationshipEdge`、`DependencyCondition`、`ActionRecommendation`、`ParallelAssessment`、`Diagnostic`、`Provenance` 等冻结对象。
   - JSON 字段、枚举、nullability、排序和 `additionalProperties=false` 与 `DASHBOARD-001` 完全一致。
5. `Relationship / Action / Parallel Engine`
   - 实现 depends_on、parent、replaces、discovered_from、conflicts_with、环检测和稳定 ID。
   - 动作矩阵逐分支输出固定 action/eligibility/authority/reason，不推导未支持的 authority。
   - 并行评估只输出 `candidate / must_serial / unknown`，且 `candidate` 永远携带 `requires_user_confirmation=true`。
6. `Canonical Serialization`
   - Unicode NFC、稳定排序、UTF-8、无多余空白并生成可复算 SHA256。
   - 相同逻辑输入必须产生相同 payload 与 revision 输入。
7. `Shared Contract Package`
   - 至少覆盖 `fresh`、`stale`、`partial`、`parse-error`、`dependency-cycle`、`parallel-unknown`、`git-degraded`、`task-detail-error`。
   - 同一个 strict validator 必须拒绝缺失字段、额外字段、错误类型和非法枚举。

### `DASHBOARD-001-P2-006` 收口要求

- benchmark dataset entry 在代码和测试中必须使用单字节 NUL `0x00` 与 LF `0x0A`。
- Python oracle 固定使用 `b"\x00"` 与 `b"\x0a"`；测试必须证明不是可见的反斜杠字符序列。
- generator 连续两次生成的 manifest 和 dataset SHA256 必须完全一致。
- 该项完成前，本任务不得进入 Review。

## 依赖与授权

- 前置依赖：`DASHBOARD-001` 已 `Review Passed / UA2 Passed / Accepted / Committed`；六文件规划 baseline 已形成。
- Base commit：规划内容 baseline 为 `371383f0d93048fa2a31c1ca1306a7e1421650ff`；新对话必须从包含本提交收据的最新 `main` HEAD 冻结实际实施 base。
- 条件化 execution authority：用户已明确要求在四份实施 TASK 复审通过、Ready 写回并形成六文件规划 Git baseline 后，新开对话执行本 TASK，允许在本 TASK 精确 allowlist 内实现、验证，并执行隔离 Review/有限 repair，直到 `Review Passed / UA3 Pending`。
- 执行前置：本轮实施 TASK Review 必须为 Passed、本 TASK lifecycle 必须为 Ready、六文件规划必须已 commit；任一条件未满足都不得创建 Worktree 或开始代码。
- 未授权动作：新增第三方依赖、实现 diff 越出 allowlist、代码 commit、代替用户 UA3、记录 Accepted、merge、push、release、外部同步、删除和 Closed。
- 执行位置：必须由用户要求的新对话创建独立 Worktree 与 `codex/dashboard-be-001` 分支；主工作区不得承载实现 diff。达到 `Review Passed / UA3 Pending` 后停止并交给用户验收。

## 路由与风险

- 路由：`Controlled`。
- Policy 输入：`task_class=C`、`ua_level=UA3`、风险包含 `architecture`、`core_execution_path`、`public_api`、`shared_component`、`tests_do_not_cover_oracle`；当前无 execution authority。
- Reviewer 闸门：`Required`；TASK 合同进入 Ready 前和代码进入验收建议前均需当前 Harness 的隔离、只读 Review。
- 主要风险：复制第二套状态机、自然语言猜测调度语义、把建议当权限、前后端 schema 漂移、稳定 ID/revision 不可复算。
- 停止条件：需要修改 `adf/v0.7.0` Core 字段；需要修改现有 Reader 私有实现；需要数据库、网络服务或大型依赖；无法用 fixtures 给出唯一 oracle；P2 字节语义仍不唯一。

## 完成标准与验证

- 完成标准：公开 Reader 与 Scheduling 使用同一冻结输入，所有结构/值错误按合同 fail closed。
- 完成标准：领域对象、关系、动作、并行、稳定 ID、canonical serialization 与共享 schema/fixtures 全部实现。
- 完成标准：`DASHBOARD-001-P2-006` 的 NUL/LF byte oracle 在生成器和测试中唯一且可复算。
- 完成标准：本任务不读取项目根外文件，不修改 TASK/Git/Worktree，不发起网络监听。
- 验证命令或检查：执行 `python -B -X utf8 -m unittest discover -s dashboard/backend/tests -p "test_*.py" -v`。
- 验证命令或检查：对 schema/fixtures 连续运行两次 validator 与 digest 生成，结果必须一致。
- 验证命令或检查：运行 `python skills/ai-dev-flow/scripts/workflow_lint.py docs/tasks/DASHBOARD-BE-001.md --format json`。
- [ ] 覆盖 Scheduling 13 字段、依赖 registry、关系环、动作笛卡尔状态、Windows 路径与并行冲突矩阵。
- [ ] 覆盖 missing/extra/type/enum schema 反例和所有 versioned fixtures。
- [ ] 覆盖 `b"\x00"` / `b"\x0a"` 与可见反斜杠序列的反例。
- [ ] 机器检查 implementation diff 只命中本任务精确 allowlist；任何 BE-002 命名空间或前端路径均拒绝。
- [ ] `git diff --check` 通过，diff 只归属当前 TASK。

## 验收建议

- 用户动作等级：UA3（用户查看构建、测试、schema/fixture 和独立 Review 证据，不需要亲自运行）。
- 是否需要用户实机测试：否；真实本地页面体验统一放到 `DASHBOARD-INTEGRATE-001`。
- 不验收的风险：关系、动作或并行结论可能在 UI 中被稳定但错误地展示。
- 是否允许关闭任务：否；当前只是 Ready，尚未实施或验收。

## 四份实施 TASK 初始独立 Review（2026-07-28）

- Reviewer：当前 Codex Harness 的独立 Reviewer 子上下文；仅收到 NTFS `RX` 冻结证据副本，Reviewer 前后主工作区六份规划文件哈希一致，`Workspace writes=None`。
- 冻结输入：本 TASK SHA256 `B778C3DE428AD179291A52AD7BA339E54678F6A606F1128CABF69B129CD7B2DD`；基线 `main@fb16bc50f02023aad4a51acd8bf495231fe65f63`。
- 结论：`Passed`；本 TASK 没有 P0/P1/P2/P3，可在规划文件形成 Git baseline 且状态写回后进入 Ready。
- 状态边界：这里只审查实施合同；未实施、未 UA3、未 commit、未 Accepted。

## 四份实施 TASK Repair Round 1 独立复审（2026-07-28）

- Reviewer：同一独立 Reviewer 子上下文；读取 17 文件 NTFS `RX` 冻结副本，前后文件数 `17 → 17`、SHA256 差异 `None`，`Workspace writes=None`。
- 结论：整体 `Needs Fix`，`P0/P1/P2/P3=0/1/0/0`；原 `P1-001/002/003` 全部 Closed，新发现 `DASHBOARD-TASKS-P1-004`。
- `DASHBOARD-TASKS-P1-004`：父 TASK/TASK_BOARD 已条件授权执行 BE-001，但本 TASK 仍写“仅允许建档，代码/Worktree/Review/repair 未授权”，细粒度事实源不唯一。

## 四份实施 TASK Repair Round 2（2026-07-28）

- `attempt_id`: `DASHBOARD-TASKS-RC-001-A2`
- `repair_chain_id`: `DASHBOARD-TASKS-RC-001`
- `finding_ids`: `DASHBOARD-TASKS-P1-004`
- 修订：把本 TASK authority 与父 TASK/TASK_BOARD 对齐；冻结复审 Passed、Ready 写回、六文件 baseline commit 三个执行前置，以及新对话、独立 Worktree、精确 allowlist、`Review Passed / UA3 Pending` 停止点。
- 保持未授权：第三方依赖、越界 diff、代码 commit、用户 UA3、Accepted、merge、push、release、外部同步、删除和 Closed。
- GREEN：三处 authority、前置和停止点已有逐项一致文本；是否关闭由下一次独立复审判定。

## 四份实施 TASK Repair Round 2 最终独立复审（2026-07-28）

- 冻结输入：本 TASK SHA256 `01BE65CB3751704DA4E946D66C004AD9AEEAF3F403ACDA1D5589378FE771EB48`。
- 结论：`Passed`；`DASHBOARD-TASKS-P1-004` Closed，原 `P1-001/002/003` 无回归，无新增 finding；整体 `P0/P1/P2/P3=0/0/0/0`。
- Reviewer 确认：公开 Reader、schema/validator/fixtures、单字节 NUL/LF oracle、精确 allowlist、执行前置和停止点足以进入 Ready。
- 状态边界：`Ready / Review Passed / UA3 Pending / Uncommitted / Unmerged`；规划 baseline 已形成，允许按条件化 authority 在新对话创建实现 Worktree。

## 实现 Review 与 Repair Round 1（2026-07-28）

- 独立 Review 输入与结论：与写入上下文隔离的只读 Reviewer 完成本轮代码、schema/fixtures 和 byte oracle 检查；`workspace writes=None`，结论 `Needs Fix`，`P0/P1/P2/P3=0/4/0/0`。
- `repair_chain_id`: `DASHBOARD-BE-001-RC-001`
- `attempt_id`: `DASHBOARD-BE-001-RC-001-A1`
- `finding_ids`: `DASHBOARD-BE-001-P1-001;DASHBOARD-BE-001-P1-002;DASHBOARD-BE-001-P1-003;DASHBOARD-BE-001-P1-004`
- `closure_contract_hash`: `B2358B9B69CD86D01A980AEE49B9F35F1ED3D573FAD1815A075C92CBD0C433BC`
- `allowed_files_hash`: `3283B4FE4B48DE449FE8041D6D58F38722E2AD2BDF7C5EEA9D635F333C062173`
- RED：`P1-001` 显式 `parallel_intent=serial` 仍可能得到 candidate；`P1-002` schema 可接受 axis/value、edge type/direction/condition 混装且 SSE 未绑定 id/revision；`P1-003` 有 Core error 的前置 TASK 仍可满足依赖并升级动作；`P1-004` 定向测试硬编码旧 lifecycle，真实运行 `51` 项中失败 `1`，原收据失真。
- 修复：三值并行意图在其他候选检查前 fail-closed；8 个 dependency axis 与 5 种 edge shape 使用 schema `oneOf` 判别约束；SSE 只接受精确 event 字段并要求 `id == data.revision`；关系引擎接收目标 diagnostics，使 Core parse/state-guard/相关轴 error 或缺 provenance 的条件为 unknown；Gateway 集成测试改为与同一冻结窗口的公开 facade 报告对照。
- GREEN：修复后 dashboard backend 定向测试实际 `55/55 Passed`；新增 9 种双边意图组合、8 轴 expected/actual、5 edge shape、SSE 缺失/额外字段与 revision mismatch、target guard/axis conflict/missing provenance 负向用例均通过；ai-dev-flow 完整回归 `81/81 Passed`；schema/SSE 测试两轮各 `10/10 Passed`，合同集合 `files=10`、digest `9722b70bd5c26491a79d424a184fc4784df41c55f75191f2a2c7031436db9c28`。
- SIGNAL：target lint `errors/violations/warnings=0/0/1`，唯一 warning 为未提交 diff 无法由 Git 历史证明 lifecycle 流转；project lint `19/0/27`，19 个 error 均来自本任务范围外的既有 Legacy TASK，本任务相关只有上述 transition warning 与 TASK_BOARD legacy warning；diff-scope `outside=0`；标准 `git diff --check` 通过，32 个非 SSE 新文件的扩展 whitespace 检查为 `issues=0`，`events.sse` 因 wire contract 固定双 LF 由 byte oracle 单独验证；前两次无输出超时不计 Review 轮次或 finding。
- 当前处置：保持 `Review Pending / UA3 Pending / Uncommitted / Unmerged`；4 个 finding 已形成修复候选，但只能由下一次独立只读复审判定 Closed，不自批、不提交。

## 实现 Repair Round 2（2026-07-28）

- A1 独立复审：只读 Reviewer 确认 `DASHBOARD-BE-001-P1-001` 至 `P1-004` 全部 Closed，同时稳定新增 `P1-005` 至 `P1-009`；结论 `Needs Fix`，`P0/P1/P2/P3=0/5/0/0`，`workspace writes=None`，未发现这 5 项之外的其他 P0/P1。
- `repair_chain_id`: `DASHBOARD-BE-001-RC-001`
- `attempt_id`: `DASHBOARD-BE-001-RC-001-A2`
- `finding_ids`: `DASHBOARD-BE-001-P1-005;DASHBOARD-BE-001-P1-006;DASHBOARD-BE-001-P1-007;DASHBOARD-BE-001-P1-008;DASHBOARD-BE-001-P1-009`
- `closure_contract_hash`: `292AC1F59818B53D4CD53B67392A21942C7BAAE66DFBB2AEA7A30B43E7F2FEC7`
- `allowed_files_hash`: `A9FC14423CFCE450B846BD23244687499E73F678B517013881B9B0840FF705A6`
- RED：`P1-005` 缺失/legacy/unsupported Scheduling 仍可能升级动作且字段错误阻断范围不准；`P1-006` ParallelEngine 不消费 blocking diagnostics；`P1-007` dependency cycle 未回灌到指向错误 target 的下游条件；`P1-008` A→B→A 可混合 Reader B 与 Scheduling A；`P1-009` wire schema 非法暴露 Reader 内部 `Not Recorded` sentinel。
- 修复：动作引擎把 absent/legacy 的 Ready/In Progress 固定为 unknown，把 structural invalid/unsupported schema 固定为整体 unknown，只让 `depends_on` 字段错误阻断依赖动作而不扩大 branch/path/lock/risk 单字段错误；并行引擎显式接收 diagnostics，Core parse/state-guard、unsupported schema、并行相关轴错误或无法解析的 diagnostic ID 均不得 candidate；关系环诊断生成后计算 cycle 及下游闭包并二次把相关 dependency condition 置为 unknown；冻结输入在 Reader 前、Reader 后和发布前核对 file set、size、mtime_ns、ctime_ns、file identity 与 SHA256，Gateway 同时核对 report source set，A→B→A 反例在 Scheduling parse 前拒绝；领域适配把 `Not Recorded` 映射为 wire `null`，schema 删除该枚举。
- GREEN：dashboard backend 定向测试实际 `67/67 Passed`；新增 action 字段边界、真实 parser unsupported schema、TaskNode blocking diagnostic、A↔B 与 C→A、Reader window ABA、wire sentinel 正反例均通过；ai-dev-flow 完整回归 `81/81 Passed`；schema/SSE 测试两轮各 `11/11 Passed`，合同集合 `files=10`、digest `0242c53017ca11f405494266cc68c5930019dc19bae1dde61a7f3457ead60907`。
- SIGNAL：target lint `errors/violations/warnings=0/0/1`，唯一 warning 为未提交 diff 无法由 Git 历史证明 lifecycle 流转；project lint `19/0/27`，19 个 error 均来自本任务范围外的既有 Legacy TASK，本任务相关只有上述 transition warning 与 TASK_BOARD legacy warning；diff-scope `outside=0`；标准 `git diff --check` 通过，32 个非 SSE 新文件扩展 whitespace 检查 `issues=0`，`events.sse` 的合同双 LF 继续由 byte oracle 验证。
- 当前处置：保持 `Review Pending / UA3 Pending / Uncommitted / Unmerged`；A2 只形成修复候选，`P1-005` 至 `P1-009` 是否 Closed 由下一次隔离只读独立复审判定，不自批、不提交。

## 实现 Repair Round 3（2026-07-28）

- A2 独立复审：只读 Reviewer 确认 `DASHBOARD-BE-001-P1-005`、`P1-007`、`P1-009` Closed，旧 `P1-001` 至 `P1-004` 继续 Closed；`P1-006` 与 `P1-008` Open，结论 `Needs Fix`，`P0/P1/P2/P3=0/2/0/0`，`workspace writes=None`。
- 授权：用户明确授权在原精确 allowlist 和同一 repair chain 内实施一次有限 A3；这是基础 AutoRepair 两轮后的用户授权修复，不扩大任务、文件或交付权限。
- `repair_chain_id`: `DASHBOARD-BE-001-RC-001`
- `attempt_id`: `DASHBOARD-BE-001-RC-001-A3`
- `finding_ids`: `DASHBOARD-BE-001-P1-006;DASHBOARD-BE-001-P1-008`
- `closure_contract_hash`: `C7E9B0F71E30F554720BED48DBB1D6CB2002B9C6FA9DBB76E20E8717DEE311C0`
- `allowed_files_hash`: `B39800110CB376119E9715380E1841134083CCB60F5F482EA496C02984F7337D`
- RED：`P1-006` 未覆盖 `task_type`、`task_class` 等实际并行输入的非法/冲突 diagnostic，Accepted-contract owner 的必需轴也未 diagnostic-aware fail-closed；`P1-008` 仅凭 metadata、hash 和 file identity 无法拒绝对抗性 A→B→A。
- 修复：并行引擎把参与判断及 Accepted-contract exception 的 Core/Scheduling 轴纳入 diagnostic-aware 阻断，`task_type`/`task_class` 非法和 owner `commit_status` 冲突均为 unknown，同时保留 `REPLACES_CYCLE` 非相关轴不阻断；冻结输入在 Windows 用标准库 `ctypes` 为完整 TASK 集合获取 `CreateFileW` 只读租约，只共享 READ，不共享 WRITE/DELETE，并在读取冻结 bytes 前完成租约和二次集合核对，持有到公开 Reader、Scheduling、关系/动作/并行、最终校验与返回发布完成，异常路径释放；非 Windows 明确 fail-closed，原 metadata/hash/identity 仅保留为纵深校验。
- GREEN：dashboard backend 定向测试实际 `74/74 Passed`；新增 task type/class diagnostic、Accepted owner conflict、`REPLACES_CYCLE` 防过度阻断、未租约 Gateway、非 Windows fail-closed 和真实 Windows 写/mtime/rename/replace/delete/预存可写句柄/并发只读/释放后写入反例；ai-dev-flow 完整回归 `81/81 Passed`；schema/SSE 测试两轮各 `11/11 Passed`，合同集合 `files=10`，两次清单摘要均为 `a82d612330d88fb43454720b400118b5ccd3d06ef0ff62e2b6ef089ffac218c8`。
- SIGNAL：target lint `errors/violations/warnings=0/0/1`；project lint `19/0/27`，与 A2 基线一致，19 个 error 均来自本任务范围外的既有 Legacy TASK，本任务相关仍只有 transition warning 与 TASK_BOARD legacy warning；diff-scope `changed=35`、`outside=0`、`staged=0`；`git diff --check` 通过，32 个非 SSE 新文件扩展 whitespace 检查 `issues=0`，`events.sse` 无 CR 并保留合同双 LF。
- 当前处置：保持 `Review Pending / UA3 Pending / Uncommitted / Unmerged`；A3 只形成修复候选，`P1-006` 与 `P1-008` 是否 Closed 由下一次隔离只读独立复审判定，不自批、不提交。

## 实现 Repair Round 3 最终独立复审（2026-07-28）

- Reviewer：与写入上下文隔离的独立只读 Reviewer；`workspace writes=None`；审查前后内容 manifest 均为 `0f792d47aa663ba239957d25a3dd8d328e1c753e3d5501e43ba4db2dc0830fad`。
- 结论：`Passed`，`P0/P1/P2/P3=0/0/0/0`；`DASHBOARD-BE-001-P1-006`、`DASHBOARD-BE-001-P1-008` Closed，`P1-001` 至 `P1-005`、`P1-007`、`P1-009` 继续 Closed，`DASHBOARD-001-P2-006` 回归通过。
- P1-006 关闭证据：19 个并行相关轴 fail-closed；Accepted-contract owner 的 13 个关键轴 conflict 均不能使用 exception；仅有 `REPLACES_CYCLE` 时仍保持 candidate。
- P1-008 关闭证据：Windows 64-bit `CreateFileW` ABI、全量 TASK handle 先于 bytes、预存可写 handle 拒绝租约、部分获取失败释放已持有 handle、写入/rename/replace/delete/A→B 写入均被阻断、mtime 变更由发布前纵深校验拒绝、新增 TASK 被拒绝、并发只读成功、释放后恢复写入、非 Windows fail-closed；租约覆盖 Reader、Scheduling、关系、动作、并行、最终校验与结果构造。
- Reviewer 验证：`unittest discover 74/74`、backend pytest `74/74`、ai-dev-flow `81/81`、schema/fixtures/SSE `11/11 × 2`，合同 digest `a82d612330d88fb43454720b400118b5ccd3d06ef0ff62e2b6ef089ffac218c8`；target lint `0/0/1`；project lint `19/0/27` 且仅为范围外既有 CONTRACT-001～006 Legacy diagnostics；diff-check、whitespace、scope、无 pycache、`staged=0` 均通过。
- 状态边界：推进到 `Ready / Review Passed / UA3 Pending / Uncommitted / Unmerged`；独立 Review 不代替用户 UA3，不授权 commit、stage、merge、push、Accepted 或 Closed。

## DASHBOARD-BE-001 UA3 2026-07-28

- 用户反馈：用户明确回复“验收通过”。
- 验收范围：确认 BE-001 后端核心的功能边界、保守 fail-closed 行为、共享 wire contract、自动验证与最终独立 Review 证据。
- 验收结果：`UA3 Passed / User Confirmed`；据此将 lifecycle 推进为 `Accepted`。
- 写回复核：target lint `errors/violations/warnings=0/0/2`，仅保留未提交 transition 与 Markdown 无法证明用户身份两项预期 warning；project lint `19/0/28`，19 个 error 仍全部来自范围外既有 CONTRACT-001～006 Legacy 文档；diff-scope `changed=35/outside=0/staged=0`，`git diff --check` 通过。
- 权限边界：本次用户反馈只构成 UA3 与 Acceptance authority，不授权 commit、stage、merge、push、release、Closed 或执行 BE-002、FE-001、INTEGRATE-001。

## DASHBOARD-BE-001 合法提交历史重建 2026-07-28

- 用户授权：用户在发现原本地提交缺少 lifecycle 中间历史后，明确授权重建尚未 push 的 BE-001 提交历史。
- 恢复点：旧 main merge `7f65f3b27afa449b48c518c09d1e0ae71c3c405c` 与旧 feature `bed4d78297c95782d04d692f1db7108490da8353` 已分别保存在 `backup/dashboard-be-001-main-7f65f3b`、`backup/dashboard-be-001-feature-bed4d78`。
- 合法流转：`Ready → In Progress` 提交为 `00f8ac54e7ef7b05d5ab76c5cfd2baf480b91ac9`；`In Progress → Review` 提交为 `6c09982a83112d6dbaf362019820b83e91d87e74`；本提交保存 `Review → Accepted`、最终 Review/UA3 收据和已审查实现树。
- Windows 交付修正：在允许的 `dashboard/contracts/**` 内新增局部 `.gitattributes`，固定 `events.sse` 为 `text eol=lf`；wire bytes 保持 312 bytes、无 CR、结尾精确双 LF。
- 状态边界：`Accepted / Review Passed / UA3 Passed / Committed / Unmerged`；用户已授权后续合并，但尚未 push、release 或 Closed。

## Outcome

- Base / Diff：base=c5bbf3a0d6178fc3a4ea83e3066df92b8f72e958;diff=c5bbf3a0d6178fc3a4ea83e3066df92b8f72e958..codex/dashboard-be-001
- 修改文件：新增 `dashboard/backend/pyproject.toml`、`dashboard/backend/src/ai_dev_flow_dashboard/__init__.py`、`dashboard/backend/src/ai_dev_flow_dashboard/core/**`、`dashboard/backend/tests/be001/**`、`dashboard/contracts/**`；同步本 TASK 与 TASK_BOARD 投影。未修改 `skills/ai-dev-flow/**`、其他 TASK、前端或发布文件。
- 验证证据：dashboard backend 定向测试 `74/74 Passed`；schema/8 JSON fixtures/SSE transcript 两轮各 `11/11 Passed`，合同集合 `files=10`、两次清单摘要均为 `a82d612330d88fb43454720b400118b5ccd3d06ef0ff62e2b6ef089ffac218c8`；ai-dev-flow 完整回归 `81/81 Passed`；Review baseline target lint `0/0/1`，UA3 写回后 target lint `0/0/2`；Review baseline project lint `19/0/27`，UA3 写回后 project lint `19/0/28`，19 个 error 均为任务范围外既有 Legacy diagnostics；diff-scope `changed=35/outside=0/staged=0`，`git diff --check` 与 32 个非 SSE 新文件扩展 whitespace 检查通过，SSE 双 LF 由 byte oracle 保留并验证。
- Review findings：A3 最终独立只读复审 `Passed`，`P0/P1/P2/P3=0/0/0/0`；`P1-001` 至 `P1-009` 全部 Closed，`DASHBOARD-001-P2-006` 回归通过；Reviewer workspace writes=None。
- UA 动作与结果：用户已查看任务说明与验收范围并明确回复“验收通过”；`UA3 Passed / User Confirmed`。
- 隔离位置：Worktree `D:\open-source\ai-dev-flow-wt\dashboard-be-001`；branch `codex/dashboard-be-001`。
- 回滚方式：旧提交均由只读 backup refs 保留；未经用户明确授权不删除备份、不 reset 或再次改写历史。
- 状态边界：`Accepted / Review Passed / UA3 Passed / Committed / Unmerged`；未 merge、未 push、未 release、未 Closed。
- 剩余风险：实现尚未合并到本地 `main`；Windows 文件共享租约已通过真实 OS 对抗测试，非 Windows 会按合同 fail-closed；BE-001 不包含 Git/watcher/HTTP/SSE server/frontend。
- 下一步：按用户授权将 `codex/dashboard-be-001` fast-forward 合并到本地 `main`，再写入 Merged 交付收据；不自动执行后续任务。
