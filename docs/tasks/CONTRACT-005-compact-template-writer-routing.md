# CONTRACT-005：启用 Compact Template 与最小 Writer 路由

## 任务元数据

| 字段 | 当前值 |
|---|---|
| 任务编号 | `CONTRACT-005` |
| 任务类型 | 工作流核心改动 / 模板 / Prompt |
| 当前模式 | 第 2 / 2 轮有限修复完成，等待最终独立复审（`review_task`） |
| 下一允许模式 | 最终复审通过后进入 UA6；仍有 P0/P1 时停止并人工接管 |
| 任务状态 | 待审查（`Review`） |
| 优先级 | 中 |
| 风险等级 | 高 |
| 任务分级 | D：修改核心 Writer 路由和多个长期入口 |
| 执行位置 | 必须独立 Worktree，Single Task |
| 独立代码/文档审查 | 必须 |
| 用户动作等级 | UA6：用户回归验收 legacy 与 Compact 两条核心流程 |
| 前置任务 | `CONTRACT-004` 达到 `Accepted` |
| Batch / Wave | 禁止；不得代码并行 |

## 背景

仅增加 Compact 模板会与当前 SKILL/PROMPTS 中硬编码的“代码审查”“Diff 审查”和两组合并字段发生冲突。Compact 启用前，必须先完成所有 TASK writer callsite inventory，并为 create、execute、review、diff-review、repair、acceptance、close 等入口建立明确的 Compact/legacy 路由。

## 目标

- 新增 `TASK_TEMPLATE_COMPACT.md`，只服务 v0.7 A/B 且无 Overlay 的新任务。
- 保留现有 `TASK_TEMPLATE.md` 作为 Full/Legacy 模板，不删除、不批量迁移。
- 建立完整 writer-callsite inventory。
- 对最小必要的 SKILL/PROMPTS/WORKFLOW 入口同步格式路由，防止 Compact TASK 重建旧状态字段。
- 用三个真实 A/B comparison 和 `workflow_lint` 证明 Compact 更轻且语义完整。

## 强制路由矩阵

| 任务条件 | Writer 选择 |
|---|---|
| 新建 A/B，`overlays=none`，无 Batch/Wave/real_env | Compact v0.7 |
| C/D | Full/Legacy |
| Batch 或 Wave | Full/Legacy |
| `real_env_signal` 或验收失败反馈 | Full/Legacy |
| 已存在 legacy TASK | 原格式继续维护，不自动迁移 |
| 格式或等级无法确定 | 停止并写待确认，不猜测 |

## Writer callsite inventory

执行时必须用全量搜索确认，而不是只修已知行。起始证据至少包括：

- `skills/ai-dev-flow/SKILL.md:208,285`
- `skills/ai-dev-flow/references/PROMPTS.md:39,90,245,260,378`
- `skills/ai-dev-flow/references/CODE_REVIEW_CHECKLIST.md:19`
- `skills/ai-dev-flow/references/AGENTS_COMPAT.md:113`
- 所有 create / execute / review / diff-review / repair / acceptance / close 入口
- 所有要求写回“代码审查”“Diff 审查”“合并状态”“提交 / 合并”的位置

## 非目标

- 不实现通用状态 Writer、自动迁移、批量重写或 Markdown 全文重排。
- 不把 C/D、Batch、Wave、`real_env_signal` 切换到 Compact。
- 不实现 Overlay Registry；它属于 `CONTRACT-007`。
- 不做 Prompt/Skill 全量文案收敛；它属于 `CONTRACT-008`。
- 不修改 TASK_BOARD projection；它属于 `CONTRACT-006`。
- 不接入 GPT‑5.6、外部 API 或第三方依赖。

## 允许修改范围

