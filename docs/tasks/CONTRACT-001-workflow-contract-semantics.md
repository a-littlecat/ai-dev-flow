# CONTRACT-001：固化 Workflow Contract 语义规范

## 任务元数据

| 字段 | 当前值 |
|---|---|
| 任务编号 | `CONTRACT-001` |
| 任务类型 | 方案 / 协议文档 / Schema |
| 当前模式 | 创建任务（`create_task`） |
| 下一允许模式 | 前置门禁满足后进入 `execute_task` |
| 任务状态 | 草稿（`Draft`） |
| 优先级 | 高 |
| 风险等级 | 高 |
| 任务分级 | C：新增稳定语义接口并影响后续全部实现 |
| 执行位置 | v0.7 独立分支或 Worktree；顺序执行 |
| 独立审查 | 必须 |
| 用户动作等级 | UA2：用户阅读并确认规范与 RFC 一致；若改变已批准架构则升级 UA7 |
| 前置任务 | `REL-001` 达到 `Accepted` |
| Batch / Wave | 禁止；Single Task |

## 背景

v0.7 RFC 已确定一个 Markdown-first、agent-agnostic、只读优先的 Workflow Contract Module。后续 fixture、Reader、CLI、模板和投影都需要引用同一份字段、枚举、不变量、诊断码和版本规则，不能继续从多个长文档各自解释。

## 目标

- 创建唯一的 Workflow Contract 语义规范。
- 固化 v0.7.0 的 8 个核心字段、条件字段、语法、枚举和版本兼容规则。
- 固化 lifecycle、Review、UA、delivery、authority 和 Acceptance Feedback Gate 的跨轴不变量。
- 定义 `WorkflowContract.inspect(target) -> WorkflowReport` 的概念接口和 provenance 要求。
- 提供用于内存结构化对象和 fixture 的 JSON Schema；它不得成为第二落盘真相源。

## 非目标

- 不实现 Markdown Reader、legacy Reader 代码、lint CLI 或 TASK_BOARD Adapter；但必须在规范中定义显式 legacy 别名矩阵和冲突规则。
- 不修改 TASK_TEMPLATE、TASK_BOARD_TEMPLATE、SKILL writer 路由或 PROMPTS。
- 不实现 Overlay Registry、Harness Profile、GPT‑5.6 Adapter 或外部同步。
- 不改变现有 `STATUS_MACHINE.md` 的合法 lifecycle 流转。
- 不新增第三方依赖。

## 必读文件

- `CONTEXT.md`
- `docs/plans/V0.7_WORKFLOW_CONTRACT_RFC.md`
- `docs/TASK_BOARD.md`
- `docs/tasks/REL-001-close-v06-release-identity.md`
- `skills/ai-dev-flow/references/STATUS_MACHINE.md`
- `skills/ai-dev-flow/references/ACCEPTANCE_GUIDE.md`
- `skills/ai-dev-flow/references/GIT_WORKFLOW.md`
- `skills/ai-dev-flow/references/TASK_TEMPLATE.md`
- `skills/ai-dev-flow/references/TASK_BOARD_TEMPLATE.md`

## 允许修改范围

- 新增 `skills/ai-dev-flow/references/WORKFLOW_CONTRACT.md`
- 新增 `skills/ai-dev-flow/schemas/workflow-contract.schema.json`
- 必要时澄清 `docs/plans/V0.7_WORKFLOW_CONTRACT_RFC.md`，但不得改变已批准方向
- 本任务文件和 `docs/TASK_BOARD.md` 的状态/证据字段

## 禁止修改范围

- `skills/ai-dev-flow/SKILL.md`
- `skills/ai-dev-flow/references/PROMPTS.md`
- `skills/ai-dev-flow/references/TASK_TEMPLATE.md`
- `skills/ai-dev-flow/references/TASK_BOARD_TEMPLATE.md`
- `skills/ai-dev-flow/scripts/` 和生产 Reader/CLI
- 现有 lifecycle 含义、UA7 用户决策和 merge 用户授权规则
- 模型专属字段、数据库、守护进程、网络 API 或大型依赖

## Readiness Gate

- [ ] `REL-001` 已 `Accepted`，版本身份形成可引用 Git baseline。
- [ ] `git merge-base --is-ancestor <REL-001 Accepted commit> <当前 Base>` 成功，证明当前执行基线包含前置结果。
- [ ] RFC 三项默认决策仍有效；若需改变，先回到 `plan_task` 并取得用户确认。
- [ ] 当前工作区干净，执行位置、Base commit、HEAD 和 Diff 范围已记录。
- [ ] 规范产物与 v0.6 发布改动可形成独立 diff。

