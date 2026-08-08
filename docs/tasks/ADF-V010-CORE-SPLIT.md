# ADF-V010-CORE-SPLIT：拆分治理核心与 Repair Policy

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `ADF-V010-CORE-SPLIT`
- `task_type`: `code`
- `task_class`: `D`
- `lifecycle`: `Review`
- `review_status`: `Passed`
- `ua_level`: `UA3`
- `ua_status`: `Pending`
- `commit_status`: `Committed`
- `merge_status`: `Unmerged`

## 目标与边界

- 目标：把默认治理核心、普通 Repair、严格 Repair Campaign 分离为 JSON canonical policy 与按需文档，同时保持现有 route 和历史 Repair fixture 行为兼容。
- 非目标：不修改 Dashboard、Workflow Contract schema、TASK 模板、GitHub Actions、生成 runtime 或本机已安装 Skill。
- 允许修改：`skills/ai-dev-flow/SKILL.md`、`references/CORE.md`、新增 Repair 文档、`policy/**`、`scripts/repair_gate.py` 与内部 loader、相关 tests/README、本 TASK、Master 与 TASK_BOARD。
- 禁止修改：`dashboard/**`、`TASK_TEMPLATE*`、发布资产、`skills/ai-dev-flow/dashboard/**`、本机安装目录、历史 TASK 事实。

## 依赖与授权

- 前置依赖：Stage 0 基线核查；`ADF-V010-MASTER`。
- Base commit：`7f2686f1492496adf2a71e2d981772502c7097e9`。
- 已有 authority：本阶段实现、测试、隔离只读 Review、commit、push 阶段分支、Draft PR。
- 未授权动作：merge、release、正式 Skill 同步、删除、Accepted、Closed。
- 执行位置：分支 `codex/v010-core-split`；Worktree `D:/open-source/ai-dev-flow-wt/v010-core-split`。

## 路由与风险

- 路由：`Controlled`。
- Policy 输入：D 级；`architecture`、`core_execution_path`、Skill 自修改、兼容性与阶段 delivery 风险。
- Reviewer 闸门：提交前必须隔离、只读 Review；无开放 P0/P1。
- 停止条件：需要修改禁止范围、无法保持历史 fixture、出现 policy 多事实源、解析失败不能 fail closed。

## 完成标准与验证

- 完成标准：核心、普通 Repair 与严格 Campaign 分离且保持既有 route/repair fixture 行为兼容。
- 验证命令或检查：Skill 单元测试、workflow lint、`git diff --check`、禁止范围 diff 检查和独立只读 Review。
- [x] 新增 `policy/core.json`、`repair-basic.json`、`repair-campaign.json`，核心无 Harness/模型名称。
- [x] 默认加载路径不接触严格 Campaign；DoNotUseSkill 不读取 Repair。
- [x] loader 严格 UTF-8、拒绝未知字段、深层校验 schema/type/enum/constraint，并兼容旧 `CORE.md POLICY_JSON` 且给 deprecated 警告。
- [x] `repair_gate.py` 支持 JSON policy，且不重复硬编码完整 policy。
- [x] 现有 route 与 Repair fixture、新 JSON与旧 Markdown 兼容测试全部通过。
- [x] Skill 全量测试、workflow lint 和 `git diff --check` 通过；Dashboard 无 diff。
- [x] 独立只读 Review 无开放 P0/P1。

## Repair Chain Ledger（仅进入 repair 时填写）

- `ADF-V010-CORE-SPLIT-R001`（P1）：Round 1 指出 loader 只校验顶层；Round 2 指出安全关键固定值与完整成员集合仍未校验。第二次修复后，三份新 policy、rc2/rc3 兼容 policy 与内存 gate 共用完整嵌套字段、类型、枚举、固定安全值和跨字段约束，并有 JSON/Markdown/内存表驱动负例；Round 3 `Closed`。
- `ADF-V010-CORE-SPLIT-R002`（P2）：Round 1 指出 `InspectAndResolve` 可能改变旧版未知输入 fail-closed 语义。修复：限定为进入 route 前的只读解析动作，所有权限、外部证据、规则冲突及最终未解析输入仍为 `Blocked`，并增加兼容测试；Round 2 `Closed`，Round 3 无回归。
- Round 1 Reviewer：same-Harness native isolated Codex CLI，只读、ephemeral；session=`019fe0b5-4f63-7503-a23a-3264ec35956b`；结论 `Needs Fix`，P0/P1/P2/P3=`0/1/1/0`。
- Round 2 Reviewer：same-Harness native isolated Codex CLI，session=`019fe0be-4b39-77b1-87c0-0d164bb292ee`；结论 `Needs Fix`，P0/P1/P2/P3=`0/1/0/0`。`R002` 已关闭；`R001` 因安全关键固定值与完整成员集合仍未校验而保持开放。Reviewer 触发 Python 字节码缓存，未产生 tracked 产品 diff。
- Round 3 Reviewer：same-Harness native isolated Codex CLI，session=`019fe0c7-1b7e-7463-ae9d-2a670ffabbe7`；结论 `Passed`，P0/P1/P2/P3=`0/0/0/0`；`R001/R002` 全部 Closed。Review 不代表 UA、commit、merge、release 或 Closed。

## Outcome

- Base / Diff：base=7f2686f1492496adf2a71e2d981772502c7097e9;diff=7f2686f1492496adf2a71e2d981772502c7097e9..9ac594d
- 隔离位置：`codex/v010-core-split` / `D:/open-source/ai-dev-flow-wt/v010-core-split`。
- 回滚方式：提交前丢弃本 TASK 精确 diff；提交后 revert 阶段 commit，不改写历史。
- 修改文件：治理入口与兼容说明、三份 canonical JSON policy、严格只读 loader、Repair gate、相关 README/测试，以及本阶段 TASK/看板事实源；`dashboard/**` 无 diff。
- 验证证据：Stage 1 Skill `99/99`、backend `174/174`、workflow lint `errors=0 / violations=0 / warnings=63`、`git diff --check` 均通过；安全约束定向测试 `53/53` 通过；Dashboard tracked diff 为空，核心 policy 具体 Harness/模型名匹配 `0`。Stage 0 frontend Vitest `95/95`、Playwright `96/96` 通过；Integration 基线 `1 failure + 1 error` 均在 Dashboard 禁止修改范围，已在 Master 记录。
- Review findings：Round 3 `Passed`，P0/P1/P2/P3=`0/0/0/0`；`R001/R002` Closed。
- UA 动作与结果：UA3 Pending，不由自动验证代替。
- 状态边界：实现提交 `9ac594d`、Review 收据提交 `314ef09` 已推送至 `origin/codex/v010-core-split`；Draft PR [#14](https://github.com/a-littlecat/ai-dev-flow/pull/14) 已创建。UA3 Pending；未 merge / release / 正式 Skill 同步 / Closed。
- 剩余风险：UA3 仍为 Pending；Review 通过不授权 merge、release、正式 Skill 同步或 Closed。
- 下一步：提交并推送本 delivery 收据；随后从阶段 HEAD 建立 CAPABILITY-REVIEW stacked branch/worktree。
