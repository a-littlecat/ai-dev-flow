# PROGRESS-VISIBILITY-001：统一跨 Worktree 进展可见性并瘦身任务看板

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `PROGRESS-VISIBILITY-001`
- `task_type`: `code`
- `task_class`: `C`
- `lifecycle`: `In Progress`
- `review_status`: `Passed`
- `ua_level`: `UA6`
- `ua_status`: `Pending`
- `commit_status`: `Uncommitted`

## 背景与价值判据

- 用户核心需求：打开仪表盘后 10 秒内回答"哪些任务在跑、卡在哪、下一个是什么"。
- 现状根因：后端快照只读取 `--project-root` 当前工作区的 `docs/tasks/*.md` 与 `docs/TASK_BOARD.md`（`dashboard/backend/.../snapshot/builder.py:493-501`、`:625`）；linked Worktree 只贡献 Git 元数据（`git_snapshot/collector.py` 的 branch→worktree 映射与 dirty 状态），从不读取 worktree 内的任务内容。任务在 worktree 分支执行时（如 `ADF-V010-*`），仪表盘完全不可见。
- 限时价值闸门（用户 2026-08-10 确认）：本任务交付后进入两周真实使用观察。达标（10 秒判据成立）则保留瘦身后的内核并停止新增治理特性；未达标则归档重流程，仅保留 TASK 模板、只读校验器与仪表盘小内核，不再继续投入。

## 目标与边界

- 目标：目标 1 为 Dashboard 跨 worktree 进展可见性，目标 2 为看板生成器与授权归档；明细如下。
- 目标 1（Dashboard）：发现合同改为 **worktree 优先**——先由 `git worktree list --porcelain -z` 的安全结果枚举候选 linked Worktree（排除 detached / locked / prunable，解析失败只报诊断不猜测），再读取各安全 worktree 的 `docs/tasks/*.md` 作为只读补充源并入快照；**不读取 worktree 的 `TASK_BOARD.md`**——看板只是投影、TASK 才是事实源，跨源看板仲裁被显式排除，任务状态一律从 TASK 文件派生。任务身份以 `task_id` 为准，不依赖任务先存在于主工作区、也不要求 TASK 带 `branch_hint`。前端明确标记任务来源（主工作区 / 具体 worktree）。同一 `task_id` 的选择规则按以下确定性顺序判定，禁止依赖 `git worktree list` 返回顺序，一切并列决胜按 worktree 根路径字典序（casefold）：(a) 主工作区含该 `task_id` 时主工作区内容进入公开快照；(b) 否则恰好一个安全 worktree 含该 `task_id` 时采用之；(c) 多个 worktree 含同一 `task_id` 且文件内容 SHA256 一致时视为一份，来源标记为字典序首个 worktree，全部来源列入 provenance；(d) 多个 worktree 内容不一致时不发布任何候选内容，只发布 `WT_TASK_CONFLICT` 冲突诊断（列出全部候选 worktree 及各自 SHA256）。冲突与异常产生稳定诊断（code / severity / provenance 见"冻结合同"节），不静默猜测；路径逃逸出 worktree 根、文件不可读、重复 `task_id` 均按诊断处理。
- 目标 2（看板生成器）：新增看板生成器，复用 `skills/ai-dev-flow/scripts/workflow_contract.py::_expected_board_projection()` 的既有 TASK→九字段状态表投影逻辑；生成器范围**只含任务状态表**，依赖链与下一动作不由生成器重复实现（Dashboard 的 SchedulingParser / ActionEngine 已提供该视图）。生成器为双模式：默认 `--check` 纯只读，显式 `--write` 才写 `TASK_BOARD.md` 生成区；写入必须 byte-stable（重复生成零 diff），人工区 byte-preserve。生成器是**独立命令**，`workflow_lint` 完全不接线、行为不变，生成器 `--check` 作为并列验证命令单独运行。`TASK_BOARD.md` 顶部标注"任务状态表为生成区，请勿手改；生成区标记范围外为人工维护区"，生成区以 `<!-- ADF-GENERATED:BEGIN -->` / `<!-- ADF-GENERATED:END -->` 显式包围。"当前有效授权"与叙事性"下一允许动作"属不可派生的授权事实，保留为生成区外的小型人工维护区，生成器 `--check` 校验其指向的任务状态一致性（指向已 Closed / 不存在任务即产生诊断，不自动改写）。历史授权流水由生成器的显式迁移模式**自动归档**：`## 当前授权边界` 整节按段落/列表项机械切分、原文逐字搬入 `docs/AUTHORITY_LOG.md`，不做"当前有效 / 历史"的语义判定——整节一律视为历史记录。迁移后看板人工区只保留用户当下重新声明的当前授权（一句话级别；未声明即为空，不存在机器误判授权有效性的问题）。生成器在迁移时按条目 ID 对账完整性（无遗漏、无重复），并在此后持续校验人工区引用完整性；归档不是 lint 或 `--check` 的副作用。
- 非目标：不修改 v0.10 各 worktree 分支内容；不引入网络写接口、数据库、自动同步或遥测；不改变 Review / UA / Accepted / delivery / Closed 的正交语义；不夹带 v0.10 架构重构（core split / console 等）内容；不改动 `artifact_guard` 的 Accepted 基线保护语义。
- 允许修改：`dashboard/backend/`、`dashboard/frontend/`、`dashboard/contracts/`、`dashboard/integration/`、`skills/ai-dev-flow/scripts/`（仅新生成器及其接线，不改既有 lint / repair_gate / 投影校验行为）、`skills/ai-dev-flow/tests/`（仅新生成器测试）、`skills/ai-dev-flow/dashboard/**`（仅由 `build_skill_runtime.py` 重建生成，含 `runtime-manifest.json`，禁止手工编辑）、`docs/TASK_BOARD.md`、新增 `docs/AUTHORITY_LOG.md`、本 TASK、上述范围对应测试。
- 禁止修改：`skills/ai-dev-flow/` 的 CORE policy 与 Contract schema（如需扩展另立 TASK）、v010 worktree 内容、已发布 tag / Release、其他项目、本机 Skill 安装目录（同步需单独授权）。
- 未授权动作：commit、merge、push、release、本机 Skill 安装目录同步、Accepted、Closed；均需用户逐项明确授权。

