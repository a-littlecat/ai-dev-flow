# ADF-V010-CORE-SPLIT：拆分治理核心与 Repair Policy

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `ADF-V010-CORE-SPLIT`
- `task_type`: `code`
- `task_class`: `D`
- `lifecycle`: `Review`
- `review_status`: `Needs Fix`
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
- [x] 外部 findings 修复后的 same-Harness 内部隔离只读 Review 无开放 P0/P1；跨 Harness 外部复审发现 P2/P3 后已进入修复，重审 Pending。

## Repair Chain Ledger（仅进入 repair 时填写）

- `ADF-V010-STACKED-EXT-P1-002`（P1，外部复审）：`policy_loader.py` 把 canonical policy 的完整风险标志、固定数组和当前值复制进 Python，形成第二事实源。修复合同：由受信任 registry 锁定的 `policy/schemas/*.schema.json` 验证结构、类型、枚举与不可弱化的安全不变量；Python 仅保留通用 Schema 解释和跨字段关系，不复制 canonical 数组或当前决策值。外部修复 Round 1 的独立复审仍为 `Needs Fix`：schema 曾允许重绑 digest 后删除 hard-stop、权限绑定或关闭 trusted context；Round 2 已把这些安全不变量迁入 Schema，并补齐 JSON/Markdown/内存与重绑 digest 负例、registry 与 `$ref` confinement 测试，等待新隔离复审。
- 外部修复 Round 1 Reviewer：same-Harness native isolated Codex CLI，只读、ephemeral；session=`019fe1dc-ef16-7b53-ac4b-12030669c68c`；结论 `Needs Fix`，P0/P1/P2/P3=`0/1/0/0`，稳定 finding=`ADF-V010-STACKED-EXT-P1-002`。该收据不替代修复后的新 Review。
- 外部修复 Round 2 Reviewer：same-Harness native isolated Codex CLI，只读、ephemeral；结论 `Needs Fix`，P0/P1/P2/P3=`0/1/2/0`。P1 证明 `required_true_fields/required_false_fields` 可删除安全成员并在重绑 digest 后获得 `MechanicallyEligible`，且 `$ref` 兄弟关键字可能被忽略；P2 指出未跟踪缓存污染范围证明与 TASK/BOARD 测试计数不一致。Round 3 已锁定这些安全成员与 `$ref`/legacy optional 使用上下文、统一计数，并把 9 个可再生缓存目录可恢复地移出 Worktree；等待新 Review。
- 外部修复 Round 3 Reviewer：same-Harness native isolated Codex CLI，只读、ephemeral；session=`019fe1fc-dc17-7621-9e7c-8a2cf8460dc0`；结论 `Needs Fix`，P0/P1/P2/P3=`0/2/0/0`。P1 证明 `repair_gate.py` 的固定 `AR-3` 无法随普通轮次值演进，并指出看板顶层仍残留历史 `Review Passed`。Round 4 已将下一 attempt ID 改为按 `used + 1` 派生并补 gate 回归测试，同时统一 TASK/BOARD 当前状态；等待新 Review。
- 外部修复 Round 4 Reviewer：same-Harness native isolated Codex CLI，只读、ephemeral；session=`019fe20a-1be4-7542-91b6-f9a2f218f9ce`；结论 `Passed`，P0/P1/P2/P3=`0/0/0/0`。`ADF-V010-STACKED-EXT-P1-002` 与状态 finding 均 Closed；该 Review 不代表 UA、commit、push、merge、release、正式 Skill 同步、Accepted 或 Closed。
- 跨 Harness 外部复审（分支头 `397acae`）：Kimi session=`session_24441a41-432e-47cc-9f22-25b384b5ed7b`，结论 `Passed`，P0/P1/P2/P3=`0/0/1/3`；Grok session=`019fe5f0-70d5-7b62-b9b7-f24d57e1629e`，结论 `Passed`，P0/P1/P2/P3=`0/0/1/2`。共同或有效 findings：部分 canonical 成员集合可被 Schema 接受为子集、兼容文档仍把 `CORE.md` 写成事实源、受信任循环 `$ref` 未 fail-closed、测试 helper 固定 `AR-3`、分支头收据陈旧。已修复前四项并增加回归测试；分支头改由 PR/Git 外部引用提供，避免在提交内容中循环记录自身哈希。等待两 Harness 对新提交重审。
- 跨 Harness 外部重审（分支头 `385a4ec`）：Kimi session=`session_dac67dc2-dcb8-474a-8ed6-7a5a8e3d92e8`，结论 `Passed`，P0/P1/P2/P3=`0/0/0/2`；Grok session=`019fe6b6-2913-7282-acb0-ef6ad5eac73d`，结论 `Passed`，P0/P1/P2/P3=`0/0/0/0`。Kimi 的两个有效 P3 为：`contains` 不应吞掉 Schema 定义错误，以及按需兼容文档不应继续指向 `CORE.md` progress/policy。当前已用 `PolicySchemaError` 区分 Schema 定义错误与值不匹配并补回归测试，同时统一 7 份兼容文档到 canonical Policy JSON；等待新 head 双 Harness 重审。
- 跨 Harness 外部重审（分支头 `bc7fd13`）：Kimi session=`session_62305337-21f3-4e86-9ecb-8bed6c6631e6` 与 Grok session=`019fe6bd-e305-7ff2-852d-ff3e24967d1f` 均为 `Needs Fix`，P0/P1/P2/P3=`0/0/0/1`。共同 finding=`V010-CS-EXT6-001`：4 份兼容文档其他段落仍复制基础/额外/最大轮次数字，因此 `EXT5-002` 仅部分关闭。当前已把全部非 prototype 活跃文档中的固定 repair 轮次、profile 阈值和默认授权次数改为 canonical Policy/receipt 相对表述；prototype 仍为默认关闭的独立 v0.8 评估资产，不属于 v0.10 canonical 路径。等待新 head 双 Harness 重审。
- 跨 Harness 外部重审（分支头 `e8ebcc2`）：Kimi session=`session_0c4e8c4a-00a5-4f12-891a-531536c79ebb` 结论 `Needs Fix`，P0/P1/P2/P3=`0/0/0/4`；Grok session=`019fe6c4-debb-7fc0-a540-ea847d43126b` 结论 `Needs Fix`，P0/P1/P2/P3=`0/0/0/1`。共同结论是 `V010-CS-EXT6-001` 仍未关闭：Skill 主入口、README、REPAIR_BASIC、scripts README 与现行看板停止条件等仍有同类固定值。当前已补齐这些非 prototype 现行规范位置；Board 的历史用户消息、授权和已完成任务收据保留原值，不作为当前 Policy 事实源。等待新 head 双 Harness 重审。
- `ADF-V010-CORE-SPLIT-R001`（P1）：Round 1 指出 loader 只校验顶层；Round 2 指出安全关键固定值与完整成员集合仍未校验。第二次修复后，三份新 policy、rc2/rc3 兼容 policy 与内存 gate 共用完整嵌套字段、类型、枚举、固定安全值和跨字段约束，并有 JSON/Markdown/内存表驱动负例；Round 3 `Closed`。
- `ADF-V010-CORE-SPLIT-R002`（P2）：Round 1 指出 `InspectAndResolve` 可能改变旧版未知输入 fail-closed 语义。修复：限定为进入 route 前的只读解析动作，所有权限、外部证据、规则冲突及最终未解析输入仍为 `Blocked`，并增加兼容测试；Round 2 `Closed`，Round 3 无回归。
- Round 1 Reviewer：same-Harness native isolated Codex CLI，只读、ephemeral；session=`019fe0b5-4f63-7503-a23a-3264ec35956b`；结论 `Needs Fix`，P0/P1/P2/P3=`0/1/1/0`。
- Round 2 Reviewer：same-Harness native isolated Codex CLI，session=`019fe0be-4b39-77b1-87c0-0d164bb292ee`；结论 `Needs Fix`，P0/P1/P2/P3=`0/1/0/0`。`R002` 已关闭；`R001` 因安全关键固定值与完整成员集合仍未校验而保持开放。Reviewer 触发 Python 字节码缓存，未产生 tracked 产品 diff。
- Round 3 Reviewer：same-Harness native isolated Codex CLI，session=`019fe0c7-1b7e-7463-ae9d-2a670ffabbe7`；结论 `Passed`，P0/P1/P2/P3=`0/0/0/0`；`R001/R002` 全部 Closed。Review 不代表 UA、commit、merge、release 或 Closed。

