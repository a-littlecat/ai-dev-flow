# CONTRACT-005：启用 Compact Template 与最小 Writer 路由

## 任务元数据

| 字段 | 当前值 |
|---|---|
| 任务编号 | `CONTRACT-005` |
| 任务类型 | 工作流核心改动 / 模板 / Prompt |
| 当前模式 | 创建任务（`create_task`） |
| 下一允许模式 | 前置门禁满足且用户明确启动后进入 `execute_task` |
| 任务状态 | 草稿（`Draft`） |
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

- [ ] `CONTRACT-004` 已 `Accepted`，真实 A/B 样本可被 lint。
- [ ] `git merge-base --is-ancestor <CONTRACT-004 Accepted commit> <当前 Base>` 成功。
- [ ] 三个 comparison 已证明 Compact 输入少于 legacy，重复状态为 0。
- [ ] 用户明确批准启动 D 级核心工作流改动。
- [ ] 独立 Worktree、Base commit、HEAD、Diff 范围和回滚方式已记录。

## 执行步骤

1. 先建立 writer-callsite inventory 和旧状态写回测试，记录 RED。
2. 新增 Compact 模板，严格使用 8 个核心字段和条件字段。
3. 在 Full/Legacy 模板顶部说明适用范围，不删除旧段落。
4. 为 create/execute/review/diff-review/repair/acceptance/close 同步最小路由。
5. 证明 Compact 入口不会重建旧 Review/merge 状态，legacy 入口仍可继续写旧格式。
6. 对三个真实 A/B 样本运行 `workflow_lint` 和填写量对比。
7. 做 legacy/Compact 回归、独立 Review 和 UA6，不执行批量迁移。

## 完成标准

- [ ] Compact 模板只面向 A/B + `overlays=none`。
- [ ] C/D、Batch、Wave、real_env 和未知条件全部保持 Full/Legacy。
- [ ] existing legacy TASK 原样可继续维护，不要求加入 v0.7 block。
- [ ] writer-callsite inventory 覆盖所有创建或更新 TASK 的入口。
- [ ] create/execute/review/diff-review/repair/acceptance/close 对 Compact 不重建旧状态字段。
- [ ] Compact 只有一个 Review 状态和一套 delivery 状态。
- [ ] Compact 模板没有一排 N/A/Not Applicable 噪声。
- [ ] 三个真实 A/B 样本通过 004 lint，填写量稳定少于 legacy。
- [ ] 没有自动迁移、状态 Writer、`--fix`、外部同步或模型依赖。
- [ ] Full/Legacy 模板仍完整可用。
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

- 审查状态：未审查
- 审查人或审查 agent：待填写
- 审查严重等级：待填写
- P0 / P1 必须修改项：待审查
- 审查结论：待填写
- 是否允许进入验收建议：待确认

## Diff 审查

- 审查方式：post-commit diff
- 审查命令：待执行时填写
- 修改文件清单：待填写
- 范围越界文件：待审查
- 审查状态：未审查
- 审查结论：待填写

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

- Commit 状态：未提交
- Commit hash：待填写
- Merge 状态：未合并
- 回滚方式：回退本任务独立 commit；执行时细化

## Git 与交接

- 当前分支：`main`（建档时）
- 建档时 HEAD：`4a6c41781a028bf6c78c1283f16f5d120ee61ae1`
- 执行 Base commit：待执行时填写
- 计划分支：`codex/contract-005-compact-routing`
- Worktree：执行时在主项目外创建并记录
- Diff 范围：待执行时填写
- 下一任务：`CONTRACT-006`，仅在本任务与 `CONTRACT-004` 均 `Accepted` 后转为 `Ready`
- 不要重复尝试：只改一处 Prompt 就宣称 Compact 路由完成