## 执行步骤

1. 从 RFC 提取完整 known-field set、枚举、条件必填和受限 Markdown grammar。
2. 明确 schema version 与 Skill package version 的独立演进规则。
3. 把当前状态机、Review、UA7、merge 和 feedback gate 不变量引用到唯一规范。
4. 定义只读 `inspect()`、Normalized View、WorkflowReport、provenance 和 phased diagnostics。
5. 编写 JSON Schema，只表达内存对象，不新增 JSON sidecar 写入流程。
6. 用 RFC 示例和反例做静态一致性验证。
7. 独立 Review 后更新任务状态，不开始 `CONTRACT-002`。

## 完成标准

- [ ] `WORKFLOW_CONTRACT.md` 是字段、枚举、不变量、诊断码和兼容规则的唯一规范入口。
- [ ] 8 个核心字段与所有条件字段均有精确语法、大小写、重复键、未知键和多值规则。
- [ ] `adf/v0.7.0` 与 Skill `VERSION` 的关系清楚，`0.7.x` 兼容规则可验证。
- [ ] JSON Schema 可被标准 JSON parser 读取，且不包含模型名或外部运行时依赖。
- [ ] `mode` 明确属于调用上下文，不进入持久 Contract。
- [ ] UA7 的 Passed/Failed/Deferred 只允许 `User Confirmed`。
- [ ] `merge_status=Merged` 只允许本次用户授权。
- [ ] 诊断码标出首批与 `CONTRACT-007` 后才启用的阶段边界。
- [ ] 规范包含 legacy 标题、字段和值的显式别名矩阵；禁止模糊匹配，并定义一致重复值与冲突值的 provenance/diagnostic 规则。
- [ ] 未改变现有 lifecycle 合法流转。
- [ ] 独立 Review 无 P0/P1；用户按 UA2 确认规范与 RFC 一致。

## 验证方式

```powershell
git status --short
git diff --name-only
git diff --check
python -X utf8 -m json.tool skills/ai-dev-flow/schemas/workflow-contract.schema.json > $null
rg -n "schema_version|task_id|task_type|task_class|lifecycle|review_status|ua_level|ua_status" skills/ai-dev-flow/references/WORKFLOW_CONTRACT.md skills/ai-dev-flow/schemas/workflow-contract.schema.json
rg -n "UA7|User Confirmed|merge_authority|User Authorized|dual-read|single-write|provenance" skills/ai-dev-flow/references/WORKFLOW_CONTRACT.md
```

附加检查：

- 使用标准库脚本读取 JSON Schema 的 `required`、`enum` 和 conditional rules，与规范表逐项比对。
- 对照 `STATUS_MACHINE.md` 的 18 条合法流转，确认没有新增或漏写。
- 当本机 Skill validator 可用时运行 `quick_validate.py`；不可用时记录替代检查。

## 停止条件

- 规范需要改变 RFC 已批准的 canonical 格式、首批范围或发布顺序。
- JSON Schema 无法表达语义，且需要新增重量级 runtime 才能继续。
- 发现现有状态机、UA 或 Git 规则存在必须由用户决策的冲突。
- 规范开始包含 GPT‑5.6、Codex、Claude 或 Gemini 专属核心字段。
- 修改范围扩展到 Reader、CLI、模板或 Prompt。

## 代码审查

- 审查状态：未审查（按协议/Schema 审查执行）
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

- 用户动作等级：UA2
- 用户需要做什么：阅读规范摘要、字段表和不变量差异，确认与已批准 RFC 一致
- agent 已提供的证据：待执行后填写
- 是否允许关闭任务：否 / 待用户确认

## 用户验收反馈 / 实机测试反馈

- 验收反馈状态：无反馈
- 当前反馈关联的 UA 等级：UA2
- 反馈分类：不适用
- 下一步建议：等待任务执行、Review 和用户阅读确认

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
- 计划分支：`codex/contract-001-semantics`
- Diff 范围：待执行时填写
- 下一任务：`CONTRACT-002`，仅在本任务 `Accepted` 后转为 `Ready`
- 不要重复尝试：在规范未冻结前先写 Reader 或 Compact Template
