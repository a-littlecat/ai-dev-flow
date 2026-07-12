# CONTRACT-001：固化 Workflow Contract 语义规范

## 任务元数据

| 字段 | 当前值 |
|---|---|
| 任务编号 | `CONTRACT-001` |
| 任务类型 | 方案 / 协议文档 / Schema |
| 当前模式 | 用户已完成 UA2 阅读确认，任务已验收 |
| 下一允许模式 | 保持已验收（`Accepted`）；实际 merge 仍需另获用户授权 |
| 任务状态 | 已验收（`Accepted`） |
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

- [x] `REL-001` 已 `Accepted`，版本身份形成可引用 Git baseline：`752b11f1a8bd6fd2b8e0b7e13309457f9a072f33`。
- [x] `git merge-base --is-ancestor 752b11f1a8bd6fd2b8e0b7e13309457f9a072f33 752b11f1a8bd6fd2b8e0b7e13309457f9a072f33` 成功，证明准备基线包含前置结果。
- [x] RFC 三项默认决策仍有效；若需改变，先回到 `plan_task` 并取得用户确认。
- [x] 当前工作区干净，执行位置、Base commit、HEAD 和 Diff 范围已记录。
- [x] v0.6 发布改动已形成独立 Accepted commit，后续规范产物可以从该 baseline 形成独立 diff。

## 执行步骤

1. 从 RFC 提取完整 known-field set、枚举、条件必填和受限 Markdown grammar。
2. 明确 schema version 与 Skill package version 的独立演进规则。
3. 把当前状态机、Review、UA7、merge 和 feedback gate 不变量引用到唯一规范。
4. 定义只读 `inspect()`、Normalized View、WorkflowReport、provenance 和 phased diagnostics。
5. 编写 JSON Schema，只表达内存对象，不新增 JSON sidecar 写入流程。
6. 用 RFC 示例和反例做静态一致性验证。
7. 独立 Review 后更新任务状态，不开始 `CONTRACT-002`。

## 完成标准

- [x] `WORKFLOW_CONTRACT.md` 是字段、枚举、不变量、诊断码和兼容规则的唯一规范入口。
- [x] 8 个核心字段与所有条件字段均有精确语法、大小写、重复键、未知键和多值规则。
- [x] `adf/v0.7.0` 与 Skill `VERSION` 的关系清楚，`0.7.x` 兼容规则可验证。
- [x] JSON Schema 可被标准 JSON parser 读取，且不包含模型名或外部运行时依赖。
- [x] `mode` 明确属于调用上下文，不进入持久 Contract。
- [x] UA7 的 Passed/Failed/Deferred 只允许 `User Confirmed`。
- [x] `merge_status=Merged` 只允许本次用户授权。
- [x] 诊断码标出首批与 `CONTRACT-007` 后才启用的阶段边界。
- [x] 规范包含 legacy 标题、字段和值的显式别名矩阵；禁止模糊匹配，并定义一致重复值与冲突值的 provenance/diagnostic 规则。
- [x] 未改变现有 lifecycle 合法流转。
- [x] 独立 Review 无 P0/P1；用户按 UA2 确认规范与 RFC 一致。

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

## 执行与验证记录

