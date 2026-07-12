# CONTRACT-002：建立 Golden fixtures 与填写量基线

## 任务元数据

| 字段 | 当前值 |
|---|---|
| 任务编号 | `CONTRACT-002` |
| 任务类型 | 测试数据 / 文档 |
| 当前模式 | 用户已完成 UA3 证据确认，任务已验收 |
| 下一允许模式 | 保持已验收（`Accepted`）；允许后继任务验证祖先关系后进入 Ready |
| 任务状态 | 已验收（`Accepted`） |
| 优先级 | 高 |
| 风险等级 | 中 |
| 任务分级 | C：建立多目录机器 oracle，并成为后续 Reader 的测试基线 |
| 执行位置 | v0.7 顺序独立分支或 Worktree；保持独立 diff |
| 独立审查 | 必须 |
| 用户动作等级 | UA3：用户查看 coverage、样本来源和验证证据 |
| 前置任务 | `CONTRACT-001` 达到 `Accepted` |
| Batch / Wave | 禁止；Single Task |

## 背景

Reader 和 lint 不能以“实现跑通”为准反向定义规则。必须先把合法输入、违规输入、legacy 冲突和期望 diagnostics 固化为独立 golden fixtures，并用真实 Git 变更回填 A/B TASK，证明 Compact Core 确实降低填写量。

## 目标

- 建立 `valid / violations / legacy / comparisons` 四类 fixture。
- 为首批每条核心不变量和 diagnostic 提供可机器读取的预期结果。
- 明确 legacy 冲突时“不产生确定 normalized 值”的 oracle。
- 用本仓库三个真实 Git 变更回填 legacy 与 Compact 两种任务表示并量化差异。
- 让 `CONTRACT-003` 可以先看到稳定 RED，再实现 Reader。

## 真实样本来源

只使用本仓库已提交、无私有业务数据的变更：

- `81a8837`：README 验收反馈闸门更新。
- `12b3dc0`：验收反馈闸门文档收紧。
- `4a6c417`：RED/GREEN/SIGNAL 顺序门禁收紧。

这些 comparison 必须标注为“基于真实 Git 变更回填”，不得声称历史上已经存在对应 TASK。

## 非目标

- 不实现 Reader、Validator、`inspect()`、CLI 或 TASK_BOARD Adapter。
- 不修改语义规范来迁就 fixture。
- 不用人为最短示例冒充“真实 A/B 样本”。
- 不引入 pytest、jsonschema、Markdown parser 或其他第三方依赖。
- 不修改 Skill、Prompt、模板、版本或发布文件。

## 允许修改范围

- 新增 `skills/ai-dev-flow/tests/fixtures/README.md`
- 新增 `skills/ai-dev-flow/tests/fixtures/manifest.json`
- 新增 `skills/ai-dev-flow/tests/fixtures/coverage.md`
- 新增 `skills/ai-dev-flow/tests/fixtures/valid/`
- 新增 `skills/ai-dev-flow/tests/fixtures/violations/`
- 新增 `skills/ai-dev-flow/tests/fixtures/legacy/`
- 新增 `skills/ai-dev-flow/tests/fixtures/comparisons/`
- 新增 `skills/ai-dev-flow/tests/fixtures/projects/`
- 本任务文件和 `docs/TASK_BOARD.md` 的状态/证据字段

## 禁止修改范围

- `skills/ai-dev-flow/references/WORKFLOW_CONTRACT.md`
- `skills/ai-dev-flow/schemas/workflow-contract.schema.json`
- `skills/ai-dev-flow/scripts/`
- `skills/ai-dev-flow/SKILL.md`
- `skills/ai-dev-flow/references/PROMPTS.md`
- 现有模板、VERSION、CHANGELOG 和三个来源 commit
- 私有项目文件、本机绝对路径、账号、密钥或未脱敏业务内容

## Readiness Gate

- [x] `CONTRACT-001` 已 `Accepted`，字段、枚举、不变量和诊断码已冻结；Accepted commit 为 `28e74f8`。
- [x] `git merge-base --is-ancestor 28e74f8 28e74f8` 成功。
- [x] JSON Schema 与语义规范一致且可被标准 JSON parser 读取。
- [x] 三个来源 commit 在当前 Git 历史中存在。
- [x] Base commit、HEAD、执行位置和 Diff 范围已记录。

## 建议 fixture 布局

```text
skills/ai-dev-flow/tests/fixtures/
├─ README.md
├─ manifest.json
├─ coverage.md
├─ valid/
│  └─ task-a-document.md
├─ violations/
├─ legacy/
├─ comparisons/
│  └─ <commit>/
│     ├─ legacy-task.md
│     ├─ compact-task.md
│     └─ metrics.json
└─ projects/
   └─ valid-project/
      └─ docs/tasks/
```