## 冻结合同（诊断与归档 oracle）

诊断 code / severity 冻结表：

| code | severity | 含义 |
|---|---|---|
| `WT_SOURCE_UNREADABLE` | warning | worktree 任务源不可读或路径逃逸出 worktree 根 |
| `WT_TASK_CONFLICT` | warning | 多个 worktree 同一 `task_id` 内容不一致；不发布候选内容 |
| `WT_SOURCE_LOST` | warning | 运行中 worktree 被锁定、删除或变为不可读，对应来源失效 |
| `BOARD_DRIFT` | error | 生成区内容与 TASK 投影不一致（`--check` 检出） |
| `BOARD_MANUAL_STALE_REF` | warning | 人工区引用指向已 Closed / Cancelled 任务 |
| `BOARD_MANUAL_UNKNOWN_REF` | warning | 人工区引用指向不存在的任务 |
| `ARCHIVE_MIGRATION_MISMATCH` | error | 授权归档迁移条目对账不一致或重复 |

- provenance 不新建结构：复用 Dashboard 现有公共合同的 `Diagnostic`（顶层 `code / severity / task_ids`）与 `Provenance[]`（`source_path / heading / field / line / raw_value / source_type`）；worktree 来源信息以对现有 `Provenance` 的兼容扩展表达（新增 `source_type` 取值），具体字段由实施者在既有 schema 兼容边界内冻结并记入 Outcome。
- 归档来源区块为 `docs/TASK_BOARD.md` 的 `## 当前授权边界` H2 节；迁移为整节机械归档：按段落/列表项切分（空行分隔的连续文本块为一个条目），条目 ID 格式 `AUTH-YYYYMMDD-NNN` 按原文顺序编号，对账键 = 条目 ID + 原段落 UTF-8 内容 SHA256；迁移完成要求来源条目数与归档条目数一致、对账键唯一、无内容改写；不做任何"当前有效 / 历史"语义判定，整节一律归档为历史。
- 实时刷新时限冻结为：安全 worktree 内 TASK 变更后 ≤2 秒产生新 snapshot revision 与 SSE 更新（与既有性能门禁口径一致）。
- 实施时冻结项（不再逐字冻结，由实施者按既有代码事实决定并记入 Outcome）：异常到诊断 code 的映射优先复用现有 `GIT_PARSE_ERROR` / `E_TASK_ID_CONFLICT` 等既有 code，不足再新增；`worktree_root` 的身份表示（canonical 绝对路径）与 `source_path` 的相对口径（相对所属 worktree 根）；`WT_SOURCE_LOST` 触发集统一为"worktree 被 locked / prunable / 删除 / 不可读，或其 TASK 源文件被删除 / 重命名"；快照失效语义采用"保留 last-known-good 并标记 stale"。