- 执行结果：规范与 Schema 候选实现及三路预审修复均完成，正式进入独立 post-commit Review；未开始 Reader、CLI、模板或 Prompt。
- 新增 `skills/ai-dev-flow/references/WORKFLOW_CONTRACT.md`：冻结 canonical grammar、字段/枚举、18 条 lifecycle 流转、14 条跨轴不变量、Legacy 精确别名、provenance、Git 只读历史、diagnostic phase 和九字段 board projection 契约。
- 新增 `skills/ai-dev-flow/schemas/workflow-contract.schema.json`：Draft 2020-12 JSON Schema，仅描述默认注入前的 `CanonicalContractInput`；8 个核心字段必填，表达 UA evidence、UA7 authority、Accepted/Closed、close 与 merge authority 的可表达条件。
- `python -X utf8 -m json.tool ...`：通过。
- 标准库 Schema 对照脚本：通过；`required=8`，6 组核心枚举与关键 conditional token 均匹配规范。
- `jsonschema.Draft202012Validator.check_schema` 与样例矩阵：通过；10 个 valid 样例通过，13 个 invalid 样例被拒绝。
- lifecycle 对照：通过；与 `STATUS_MACHINE.md` 一致，共 18 条合法流转。
- `quick_validate.py skills/ai-dev-flow`：通过，输出 `Skill is valid!`。
- runtime/model 中立检查：通过；Schema 不含 GPT、Codex、Claude、Gemini 或 OpenAI 专属字段。
- `git merge-base --is-ancestor 752b11f... b198abc...`：通过，执行 Base 包含前置 Accepted baseline。
- `git diff --check`：通过，无 whitespace error；PowerShell 仅提示现有文档的 LF/CRLF 转换策略。
- 范围检查：当前 diff 仅包含规范、Schema、本任务文件与 TASK_BOARD；未修改禁止范围。
- 三路预审：Schema/规范一致性、Legacy 实样兼容和任务完成标准复核最终均无 findings；预审不替代正式 post-commit Review。
- 独立 post-commit Review：基于 `b198abce89e18dc417b935fa219be8ed6a56711a..021175a374381c48294e23ea2d24f6a987a78176` 完成，结论为需要修改；3 个 P1、1 个 P2。
- 未验证项：Review findings 修复后的复审、UA2 用户阅读确认。

## 审查-修复循环（review_repair_loop）记录

- 当前任务：`CONTRACT-001`
- 当前轮次：1
- 最大轮次：2
- 本轮角色：修复者（Repairer）已完成；独立 Reviewer 已复审
- Repair 输入：Reader opt-in 与 RFC 对齐；board Pending 别名；Git commit 事实写回；extension optional/required 互斥。
- 允许修改：`WORKFLOW_CONTRACT.md`、必要的 Schema、当前 TASK 与 TASK_BOARD。
- 禁止扩大：Reader、CLI、fixture、模板、SKILL、PROMPTS 与 `CONTRACT-002+`。
- 验证方式：复跑 JSON/Schema 矩阵、18 流转、Skill validation、范围检查和独立复审。
- 本轮处理：
  1. P1 Reader opt-in：改为仅精确 `schema_version` declaration 启用严格 v0.7；无 declaration 保持 Legacy。
  2. P1 board Review：新增 `待独立审查 -> Pending`，并允许 canonical review token 直读。
  3. P1 Git 事实：写回实现 commit `021175a...` 与 Review 记录 commit `a628fc7...`。
  4. P2 extension：optional/required 集合必须互斥，重叠唯一输出 `E_PARSE`。
- 修改文件：`WORKFLOW_CONTRACT.md`、本任务文件、`docs/TASK_BOARD.md`；未修改 Schema、Reader、CLI、fixture、模板、SKILL 或 PROMPTS。
- 验证结果：repair assertions 5/5、JSON/Schema 解析、18 条流转、Skill validation、`git diff --check` 均通过。
- 未处理意见：无。
- 独立复审 HEAD：`14fd7f3dd57662ab7bfe844f5fc90dc1fa8efb72`。
- 复审结论：无 P0/P1/P2/P3，原 4 项 finding 全部关闭，允许进入 UA2。
- 是否需要再审查：否；除非 UA2 反馈要求改变规范或出现新 diff。
- 是否触发人工接管：否。

## 停止条件

- 规范需要改变 RFC 已批准的 canonical 格式、首批范围或发布顺序。
- JSON Schema 无法表达语义，且需要新增重量级 runtime 才能继续。
- 发现现有状态机、UA 或 Git 规则存在必须由用户决策的冲突。
- 规范开始包含 GPT‑5.6、Codex、Claude 或 Gemini 专属核心字段。
- 修改范围扩展到 Reader、CLI、模板或 Prompt。

## 代码审查

- 审查状态：复审通过
- 审查人或审查 agent：Codex 独立 Reviewer（第 1 轮复审）
- 审查严重等级：无（原 3 个 P1、1 个 P2 均已关闭）
- 原 P0 / P1 必须修改项：
  1. Reader 选择应以显式 `schema_version` opt-in，不能仅凭同名标题升级为严格 v0.7。
  2. Legacy board Review 必须确定性接受当前 `待独立审查` / canonical Pending 表达。
  3. 写回实现 commit `021175a374381c48294e23ea2d24f6a987a78176`，消除 TASK、看板与 Git 事实冲突。