- 新增 `skills/ai-dev-flow/references/TASK_TEMPLATE_COMPACT.md`
- `skills/ai-dev-flow/references/TASK_TEMPLATE.md`：仅增加 Full/Legacy 标识与路由说明
- `skills/ai-dev-flow/SKILL.md`：仅同步最小格式选择和写回入口
- `skills/ai-dev-flow/references/PROMPTS.md`：仅同步必要 writer callsites
- `skills/ai-dev-flow/references/WORKFLOW.md`：仅同步格式路由边界
- `skills/ai-dev-flow/references/CODE_REVIEW_CHECKLIST.md`：仅增加 Compact/legacy 条件写回路由
- `skills/ai-dev-flow/references/AGENTS_COMPAT.md`：仅增加 Compact/legacy 条件写回路由
- `skills/ai-dev-flow/README.md`：仅修正安装清单和 create 示例路由（用户已批准扩围）
- `skills/ai-dev-flow/references/VALIDATION_GUIDE.md`：仅增加验证/验收记录的条件写回路由（用户已批准扩围）
- `skills/ai-dev-flow/references/ACCEPTANCE_GUIDE.md`：仅增加 acceptance/close 的条件写回路由（用户已批准扩围）
- Compact/legacy 路由测试与 comparison fixture
- 本任务文件和 `docs/TASK_BOARD.md` 的状态/证据字段

## 禁止修改范围

- `WORKFLOW_CONTRACT.md` 的字段、枚举、不变量或 diagnostic severity
- Reader、`workflow_lint` core、TASK_BOARD Adapter
- `TASK_BOARD_TEMPLATE.md`
- Overlay、Harness Profile、GPT‑5.6 Adapter、外部同步
- 自动 Writer、`--fix`、批量迁移、状态自动推进
- VERSION、CHANGELOG、发布和本机 Skill 副本

## Readiness Gate

- [x] `CONTRACT-004` 已 `Accepted`，Accepted commit `7f0f7e5`；真实 A/B 样本可被 lint。
- [x] `git merge-base --is-ancestor 7f0f7e5 7f0f7e5` 成功。
- [x] 三个 comparison 均为 required inputs 19→18，duplicate state 2→0。
- [x] 用户以“继续”明确批准启动剩余串行任务和本 D 级核心工作流改动。
- [x] 独立 Worktree `D:\open-source\ai-dev-flow-contract-005`；Base/HEAD `7f0f7e5`；回滚方式为回退本任务独立 commit。

## 执行步骤

1. 先建立 writer-callsite inventory 和旧状态写回测试，记录 RED。
2. 新增 Compact 模板，严格使用 8 个核心字段和条件字段。
3. 在 Full/Legacy 模板顶部说明适用范围，不删除旧段落。
4. 为 create/execute/review/diff-review/repair/acceptance/close 同步最小路由。
5. 证明 Compact 入口不会重建旧 Review/merge 状态，legacy 入口仍可继续写旧格式。
6. 对三个真实 A/B 样本运行 `workflow_lint` 和填写量对比。
7. 做 legacy/Compact 回归、独立 Review 和 UA6，不执行批量迁移。

## 完成标准

- [x] Compact 模板只面向 A/B + `overlays=none`。
- [x] C/D、Batch、Wave、real_env 和未知条件全部保持 Full/Legacy。
- [x] existing legacy TASK 原样可继续维护，不要求加入 v0.7 block。
- [x] writer-callsite inventory 覆盖所有创建或更新 TASK 的入口。
- [x] create/execute/review/diff-review/repair/acceptance/close 对 Compact 不重建旧状态字段。
- [x] Compact 只有一个 Review 状态和一套 delivery 状态。
- [x] Compact 模板没有一排 N/A/Not Applicable 噪声。
- [x] 三个真实 A/B 样本通过 004 lint，填写量稳定少于 legacy。
- [x] 没有自动迁移、状态 Writer、`--fix`、外部同步或模型依赖。
- [x] Full/Legacy 模板仍完整可用。
- [ ] 独立 Review 无 P0/P1，用户完成核心流程回归验收。

## 验证方式

