# DASHBOARD-BE-001：实现任务关系与调度核心

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `DASHBOARD-BE-001`
- `task_type`: `code`
- `task_class`: `C`
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

## Outcome

- Base / Diff：base=c5bbf3a0d6178fc3a4ea83e3066df92b8f72e958;diff=uncommitted-worktree
- 修改文件：实现候选将在独立 Worktree 中严格限制于 BE-001 allowlist；当前提交只记录合法执行状态入口。
- 验证证据：执行入口、精确 base、独立 Worktree 和 allowlist 已只读核对；代码验证将在实现候选形成后运行。
- Review findings：implementation review 尚未开始；规划 Review Passed 不代替代码 Review。
- UA 动作与结果：UA3 Pending；用户尚未查看实现证据。
- 隔离位置：Worktree `D:\open-source\ai-dev-flow-wt\dashboard-be-001`；branch `codex/dashboard-be-001`。
- 回滚方式：实现尚未提交；如需停止只保留当前治理提交，不执行删除、reset 或历史改写。
- 状态边界：In Progress / Review Pending / UA3 Pending / Uncommitted / Unmerged；未 Accepted、未交付、未 Closed。
- 剩余风险：单字节 byte oracle 尚未由代码与测试实际验证；实现仍需严格限于 allowlist。
- 下一步：在独立 Worktree 实施 BE-001，完成验证后推进到 Review。
