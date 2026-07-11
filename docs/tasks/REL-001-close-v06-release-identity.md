# REL-001：收口 v0.6 发布身份

## 任务元数据

| 字段 | 当前值 |
|---|---|
| 任务编号 | `REL-001` |
| 任务类型 | 文档 / 发布治理 |
| 当前模式 | UA7 用户决策已完成，等待后续收口授权 |
| 下一允许模式 | 收口任务（`close_task`），需用户另行确认关闭或提交/合并动作 |
| 任务状态 | 已验收（`Accepted`） |
| 优先级 | 高 |
| 风险等级 | 高 |
| 任务分级 | B：改动范围小，但发布语义敏感 |
| 执行位置 | 独立分支 `codex/rel-001-close-v06-release-identity` |
| 独立审查 | 必须 |
| 用户动作等级 | UA7：最终版本身份、tag 与发布策略必须由用户决定 |
| Intake | 无；来源为已批准的 v0.7 RFC |
| Batch / Wave | 禁止；Single Task |

## 当前事实

- 仓库 `skills/ai-dev-flow/VERSION` 当前为 `0.6.0`。
- README、Skill README、CHANGELOG 和 `CONTEXT.md` 已统一为 `0.6.0 / Release ready（尚未发布）`。
- v0.7 RFC 要求先收口 v0.6 身份，再开始 Workflow Contract 实现。
- 用户已授权执行 `REL-001` 及针对独立 Review P1 的有限修复；仍未授权 tag、merge、push、GitHub Release 或本机 Skill 同步。

## 目标

- 审计 `VERSION`、根 README、英文 README、Skill README 和 CHANGELOG 中的版本声明。
- 给出并落实一个一致的仓库内部版本身份，使“已发布 / Unreleased / 设计级能力”措辞不再互相冲突。
- 明确 tag 策略和实际发布动作的授权门禁。
- 形成可被 `CONTRACT-001` 引用的干净 Git baseline。

## 非目标

- 不实现任何 v0.7 Contract、Reader、lint、模板或投影功能。
- 不创建 Git tag、GitHub Release，不 merge、push 或发布。
- 不同步 Codex、Claude、cc-switch、Gemini 等本机 Skill 副本。
- 不重写历史 CHANGELOG，不修改与版本身份无关的工作流规则。

## 必读文件

- `CONTEXT.md`
- `README.md`
- `README.en.md`
- `skills/ai-dev-flow/VERSION`
- `skills/ai-dev-flow/CHANGELOG.md`
- `skills/ai-dev-flow/README.md`
- `docs/plans/V0.7_WORKFLOW_CONTRACT_RFC.md`
- `docs/TASK_BOARD.md`
- 本任务文件

## 允许修改范围

- `skills/ai-dev-flow/VERSION`
- `skills/ai-dev-flow/CHANGELOG.md`
- `README.md`
- `README.en.md`
- `skills/ai-dev-flow/README.md`
- `CONTEXT.md`（经独立 Review P1 明确纳入有限修复）
- 本任务文件和 `docs/TASK_BOARD.md` 的状态/证据字段

## 禁止修改范围

- `skills/ai-dev-flow/SKILL.md`
- `skills/ai-dev-flow/references/`
- `skills/ai-dev-flow/scripts/`
- v0.7 schema、fixture、Reader、lint、模板或 Prompt
- Git tag、远端、GitHub Release、本机安装副本
- 任何密钥、Token、本机私有配置或绝对路径

## 前置门禁

- [x] 用户明确发出 `执行 REL-001` 或等价指令。
- [x] 本轮 RFC、CONTEXT、TASK_BOARD 与 TASK 文件已形成清晰 Git baseline。
- [x] `git status --short` 没有来源不明或不属于本任务的改动。
- [x] 执行分支、Base commit、HEAD 和 Diff 范围已写入本任务。

## 执行步骤

1. 逐文件列出所有版本号、Unreleased、发布能力和设计级能力声明。
2. 对照实际仓库内容，区分“已实现的文档能力”“未实现的脚本能力”和“未来 v0.7 提案”。
3. 形成唯一推荐结论；如结论涉及实际发布或改变发布流程，先停线取得 UA7 确认。
4. 只修改允许范围内的版本身份和说明文字。
5. 运行一致性、Skill 和 diff 验证。
6. 更新本任务与 TASK_BOARD，进入 `Review`，不执行 tag/push/release。

## 完成标准