```powershell
rg -n "代码审查|Diff 审查|合并状态|提交 / 合并|TASK_TEMPLATE" skills/ai-dev-flow/SKILL.md skills/ai-dev-flow/references
python -B -X utf8 -m unittest discover -s skills/ai-dev-flow/tests -p "test_workflow_contract*.py" -v
$compactTasks = @(Get-ChildItem skills/ai-dev-flow/tests/fixtures/comparisons -Recurse -Filter 'compact-task.md')
if ($compactTasks.Count -ne 3) { throw "Expected 3 Compact comparison TASK files" }
foreach ($task in $compactTasks) {
  python -B -X utf8 skills/ai-dev-flow/scripts/workflow_lint.py $task.FullName --format human
  if ($LASTEXITCODE -ne 0) { throw "Compact lint failed: $($task.FullName)" }
}
git diff --check
git diff --name-only
```

回归矩阵必须包含：

- A/B + no Overlay 选择 Compact。
- C/D、Batch、Wave、real_env 选择 legacy。
- Compact 的 create/execute/review/diff-review/repair/acceptance/close 不复活旧字段。
- legacy TASK 继续使用旧段落。
- 三个真实样本填写量对比。
- 未知格式/等级停止并待确认。
- 文档相对链接和 Skill package validation。

## 停止条件

- writer callsite 无法完整枚举。
- 任一入口需要自动迁移旧 TASK 才能工作。
- Compact 会误路由 C/D、Batch、Wave 或 real_env。
- 必须改变 Contract 语义、diagnostic severity 或 Reader 才能继续。
- 修改范围扩展为全量 Prompt 重写、Overlay 或 TASK_BOARD 自动写回。
- 回归出现新旧状态双写或 legacy 不可继续。

## 代码审查

- 审查状态：需要修改
- 审查人或审查 agent：Codex 独立 Reviewer（第 1 轮）
- 审查严重等级：P1（2 项，同一根因）
- P0 / P1 必须修改项：
  1. inventory 漏掉 `skills/ai-dev-flow/README.md` 的 create 入口，以及 `VALIDATION_GUIDE.md` / `ACCEPTANCE_GUIDE.md` 的 execute/acceptance/close 写回格式；它们仍可能绕过 Compact 路由。
  2. 专项测试只检查预选文件关键词，没有用可执行路由/结构场景覆盖 create、execute、review、diff-review、repair、acceptance、close，因此无法发现真实 callsite 遗漏。
- P2：metrics 测试读取静态 JSON，未从 comparison Markdown 重新计算，存在未来漂移盲区。
- 审查结论：Needs Fix；不允许进入 UA6
- 是否允许进入验收建议：否

## 执行与验证记录

- Writer callsite inventory：
  - 创建入口：`SKILL.md` 默认执行建议；`PROMPTS.md` 的拆任务/create_task；`WORKFLOW.md` 创建 TASK；Full/Compact 两份模板。
  - 更新入口：execute、自查、review、pre/post diff-review、repair、acceptance、close；集中规则已写入 `SKILL.md`、`PROMPTS.md`、`WORKFLOW.md`。
  - 审查兼容入口：`CODE_REVIEW_CHECKLIST.md`、`AGENTS_COMPAT.md`。
  - 全量搜索关键词：`代码审查|Diff 审查|合并状态|提交 / 合并|TASK_TEMPLATE|create_task|execute_task|review_task|repair_task|close_task|acceptance`。
- RED：新增 `test_compact_writer_routing.py` 后 4 tests 中 1 error、7 个 subtest failure；缺少 Compact 模板和所有入口路由。
- GREEN：完整 `test_*.py` 30/30 通过；Compact 路由专项 4/4 通过。
- 三个 comparison：`CMP-12B3DC0-compact.md`、`CMP-4A6C417-compact.md`、`CMP-81A8837-compact.md` 均 lint exit 0；仅因历史 blob 不足输出非阻塞 `W_TRANSITION_UNVERIFIABLE`。
- 填写量：三组均 required inputs 19→18，duplicate state occurrences 2→0。
- 范围：未修改 fixture、Reader、workflow_lint、Contract 语义、TASK_BOARD projection、VERSION/CHANGELOG；未实现自动 Writer 或迁移。