`manifest.json` 是测试 oracle，不是第二份 TASK 状态真相源。

### 填写量计数规则

- 所有 comparison 在同一个 lifecycle checkpoint 比较，首批统一使用 `Review`。
- `required_input` 指为使该 checkpoint 的 TASK 语义完整而必须由作者提供的一个独立事实；标题、Markdown 标记、派生默认值和自动生成 provenance 不计数。
- 同一事实即使换行或换标题仍只计 1；同一状态轴在两个位置要求作者重复填写时，第一次计 required input，后续每次分别计入该格式的 duplicate state occurrences。
- 目标、范围、完成标准、验证和证据在 legacy/Compact 两侧使用同一内容，不能靠删减业务事实让 Compact 变短。
- 每个 comparison 在 `manifest.json` 固定记录 `lifecycle_checkpoint`、`legacy_required_inputs`、`compact_required_inputs`、`legacy_duplicate_state_occurrences` 和 `compact_duplicate_state_occurrences`。

## 执行步骤

1. 从 `WORKFLOW_CONTRACT.md` 建立 invariant/diagnostic coverage matrix。
2. 先写 parsing、枚举、状态、UA7、merge authority、feedback gate 和 legacy conflict 的正反输入。
3. 为每个 fixture 记录唯一 ID、输入、期望 normalized 字段、精确 diagnostic 集合和阶段标签。
4. 用三个真实 commit 分别回填 legacy 与 Compact 版本，记录所需填写项、重复状态数和证据段落数。
5. 使用标准库和 PowerShell 验证 manifest、路径、ID 唯一性与 coverage 引用。
6. 独立 Review 后更新任务状态，不开始 Reader 实现。

## 完成标准

- [x] 每个 fixture 有唯一 ID、真实输入路径和确定 expected result。
- [x] 首批每条核心不变量至少有一个正例和一个反例。
- [x] 首批每个 `E_* / V_* / W_*` diagnostic 至少有一个 fixture。
- [x] `V_OVERLAY_WEAKENS_CORE` 标记为 `future_contract_007`，不冒充首批已实现。
- [x] 覆盖重复 key、未知 key/value、ID 冲突、状态门禁、UA7、merge authority 和 feedback scope。
- [x] legacy Review/merge 冲突明确预期 `E_LEGACY_CONFLICT`，且不产生确定 normalized 值。
- [x] 未知 optional extension 保留并 warning；未知 required extension 按规范产生阻塞诊断。
- [x] 三个真实样本均包含 legacy、Compact 和度量表。
- [x] 每个 Compact 样本只有 8 个核心字段，不靠一排 `N/A / Not Applicable` 填充。
- [x] 三个样本的 `compact_required_inputs` 均小于 `legacy_required_inputs`。
- [x] 三个样本的 `compact_duplicate_state_occurrences` 均为 0，且严格小于对应的 `legacy_duplicate_state_occurrences`。
- [x] fixture 不含私有路径、账号、密钥或项目外业务信息。
- [x] 存在 `projects/valid-project/docs/tasks/` 形状的目录 fixture，用于验证 public project-root target，不把任意 fixture 目录当项目根。
- [x] 独立 Review 无 P0/P1。

## 验证方式

```powershell
git status --short
git diff --name-only
git diff --check
Get-Content -Raw skills/ai-dev-flow/tests/fixtures/manifest.json | ConvertFrom-Json | Out-Null
rg -n "81a8837|12b3dc0|4a6c417" skills/ai-dev-flow/tests/fixtures/comparisons
rg -n "E_LEGACY_CONFLICT|V_REVIEW_GUARD|V_UA_GUARD|V_SIGNAL_GATE|V_DELIVERY_AUTHORITY" skills/ai-dev-flow/tests/fixtures
rg -n "compact_required_inputs|legacy_required_inputs|legacy_duplicate_state_occurrences|compact_duplicate_state_occurrences" skills/ai-dev-flow/tests/fixtures/comparisons
$m = Get-Content -Raw skills/ai-dev-flow/tests/fixtures/manifest.json | ConvertFrom-Json
foreach ($c in $m.comparisons) {
  if ($c.lifecycle_checkpoint -ne 'Review') { throw "checkpoint mismatch: $($c.id)" }
  if ([int]$c.compact_required_inputs -ge [int]$c.legacy_required_inputs) { throw "Compact not smaller: $($c.id)" }
  if ([int]$c.compact_duplicate_state_occurrences -ne 0) { throw "Compact duplicate state remains: $($c.id)" }
  if ([int]$c.compact_duplicate_state_occurrences -ge [int]$c.legacy_duplicate_state_occurrences) { throw "Compact duplicate count not lower: $($c.id)" }
}
```