- [x] `VERSION`、README、Skill README 和 CHANGELOG 对当前发布身份表述一致。
- [x] `0.6.0` 是否已发布、仅 release-ready 或仍为 Unreleased 只有一个明确结论。
- [x] v0.7 内容明确标记为 Draft / 未实现，没有混入 v0.6 已发布能力。
- [x] tag 命名、创建条件和授权要求已记录，但没有实际创建 tag。
- [x] 未改动 Skill 行为、Prompt、模板或脚本。
- [x] 独立 Review 无 P0/P1。
- [x] 用户完成 UA7 决策后，任务才可进入 `Accepted`。

## 验证方式

```powershell
git status --short
git diff --name-only
git diff --check
rg -n "0\.5\.2|0\.6\.0|0\.7|Unreleased|VERSION|发布" README.md README.en.md skills/ai-dev-flow
Get-Content skills/ai-dev-flow/VERSION
python -X utf8 "$env:USERPROFILE\.codex\skills\.system\skill-creator\scripts\quick_validate.py" skills/ai-dev-flow
```

附加检查：

- 修改文件必须全部属于允许范围。
- `git tag --list` 只读检查可以执行，但不得创建或删除 tag。
- 如果本机没有 `quick_validate.py`，记录原因并执行等价的 SKILL frontmatter、文件存在性和 Markdown 链接检查。

## 停止条件

- 实际能力与 `0.6.0` 声明无法对应。
- 需要删除或重写历史发布记录。
- 需要修改发布流程、创建 tag、push 或 GitHub Release。
- 发现 v0.6 和 v0.7 改动无法在 diff 中清晰分离。
- 工作区出现本任务范围外改动。

## 代码审查

- 审查状态：复审通过
- 审查人或审查 agent：Codex Reviewer（独立审查）
- 审查严重等级：无（原两项 P1 均已修复）
- P0 / P1 必须修改项：
  1. `CONTEXT.md:49` 仍将 `VERSION=0.5.2`、`0.6.0 Unreleased` 和“发布身份尚未收口”列为当前事实，与本任务落实的 `0.6.0 / Release ready（尚未发布）` 直接冲突。该文件是项目当前事实真相源且属于任务必读文件，必须在允许范围明确扩展后同步，或由任务记录给出不修改它仍能形成单一身份的有效依据。
  2. “提交 / 合并”记录的 commit hash `b8c2a0195df16d512a3241b9382bcd9db9874277` 不是仓库对象；实际执行提交为 `b8c2a01d4dc89b767a5ee3e8a0195e742876d7dc`。同时前置门禁声称已写入 HEAD，但任务没有记录具体审查前 HEAD。必须修正可追溯 Git 证据，并明确 release/tag 候选提交如何包含执行证据与后续审查记录。
- 复审结果：两项原 P1 均已关闭；未发现新增 P0/P1/P2/P3。
- 审查结论：通过；允许进入 UA7 用户决策，但不代表已验收、已合并或已发布
- 是否允许进入验收建议：是（UA7）

## P1 有限修复记录

- 修复模式：修复任务（`repair_task`）。
- 修复起点 HEAD：`d7abee028782653543b15e2207f62775e6515ef5`；开始修复时工作区仅包含独立 Reviewer 写回的本任务文件与 TASK_BOARD 状态记录。
- Finding 1：已把 `CONTEXT.md` 明确加入允许修改范围，并将当前事实更新为 `0.6.0 / Release ready（尚未发布）`，同时保留 tag、push、GitHub Release、merge 和本机 Skill 同步的独立授权门禁。
- Finding 2：已把不可解析 hash 修正为实际执行提交 `b8c2a01d4dc89b767a5ee3e8a0195e742876d7dc`；补记审查前 HEAD `d7abee028782653543b15e2207f62775e6515ef5`。
- 最终 release/tag 候选规则：不得固定为执行提交或修复提交。候选必须是包含执行提交、执行证据、P1 修复及独立复审结论的最终获准提交，并满足 `git merge-base --is-ancestor b8c2a01d4dc89b767a5ee3e8a0195e742876d7dc <候选提交>` 成功；实际候选 hash 只能在复审记录提交后填写，并仍需 UA7 授权。
- 修复范围：仅 `CONTEXT.md`、本任务文件和 `docs/TASK_BOARD.md`；未修改版本内容、Skill 行为、Prompt、模板、脚本或 v0.7 实现。

## 执行与验证记录