## 完成标准与验证

- 完成标准：以下勾选项全部完成。
- [ ] 在 4 个 `codex/v010-*` worktree 存在（且其 TASK 无 `branch_hint`）的情况下启动仪表盘，`ADF-V010-*` 任务状态可见（一律派生自 TASK 文件，不读取 worktree 看板），来源标记正确。
- [ ] 冲突选择规则生效：主工作区优先、单源采用、多源同 SHA 去重、多源不同内容只发 `WT_TASK_CONFLICT` 诊断不发布候选；诊断带冻结 code / severity / provenance；detached / locked / prunable worktree 不进入读取集；并列决胜不依赖 `git worktree list` 返回顺序。
- [ ] 运行中实时刷新：仪表盘已运行时修改一个安全 worktree 的 TASK，≤2 秒产生新 snapshot revision 与 SSE 更新且状态与来源正确；worktree 被 locked / prunable / 删除 / 不可读或其 TASK 源文件被删除 / 重命名时，保留 last-known-good 并标记 stale，同时产生 `WT_SOURCE_LOST` 诊断。
- [ ] 看板生成器落地：`--check` 全程只读（运行前后 Git 状态一致）；生成表与 TASK 内容 drift 为 0；`--write` 重复执行 byte-stable 且人工区块 byte-preserve；人工授权区块指向已 Closed / 不存在任务时产生诊断；授权归档按条目 ID 对账无遗漏、无重复。
- [ ] 后端、前端、集成测试与 `workflow_lint` 通过；artifact 门禁按阶段判定：Review 候选阶段要求 `baseline_preserved=true` 且 `candidate_consistent=true`，明确接受 `artifact_guard` 返回非零；获得独立授权并形成相应提交、更新 Accepted 基线后才要求 `accepted_ok=true`；候选阶段结果不得记为 Accepted artifact 全绿。
- [ ] `build_skill_runtime.py --check` 在运行时重建后通过，**仓库内**便携 Skill runtime 入口具备新功能；本机已安装 Skill 的同步与安装态验证不在本任务内。
- 验证命令或检查：`dashboard/README.md` 既有验证套件（后端 unittest、前端 `npm run verify`、Playwright、artifact_guard 按上述阶段判定），新增 worktree 聚合与生成器定向测试。"看板当前信息一屏可读"与两周 10 秒判据为 UA6 主观体验项，由用户真实使用观察确认，不作为自动完成标准，不以自动测试或 Reviewer 代替。

## Outcome

