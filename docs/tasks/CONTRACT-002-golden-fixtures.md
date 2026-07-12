# CONTRACT-002：建立 Golden fixtures 与填写量基线

## 任务元数据

| 字段 | 当前值 |
|---|---|
| 任务编号 | `CONTRACT-002` |
| 任务类型 | 测试数据 / 文档 |
| 当前模式 | 第 1 轮独立 Review 发现 P1，进入有限修复（`repair_task`） |
| 下一允许模式 | 完成第 1 轮修复与验证后重新进入独立审查 |
| 任务状态 | 需修复（`Needs Fix`） |
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
- [ ] 独立 Review 无 P0/P1。

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
- Comparison：`81a8837` 为 12→8、重复 3→0；`12b3dc0` 为 13→8、重复 3→0；`4a6c417` 为 14→8、重复 4→0。
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

- 审查状态：需要修改
- 审查人或审查 agent：Codex 独立 Reviewer（第 1 轮）
- 审查严重等级：P1（4 项）
- P0 / P1 必须修改项：
  1. board drift fixture 表头不属于 canonical 或 legacy 精确别名，实际会先触发 `E_BOARD_PARSE`。
  2. feedback/signal fixture 未使用精确字段、值、标题，且缺少 In Progress C 级正文门禁。
  3. Legacy authority fixture 处于 Accepted 但未补齐 Review、UA、Outcome 门禁，exact diagnostics 漏报。
  4. comparison 只声明总数，缺逐事实 ledger，且 Compact 不满足 Review checkpoint 正文语义。
- 审查结论：Needs Fix；不允许进入 UA3
- 是否允许进入验收建议：否；修复后重新独立 Review

## Diff 审查

- 审查方式：post-commit diff
- 审查命令：待执行时填写
- 修改文件清单：待填写
- 范围越界文件：待审查
- 审查状态：第 1 轮未通过
- 审查结论：范围无越界、JSON 与路径检查通过，但 oracle 精确性和 comparison 可审计性存在 4 项 P1

## 用户动作等级 / 验收建议

- 用户动作等级：UA3
- 用户需要做什么：查看 coverage、真实样本对比和 fixture 验证证据
- agent 已提供的证据：待执行后填写
- 是否允许关闭任务：否 / 待用户确认

## 用户验收反馈 / 实机测试反馈

- 验收反馈状态：无反馈
- 当前反馈关联的 UA 等级：UA3
- 反馈分类：不适用
- 下一步建议：等待任务执行、Review 和证据确认

## 合并状态

- 合并状态：未合并
- 合并目标：待执行时填写
- 合并说明：实际 merge 必须另获用户确认

## 提交 / 合并

- Commit 状态：实现候选待提交，提交后写回 hash
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
