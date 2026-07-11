# REL-001：收口 v0.6 发布身份

## 任务元数据

| 字段 | 当前值 |
|---|---|
| 任务编号 | `REL-001` |
| 任务类型 | 文档 / 发布治理 |
| 当前模式 | 创建任务（`create_task`） |
| 下一允许模式 | 执行任务（`execute_task`），需用户明确指定 |
| 任务状态 | 可执行（`Ready`） |
| 优先级 | 高 |
| 风险等级 | 高 |
| 任务分级 | B：改动范围小，但发布语义敏感 |
| 执行位置 | 计划使用独立分支；执行时确认 |
| 独立审查 | 必须 |
| 用户动作等级 | UA7：最终版本身份、tag 与发布策略必须由用户决定 |
| Intake | 无；来源为已批准的 v0.7 RFC |
| Batch / Wave | 禁止；Single Task |

## 当前事实

- 仓库 `skills/ai-dev-flow/VERSION` 当前为 `0.5.2`。
- README 和 `skills/ai-dev-flow/CHANGELOG.md` 已包含 `0.6.0 Unreleased` 能力说明。
- v0.7 RFC 要求先收口 v0.6 身份，再开始 Workflow Contract 实现。
- 用户本轮只授权建档，没有授权改版本、tag、merge、push 或发布。

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
- 本任务文件和 `docs/TASK_BOARD.md` 的状态/证据字段

## 禁止修改范围

- `skills/ai-dev-flow/SKILL.md`
- `skills/ai-dev-flow/references/`
- `skills/ai-dev-flow/scripts/`
- v0.7 schema、fixture、Reader、lint、模板或 Prompt
- Git tag、远端、GitHub Release、本机安装副本
- 任何密钥、Token、本机私有配置或绝对路径

## 前置门禁

- [ ] 用户明确发出 `执行 REL-001` 或等价指令。
- [ ] 本轮 RFC、CONTEXT、TASK_BOARD 与 TASK 文件已形成清晰 Git baseline。
- [ ] `git status --short` 没有来源不明或不属于本任务的改动。
- [ ] 执行分支、Base commit、HEAD 和 Diff 范围已写入本任务。

## 执行步骤

1. 逐文件列出所有版本号、Unreleased、发布能力和设计级能力声明。
2. 对照实际仓库内容，区分“已实现的文档能力”“未实现的脚本能力”和“未来 v0.7 提案”。
3. 形成唯一推荐结论；如结论涉及实际发布或改变发布流程，先停线取得 UA7 确认。
4. 只修改允许范围内的版本身份和说明文字。
5. 运行一致性、Skill 和 diff 验证。
6. 更新本任务与 TASK_BOARD，进入 `Review`，不执行 tag/push/release。

## 完成标准

- [ ] `VERSION`、README、Skill README 和 CHANGELOG 对当前发布身份表述一致。
- [ ] `0.6.0` 是否已发布、仅 release-ready 或仍为 Unreleased 只有一个明确结论。
- [ ] v0.7 内容明确标记为 Draft / 未实现，没有混入 v0.6 已发布能力。
- [ ] tag 命名、创建条件和授权要求已记录，但没有实际创建 tag。
- [ ] 未改动 Skill 行为、Prompt、模板或脚本。
- [ ] 独立 Review 无 P0/P1。
- [ ] 用户完成 UA7 决策后，任务才可进入 `Accepted`。

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

- 审查状态：未审查（按发布治理/文档审查执行）
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

- 用户动作等级：UA7
- 用户需要做什么：确认最终版本身份与 tag 策略；实际发布需另行明确授权
- agent 已提供的证据：待执行后填写
- 是否允许关闭任务：否 / 待用户确认

## 用户验收反馈 / 实机测试反馈

- 验收反馈状态：无反馈
- 当前反馈关联的 UA 等级：UA7
- 反馈分类：不适用
- 下一步建议：等待任务执行、Review 和用户决策

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
- 执行 Base commit：待执行时填写，必须包含本任务文件
- 计划分支：`codex/rel-001-v06-release-identity`
- Diff 范围：待执行时填写
- 下一任务：`CONTRACT-001`，仅在本任务 `Accepted` 且形成可引用 baseline 后转为 `Ready`
- 不要重复尝试：未经新授权直接 tag、push、release 或同步本机 Skill