## Outcome

- Base / Diff：base=9a8642a;diff=9a8642a..bed3ac9
- 隔离位置：`codex/v010-core-split` / `D:/open-source/ai-dev-flow-wt/v010-core-split`。
- 回滚方式：提交前丢弃本 TASK 精确 diff；提交后 revert 阶段 commit，不改写历史。
- 修改文件：治理入口与兼容说明、三份 canonical JSON policy、严格只读 loader、Repair gate、相关 README/测试，以及本阶段 TASK/看板事实源；`dashboard/**` 无 diff。
- 验证证据：Stage 1 Skill `99/99`、backend `174/174`、workflow lint `errors=0 / violations=0 / warnings=63`、`git diff --check` 均通过；安全约束定向测试 `53/53` 通过；Dashboard tracked diff 为空，核心 policy 具体 Harness/模型名匹配 `0`。Stage 0 frontend Vitest `95/95`、Playwright `96/96` 通过；Integration 基线 `1 failure + 1 error` 均在 Dashboard 禁止修改范围，已在 Master 记录。
- Review findings：Round 3 `Passed`，P0/P1/P2/P3=`0/0/0/0`；`R001/R002` Closed。
- 外部 stacked finding 修复：原 P1/P2 已关闭；`e8ebcc2` 双 Harness 共同指出的 P3 残留已补齐，Skill 主入口及全部非 prototype 现行规范改为 canonical Policy/authority receipt 相对表述，历史事实收据不改写。fresh Skill `106/106`、workflow lint `errors=0 / violations=0 / warnings=1` 与 `git diff --check` 已通过；宽模式扫描仅剩 rc2 旧单次 receipt 的兼容类型说明，不是当前默认授权次数。新 head 双 Harness 重审 Pending。backend `173/174`：`test_non_recursive_request_ignores_nested_file_changes` 在 #14 与无 Dashboard diff 的既有工作区均可复现，属于当前 Windows/Python 3.13 基线边界，本阶段未修改 `dashboard/**`。
- UA 动作与结果：UA3 Pending，不由自动验证代替。
- 状态边界：Internal Isolated Repair Review Passed / External Review Needs Fix / External Re-review Pending / branch pushed（精确 head 以 PR/Git ref 为准）/ UA3 Pending。未 merge / release / 正式 Skill 同步 / Accepted / Closed。
- 剩余风险：UA3 仍为 Pending；Review 通过不授权 merge、release、正式 Skill 同步或 Closed。
- 下一步：完成 fresh 验证并由 Kimi、Grok 对新提交分别执行跨 Harness 外部只读复审；不得由测试或内部 Review 推导 UA、merge 或其他后续生命周期动作。