- 版本身份结论：仓库内部版本为 `0.6.0`，状态为 Release ready（尚未发布）。
- tag 策略：计划使用 `v0.6.0`；独立 Review 无 P0/P1、版本一致性验证通过且用户明确完成 UA7 授权后才允许创建。
- 实际发布动作：未创建 tag，未 push，未创建 GitHub Release，未 merge，未同步本机 Skill。
- 修改文件：`README.md`、`README.en.md`、`skills/ai-dev-flow/README.md`、`skills/ai-dev-flow/CHANGELOG.md`、`skills/ai-dev-flow/VERSION`、本任务文件、`docs/TASK_BOARD.md`。
- `git diff --check`：通过，无输出。
- 版本检索：通过；对外文档当前版本均为 `0.6.0`，没有剩余 `Unreleased` 身份声明。
- Skill 验证：`quick_validate.py skills/ai-dev-flow` 通过，输出 `Skill is valid!`。
- 范围检查：未修改 `SKILL.md`、`references/`、`scripts/` 或任何 v0.7 实现文件。
- tag 只读检查：仓库当前无 tag。
- 未验证项：独立 Review 与 UA7 用户决策尚未完成。

## Diff 审查

- 审查方式：post-commit diff
- 审查命令：`git diff --check 5c505d202880a538c57c7c9d0ff35df30cf3af8f..HEAD`；`git diff --name-status 5c505d202880a538c57c7c9d0ff35df30cf3af8f..HEAD`；`git diff 5c505d202880a538c57c7c9d0ff35df30cf3af8f..HEAD`
- 修改文件清单：`README.md`、`README.en.md`、`skills/ai-dev-flow/README.md`、`skills/ai-dev-flow/CHANGELOG.md`、`skills/ai-dev-flow/VERSION`、`CONTEXT.md`、本任务文件、`docs/TASK_BOARD.md`
- 范围越界文件：执行自查未发现；以独立 Review 结论为准
- 审查状态：复审通过
- 审查结论：通过；`d7abee028782653543b15e2207f62775e6515ef5..169db4f09da79a4ac3b4518802b7b1fa6c0603be` 的有限修复仅涉及获准的三份文档，完整任务 diff 无禁止路径改动

## 用户动作等级 / 验收建议

- 用户动作等级：UA7
- 用户需要做什么：已确认最终版本身份与 tag 策略；实际创建 tag 或发布仍需另行明确授权
- agent 已提供的证据：版本检索、`git diff --check`、Skill quick validation、允许范围检查和空 tag 列表
- 是否允许关闭任务：否；已达到 `Accepted`，但 `Closed`、commit、merge、tag、push 和发布均需分别授权

## 用户验收反馈 / 实机测试反馈

- 验收反馈状态：UA7 已确认通过
- 当前反馈关联的 UA 等级：UA7
- 反馈分类：接受版本身份与 tag 策略
- 下一步建议：形成包含复审与验收记录的可引用 Git baseline；实际 commit、merge、tag、push 或发布按用户后续授权执行

## 合并状态

- 合并状态：未合并
- 合并目标：待执行时填写
- 合并说明：实际 merge 必须另获用户确认

## 提交 / 合并

- Commit 状态：已提交执行结果
- 执行内容 commit：`b8c2a01d4dc89b767a5ee3e8a0195e742876d7dc`
- 执行证据 commit / 审查前 HEAD：`d7abee028782653543b15e2207f62775e6515ef5`
- P1 修复 commit：`dc363745eb2e378eb54696d50286c8278d7e8e1e`
- 最终 release/tag 候选 commit：待独立复审结论提交后填写；必须满足本任务“P1 有限修复记录”中的 ancestor 与授权条件
- Merge 状态：未合并
- 回滚方式：回退本任务独立 commit；执行时细化

## Git 与交接

- 当前分支：`codex/rel-001-close-v06-release-identity`
- 建档时 HEAD：`4a6c41781a028bf6c78c1283f16f5d120ee61ae1`
- 执行 Base commit：`5c505d202880a538c57c7c9d0ff35df30cf3af8f`
- 计划分支：`codex/rel-001-close-v06-release-identity`（已建立）
- Diff 范围：`5c505d202880a538c57c7c9d0ff35df30cf3af8f...HEAD`（提交前使用同一 Base 到工作区）
- 下一任务：`CONTRACT-001`，仅在本任务 `Accepted` 且形成可引用 baseline 后转为 `Ready`
- 不要重复尝试：未经新授权直接 tag、push、release 或同步本机 Skill