还需用标准库或 PowerShell 检查：

- manifest ID 唯一。
- 每个 input 路径存在。
- coverage 中引用的 fixture ID 全部存在。
- 每个 expected diagnostic 均存在于 `WORKFLOW_CONTRACT.md`。
- fixture 创建前后的三个来源 commit 未发生改变。

## 执行与验证记录

- 新增 `skills/ai-dev-flow/tests/fixtures/`，共 33 个文件；包含 21 个 diagnostic fixture、3 个真实变更 comparison，以及 README、coverage 和 manifest。
- `manifest.json`：固定唯一 ID、真实相对输入路径、expected normalized 片段、精确 diagnostic 集合和阶段标签。
- `coverage.md`：覆盖全部首批 `E_* / V_* / W_*`，并把 `V_OVERLAY_WEAKENS_CORE` 明确标为 `future_contract_007`。
- Legacy oracle：Review 与 merge 冲突均预期 `E_LEGACY_CONFLICT`，冲突轴 normalized 值为 `null`。
- Comparison：逐事实 ledger 可机械复算；三个样本均为 19→18、重复 2→0。唯一 Legacy-only required input 是现有 A/B 模板建议必填、但规范明确不持久化进 Contract 的 `current_mode`；来源绑定 `TASK_TEMPLATE.md:7-13`。
- 标准库验证：通过；24 个 fixture/comparison ID 唯一，所有 input 存在，所有 expected diagnostic 均在规范中，三个 Compact 样本恰好只有 8 个核心字段。
- PowerShell JSON 解析：所有 JSON 文件通过；三个来源 commit 仍可由 `git cat-file -e` 解析。
- `git diff --check`：通过；仅有现有 Windows LF/CRLF 策略 warning。
- 未实现 Reader、Validator、CLI、Adapter，也未修改规范、Schema、Skill、Prompt、模板或版本文件。

## 停止条件

- `CONTRACT-001` 仍有未决语义或未 Accepted。
- expected diagnostic 需要猜测。
- fixture 暴露规范冲突；应回到 `CONTRACT-001`，不得在 fixture 中自行定规则。
- 三个真实样本无法从仓库历史重建。
- Compact 版本没有稳定减少填写项或仍需大量 N/A。
- 必须提前实现 Reader 或引入外部依赖才能验证 fixture。

## 代码审查

- 审查状态：最终复审通过
- 审查人或审查 agent：Codex 独立 Reviewer（2 轮 repair 后最终复审）
- 审查严重等级：无 P0/P1；保留 1 类 P2 文档定位精度项
- P0 / P1 必须修改项：
  1. board drift fixture 表头不属于 canonical 或 legacy 精确别名，实际会先触发 `E_BOARD_PARSE`。
  2. feedback/signal fixture 未使用精确字段、值、标题，且缺少 In Progress C 级正文门禁。
  3. Legacy authority fixture 处于 Accepted 但未补齐 Review、UA、Outcome 门禁，exact diagnostics 漏报。
  4. comparison 只声明总数，缺逐事实 ledger，且 Compact 不满足 Review checkpoint 正文语义。
- 审查结论：通过；原 P1 全部关闭
- 是否允许进入验收建议：是（UA3）

## 审查-修复循环（review_repair_loop）记录

- 当前轮次：1 / 2。
- 修复输入：第 1 轮独立 Review 的 4 项 P1。
- 修复范围：fixture、manifest、coverage、本任务文件与 TASK_BOARD；未修改规范、Schema、Reader、CLI、Skill、Prompt 或模板。
- P1-1：board drift 改为规范规定的 9 列 Canonical 中文表头，保留 lifecycle drift 与 orphan row 两个目标信号。
- P1-2：feedback/signal 改为精确字段、精确枚举、精确 repair intent 和 real_env_signal 标题，并补齐 C 级 In Progress 正文门禁。
- P1-3：Legacy authority 改为语义完整的 Review checkpoint，补齐 Review、UA evidence、Base/Diff、修改文件、验证证据与 commit 状态，只保留 legacy/authority warnings。
- P1-4：三个 comparison 均改成语义完整的 Review TASK；metrics 新增逐事实 ledger、位置映射、事实值和 duplicate ledger，可机械复算 22/23/24→18 与 3→0。
- 修复验证：24 个 ID 唯一、33 个文件路径存在、diagnostic 均属于规范、ledger 汇总与 manifest/metrics 一致、三个 Compact 前 8 字段精确为 core 且无 N/A、三个来源 commit 仍存在、全部 JSON 可解析、`git diff --check` 通过。
- 未处理意见：无。
- 下一步：提交修复候选并进行独立复审。