- 原 P2 建议修改项：`extensions_optional` 与 `extensions_required` 必须互斥，并有唯一 diagnostic。
- 复审结果：上述 4 项全部关闭；未发现新增 P0/P1/P2/P3。
- 审查结论：通过；允许进入 UA2，但不代表已验收、已合并或已发布
- 是否允许进入验收建议：是（UA2）

## Diff 审查

- 审查方式：post-commit diff
- 审查命令：原审查 `b198abce89e18dc417b935fa219be8ed6a56711a..021175a374381c48294e23ea2d24f6a987a78176`；修复复审 `a628fc7b1114c82279a7c4f4d047d425bc7025b5..14fd7f3dd57662ab7bfe844f5fc90dc1fa8efb72`；完整复核 `b198abce89e18dc417b935fa219be8ed6a56711a..14fd7f3dd57662ab7bfe844f5fc90dc1fa8efb72`
- 修改文件清单：`docs/TASK_BOARD.md`、本任务文件、`skills/ai-dev-flow/references/WORKFLOW_CONTRACT.md`、`skills/ai-dev-flow/schemas/workflow-contract.schema.json`
- 范围越界文件：无
- 审查状态：已通过
- 审查结论：完整任务仅包含 4 个允许文件；修复范围仅包含规范、TASK、TASK_BOARD；无越界且无 P0-P3

## 用户动作等级 / 验收建议

- 用户动作等级：UA2
- 用户需要做什么：阅读规范摘要、字段表、Legacy/diagnostic 边界，确认与已批准 RFC 一致
- agent 已提供的证据：JSON/Schema 检查、18 条状态流转对照、Skill validation、范围检查和后续独立 Review 记录
- 是否允许关闭任务：否；本次授权为 Accepted 与继续后继任务，不包含 Closed 或 merge

## 用户验收反馈 / 实机测试反馈

- 验收反馈状态：通过；用户于 2026-07-12 明确认可当前升级方案并要求继续
- 当前反馈关联的 UA 等级：UA2
- 反馈分类：不适用
- 下一步建议：任务保持 Accepted；允许在其 Accepted commit 成为当前 Base 祖先后准备 `CONTRACT-002`

## 合并状态

- 合并状态：未合并
- 合并目标：待执行时填写
- 合并说明：实际 merge 必须另获用户确认

## 提交 / 合并

- Commit 状态：实现结果、Review 记录和第 1 轮修复均已提交；复审记录待提交
- 实现 commit：`021175a374381c48294e23ea2d24f6a987a78176`
- Review 记录 commit：`a628fc7b1114c82279a7c4f4d047d425bc7025b5`
- 第 1 轮修复 commit：`8427eefe10f40fbeb1d74ad251ce24d63d7fc0b0`
- 修复证据 commit / 复审 HEAD：`14fd7f3dd57662ab7bfe844f5fc90dc1fa8efb72`
- 复审记录 commit：`ba85738d9bf7b47110ac84ed21c16601ebf10ef2`
- Merge 状态：未合并
- 回滚方式：回退本任务独立 commit；执行时细化

## Git 与交接

- 当前分支：`codex/contract-001-semantics`
- 建档时 HEAD：`4a6c41781a028bf6c78c1283f16f5d120ee61ae1`
- 准备 Base / 前置 Accepted commit：`752b11f1a8bd6fd2b8e0b7e13309457f9a072f33`
- 执行 Base commit：`b198abce89e18dc417b935fa219be8ed6a56711a`；已验证包含前置 Accepted commit
- 执行开始 HEAD：`b198abce89e18dc417b935fa219be8ed6a56711a`
- 开始时工作区：干净，无来源不明改动；未发现不应提交文件
- 计划分支：`codex/contract-001-semantics`
- Diff 范围：原实现审查为 `b198abce89e18dc417b935fa219be8ed6a56711a..021175a374381c48294e23ea2d24f6a987a78176`；第 1 轮复审使用 `a628fc7b1114c82279a7c4f4d047d425bc7025b5..8427eefe10f40fbeb1d74ad251ce24d63d7fc0b0`，完整任务复核使用执行 Base 到最新证据提交
- 下一任务：`CONTRACT-002`，仅在本任务 `Accepted` 后转为 `Ready`
- 不要重复尝试：在规范未冻结前先写 Reader 或 Compact Template