- Review Round 1（2026-08-10）：Codex 隔离只读复审结论 `Needs Fix`，P1×3 / P2×3，无 P0/P3。Kimi 独立核实后确认全部 6 项属实（`workflow_contract.py:354` 确有 `_expected_board_projection`；4 个 v010 worktree 的 `ADF-V010-*` TASK 确无 `branch_hint` / `Scheduling`），已就地在 Draft 内修复：目标 1 改为 worktree 优先发现合同；目标 2 修正复用模块、收窄为状态表投影、明确 `--check` / `--write` 双模式；完成标准改为 artifact 门禁分阶段判定；允许范围补入 `skills/ai-dev-flow/dashboard/**` 构建产物；诊断 / 归档 / UA6 体验项冻结 oracle。复审待定。
- Review Round 2（2026-08-10）：Codex 复审结论 `Needs Fix`；Round 1 findings 关闭 3 项（RVW-002/003/004），仍 Open 3 项，新增 P1×1 / P2×2。Kimi 逐项复核确认 5 项未决全部属实，已就地修复：RVW-001 残余 → 目标 1 补 (a)-(d) 确定性选择规则与字典序决胜，多源内容不一致只发诊断不发布候选；RVW-005 残余 → 完成标准改为"仓库内便携 runtime 入口具备新功能"，明确安装态验证不在本任务；RVW-006 残余 → 新增"冻结合同"节，落地诊断 code/severity 表、provenance 结构、归档来源区块与 `AUTH-YYYYMMDD-NNN` 对账键；R2-001 → 完成标准补运行中实时刷新（≤2 秒 SSE）与 `WT_SOURCE_LOST` 失效诊断；R2-002 → 看板标注改为生成区/人工区双区文案并以 `ADF-GENERATED` 标记包围；R2-003 → 生成器定为独立命令，`workflow_lint` 不接线。复审 Round 3 待定。
- Review Round 3（2026-08-10）：Codex 复审结论 `Needs Fix`；Round 2 修复关闭 4 项、Open 2 项，新增 P1×3 / P2×2。三轮整体趋势：Round 1 为致命设计缺陷，Round 2 为规则完备性，Round 3 已为合同措辞精度级。用户裁定"方案已经可以，不再逐字抠细节"，授权按降范围方式定稿、不再进行 Round 4 正式复审：R3-002 → 砍掉跨 worktree 看板聚合（回归 TASK 即事实源，看板不跨源仲裁）；R3-003 → 归档迁移降为人工一次性归类 + 生成器仅校验对账与引用完整性；R3-001 / R3-004 / R3-005 → 记入"实施时冻结项"（provenance 复用现有 `Diagnostic` / `Provenance[]` 兼容扩展、异常 code 优先复用既有、路径身份与 `WT_SOURCE_LOST` 触发集统一、失效语义为 last-known-good + stale），由实施者按既有代码事实决定并记入 Outcome。Draft 就此定稿，Review 状态保持用户裁决口径。
- 用户裁决补充（2026-08-10）：用户拒绝"人工搬移授权流水"，确认归档迁移改为生成器自动整节机械归档（无语义判定、整节视为历史），当前授权由用户在看板人工区按需重新声明。
- 验收与授权（2026-08-10）：用户明确"验收通过，提交然后进行实施"。据此记录：草稿验收通过（规划级验收），Review 状态按用户裁决口径记为 `Passed`（三轮正式复审结论为 Needs Fix，残余项已由用户裁决降范围或降为实施时冻结项，详见上条）；lifecycle 推进为 `In Progress`。授权范围：精确提交本 TASK 与看板索引形成 baseline，随后开始实施。UA6（两周真实使用 10 秒判据）保持 Pending，不以草稿验收代替。commit 之外的 merge、push、release、本机 Skill 安装目录同步、Closed 仍未授权。
- Base / Diff：base=733dc145aef833f433dd4fc639293465e9296a31
- 隔离位置：独立 Worktree `D:/open-source/ai-dev-flow-wt/progress-visibility-001`，分支 `codex/progress-visibility-001`。
- 回滚方式：删除该 Worktree 与分支即可整体回退；baseline 提交 `733dc14` 不含实现代码。
- 实施证据（2026-08-10，全部实跑）：
  - 目标 1（Dashboard 聚合）：新增 `core/worktree_tasks.py`（worktree 优先发现、(a)-(d) 确定性选择、last-known-good stale）；`engine.py` / `builder.py` / `models.py` / `contract_gateway.py` 接入聚合与失效检测；合同 schema 兼容扩展（`Provenance.source_type` 加 `worktree`，`TaskNode.worktree_root` 可选）；前端 `detailPanel` / `actionCenter` / `graphView` / `labels` 来源标记。实施时代理发现 `state-matrix.spec.mjs` 两处断言为 baseline 内 PR #13 遗留既有失败（git 历史证实），已随本任务修正；`test_build_skill_runtime.py` bundle 计数 37→38。
  - 目标 2（看板生成器）：新增 `skills/ai-dev-flow/scripts/board_generator.py`（`--check` 只读 / `--write` / `--migrate-authority-log` 三模式）与 15 个定向测试；既有 lint / repair_gate / 投影校验零改动。
  - 看板重建：授权流水 32 条机械归档至 `docs/AUTHORITY_LOG.md`（AUTH-20260810-001～032，逐字未改写、SHA256 对账）；看板 213→122 行，生成区以 ADF-GENERATED 标记包围；`--check` errors=0（22 条 warning 为人工区历史节对 Closed 任务的引用提示，不阻断，是否继续归档由用户决定）。
  - 验证数字：后端 unittest 187/187；集成 51/51；技能测试 106/106；前端 `npm run verify` 全绿（Vitest 95、Playwright 96）；`workflow_lint` errors=0；`build_skill_runtime.py --check` ok（37 文件 manifest）；artifact 门禁候选阶段 `baseline_preserved=true / candidate_consistent=true / accepted_ok=false`（候选记录已更新为 PROGRESS-VISIBILITY-001、57 文件，集成测试冻结断言同步更新）。
  - 真实冒烟：以主项目为 root 启动便携 runtime，快照 `fresh`、38 任务、`WT_TASK_CONFLICT`×7（4 个 v010 worktree 同名 TASK 内容互异，按用户裁定规则 (d) 只报冲突不发布内容）、来源 provenance 正确。