## Diff 审查

- 审查方式：post-commit diff
- 审查命令：待执行时填写
- 修改文件清单：待填写
- 范围越界文件：待审查
- 审查状态：第 1 轮未通过
- 审查结论：30/30 tests 与 comparison lint 通过，但 callsite inventory 和行为验证存在 P1

## 审查-修复循环（review_repair_loop）记录

- 当前轮次：1 / 2；用户已批准将三个遗漏入口加入允许范围。
- 第 1 轮修复范围：`skills/ai-dev-flow/README.md`、`references/VALIDATION_GUIDE.md`、`references/ACCEPTANCE_GUIDE.md` 和专项测试；不改变 Contract 语义、Reader、lint、fixture 或自动 Writer 边界。
- 第 1 轮修复结果：
  1. README 的轻量安装清单和 create 示例同时暴露 Compact/Full 路由。
  2. VALIDATION/ACCEPTANCE 明确 Compact 只写 Contract/Outcome，Full/Legacy 才使用旧式验收段落。
  3. WORKFLOW 增加可机械读取的 7 场景选择矩阵和 7 动作写回矩阵。
  4. 专项测试从预选关键词升级为：解析并精确断言路由/写回矩阵、全仓 writer-callsite 集合封闭检查、metrics ledger 机械复算。
- 修复后验证：专项 5/5、全量 31/31 GREEN；fixture diff 为空，`git diff --check` 通过。
- 第 1 轮修复复审：上一轮两个 P1主体和 metrics P2 已关闭；仍有 1 项 P1——README 与 Compact 模板把 unknown 错误写成先选择 Full，违反 `STOP_PENDING_CONFIRMATION`。
- 第 2 / 2 轮修复边界：只统一 unknown 为“停止、待确认、不选择模板”，并增加跨入口一致性反例；不扩大其他范围。
- 第 2 / 2 轮修复结果：README 与 Compact 模板均区分“已确定不满足→Full”和“条件未知→停止且不选模板”；新增真实 create 入口一致性测试。

## 用户动作等级 / 验收建议

- 用户动作等级：UA6
- 用户需要做什么：回归验证 A/B Compact 与 legacy C/D 两条核心流程均未退化
- agent 已提供的证据：待执行后填写
- 是否允许关闭任务：否 / 待用户确认

## 用户验收反馈 / 实机测试反馈

- 验收反馈状态：无反馈
- 当前反馈关联的 UA 等级：UA6
- 反馈分类：待确认
- 下一步建议：等待任务执行、Review 和回归验收

## 合并状态

- 合并状态：未合并
- 合并目标：待执行时填写
- 合并说明：实际 merge 必须另获用户确认

## 提交 / 合并

- Commit 状态：实现 `f99dbb2`、首轮 Review 记录 `48d1c01`、第 1 轮修复 `d4802ff`、复审记录 `bd0ee89`；最终修复候选待提交
- Commit hash：待填写
- Merge 状态：未合并
- 回滚方式：回退本任务独立 commit；执行时细化

## Git 与交接

- 当前分支：`codex/contract-005-compact-routing`
- 建档时 HEAD：`4a6c41781a028bf6c78c1283f16f5d120ee61ae1`
- 执行 Base commit：`7f0f7e5a54d0727098457811359dc6dbee5e7cf4`
- 计划分支：`codex/contract-005-compact-routing`
- Worktree：`D:\open-source\ai-dev-flow-contract-005`
- Diff 范围：`7f0f7e5..HEAD`（待审查）
- 下一任务：`CONTRACT-006`，仅在本任务与 `CONTRACT-004` 均 `Accepted` 后转为 `Ready`
- 不要重复尝试：只改一处 Prompt 就宣称 Compact 路由完成