### 第 1 轮复审结果

- 已关闭：feedback/signal 精确 grammar；Legacy authority 的主要 Review/UA/Outcome 门禁。
- 未关闭 P1：4 个 tracked fixture 的 `Ready -> Draft` 会形成可证明非法历史；comparison ledger 对 required input 与 duplicate 的语义证据不足。
- P2：canonical authority fixture 应包含 `W_AUTHORITY_UNVERIFIABLE`。
- P3：Legacy authority 文案仍误写 Accepted。
- 结论：不允许进入 UA3；进入第 2 轮（最后一轮）有限修复。

### 第 2 轮修复记录

- 4 个 lifecycle fixture 恢复 `Ready` 并补齐合法最小正文；当前父快照为 Draft，因此本轮 `Draft -> Ready` 合法，避免把正文缺失或非法逆向流转写入 oracle。
- canonical UA7/close authority 反例补入 `W_AUTHORITY_UNVERIFIABLE`；Legacy 文案改为 Review fixture。
- 三个 Legacy comparison 增加精确 `验收反馈状态=无反馈`，与 Compact `ua_status=Pending` 对齐。
- comparison 文件改为以 `CMP-*` task_id 开头的合法文件名，并同步 manifest。
- ledger 删除 priority/risk/next mode 等非必需输入；仅保留 `TASK_TEMPLATE.md:7-13` 明确建议 A/B 必填、但 Contract 明确不持久化的 `current_mode`，三个样本均为 19→18。
- duplicate ledger 删除错误的 `lifecycle@current_mode`，只保留 Review 状态与 UA level 的真实重复，三个样本均为 2→0。
- 本轮为 repair 上限 2 / 2；提交并验证后必须最终独立复审。

### 第 2 轮最终复审结果

- 结论：通过；无 P0/P1，允许进入 UA3。
- 原阻断项：全部关闭。
- P2 非阻塞项：三个 metrics 的 `ua_status` location 说明仍写旧路径“用户动作等级/待确认”，实际来源为“用户验收反馈 / 实机测试反馈/验收反馈状态：无反馈”；不影响事实一致、计数或 exact diagnostics，留作后续文档清理。
- P3：无。
- 完整审查范围：`28e74f8..2fd069e`；最终修复范围：`e8313b2..2fd069e`。

## Diff 审查

- 审查方式：post-commit diff
- 审查命令：待执行时填写
- 修改文件清单：待填写
- 范围越界文件：待审查
- 审查状态：最终复审通过
- 审查结论：完整任务范围无越界，无 P0/P1；允许进入 UA3

## 用户动作等级 / 验收建议

- 用户动作等级：UA3
- 用户需要做什么：查看 coverage、真实样本对比和 fixture 验证证据
- agent 已提供的证据：24 个唯一 ID、33 个 fixture 文件、全部 diagnostic coverage、JSON/路径/ledger/历史流转检查、三个真实 commit 来源、两轮独立 Review
- 是否允许关闭任务：否；本次授权为 Accepted 与继续后继任务，不包含 Closed 或 merge

## 用户验收反馈 / 实机测试反馈

- 验收反馈状态：通过；用户明确表示“CONTRACT-002 UA3通过，继续完成剩余部分”
- 当前反馈关联的 UA 等级：UA3
- 反馈分类：不适用
- 下一步建议：形成 Accepted commit 并验证祖先关系后启动 `CONTRACT-003`

## 合并状态

- 合并状态：未合并
- 合并目标：待执行时填写
- 合并说明：实际 merge 必须另获用户确认

## 提交 / 合并

- Commit 状态：实现 `c8626a1`、首审记录 `4da8643`、第 1 轮修复 `23fcb7d`、复审记录 `e8313b2`、第 2 轮修复 / 最终复审 HEAD `2fd069e`
- Commit hash：待填写
- Merge 状态：未合并
- 回滚方式：回退本任务独立 commit；执行时细化

## Git 与交接

- 当前分支：`codex/contract-002-golden-fixtures`
- 建档时 HEAD：`4a6c41781a028bf6c78c1283f16f5d120ee61ae1`
- 执行 Base commit：`28e74f8`（CONTRACT-001 Accepted commit）
- 计划分支：`codex/contract-002-golden-fixtures`
- Diff 范围：`28e74f8..HEAD`（实现候选待提交并独立审查）
- 下一任务：`CONTRACT-003`，仅在本任务 `Accepted` 后转为 `Ready`
- 不要重复尝试：为让后续代码通过而修改 expected oracle