- Review findings：Round 1 P1×3/P2×3、Round 2 Open 3 + 新 P1×1/P2×2、Round 3 Open 2 + 新 P1×3/P2×2，全部经用户裁决关闭（降范围或降为实施时冻结项）；用户 2026-08-10 裁定多源冲突任务保持规则 (d) 只报冲突。
- 实施时冻结项的实际选择：provenance 复用现有 `Diagnostic`/`Provenance[]`（新增 `source_type="worktree"` 取值，字段 `worktree_root`/`sha256`/`worktree_source`）；`worktree_root` 为 canonical 绝对路径 posix；`WT_SOURCE_LOST` 触发集为 worktree 变 unsafe/不可扫描或曾贡献文件消失；失效语义为 last-known-good + `freshness="stale"`；异常 code 复用既有 `GIT_PARSE_ERROR` 等。
- 剩余风险与下一步：重启后 `_wt_last_good` 为空（`WT_SOURCE_LOST` 仅对运行中失效发射）；worktree TASK 的 Scheduling 拓扑探测用主 root 的 SchedulingParser；主工作区看板存在 1 条既有 `V_BOARD_DRIFT`（ACTION-CENTER/FOCUS-ASSESSMENT 行与 TASK 不一致，早于本任务）；实施 diff 已 stage 未 commit（commit 待用户授权）；本机已安装 Skill 仍为 0.9.2 旧运行时（同步未授权）。UA6 两周实测自用户验收后起算。
