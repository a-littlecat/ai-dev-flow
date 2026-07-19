# PLAN-001：规划前沿模型时代的 Skill 瘦身与净收益门禁

## 任务元数据

| 字段 | 当前值 |
|---|---|
| 任务编号 | `PLAN-001` |
| 任务类型 | 方案 |
| 当前模式 | Accepted Git baseline 提交（`close_task` 交付写回） |
| 任务状态 | 已验收（`Accepted`） |
| 优先级 | 高 |
| 风险等级 | 高 |
| 任务分级 | C：改变默认工作流入口、运行时加载面和 v0.8 实施顺序 |
| 建议执行位置 | 当前分支 `codex/plan-001-loop-decision-rfc`；已形成 Accepted 记录，但实现和 Git baseline 仍须另行授权 |
| 独立审查 | 必须 |
| 用户动作等级 | UA2：阅读并确认瘦身方向与成本上限 |
| 前置任务 | `REL-002` Closed；Base `0422887` |
| Base commit | `042288713ab41a7bab73d1ec18a86c80679ba287` |
| 计划产物 | `docs/plans/V0.8_SKILL_SLIMMING_RFC.md` |

## 需求变更与重开原因

原 PLAN-001 把用户的整体优化需求收窄成 Review-Repair Loop 决策，并进一步产生 9 个串行 Draft TASK。用户明确指出这不是项目瘦身，并授权修改或推翻 PLAN-001。

因此：

- 原 Loop RFC 的 Review、UA 和 Accepted 结论不再作为当前方案的验收依据；
- PLAN-001 重新进入待审查（`Review`）；
- 原 Loop RFC、`LOOP-001`～`LOOP-009` 均未提交、未形成 baseline，已从当前规划集移除；
- 当前唯一验收对象是整体 Skill 瘦身 RFC。

## 当前基线

| 指标 | 当前值 |
|---|---:|
| Skill 文件 | 85 |
| Markdown 文件 / 行 | 69 / 8227 |
| `references/` 文件 / 行 | 36 / 6320 |
| `SKILL.md` | 288 行 |
| `WORKFLOW.md` | 615 行 |
| `TASK_TEMPLATE.md` | 389 行 |
| `PROMPTS.md` | 1182 行 |
| 原 v0.8 后续任务 | 9 个，已从未提交规划集移除 |

## 目标

- 把 ai-dev-flow 定位为按风险启用的治理内核，而不是所有任务的强制流程。
- 明确 Lite / Tracked / Controlled 三档入口和升级条件。
- 量化减少运行时文档、模型调用、用户打断和后续任务数量。
- 用确定性风险闸门补齐自动审核，避免低风险强制审查和高风险漏审。
- 用 progress / stall 证据决定是否自动授予第 3 轮修复，避免机械地在两轮后让用户接管。
- 把收益 eval 前置，真实模型对照设置硬额度上限。
- 为“没有正收益就停止扩建”建立退出条件。

## 非目标

- 不修改现行 `skills/ai-dev-flow/` 实现、模板、脚本或测试。
- 不创建 `LEAN-*` 实施任务；须在本计划 Review 与 UA2 后另行授权。
- 不调用 GPT、Kimi、Claude 或其他外部模型做对照测试。
- 不 commit、merge、push、release 或同步本机 Skill。
- 不把任何厂商模型设为核心依赖。

## 允许修改范围

- `docs/plans/V0.8_SKILL_SLIMMING_RFC.md`
- `docs/tasks/PLAN-001.md`
- `docs/TASK_BOARD.md`
- 删除同一未提交规划集中被本方案取代的原 Loop RFC、旧 PLAN-001 文件、`LOOP-001`～`LOOP-009` 和临时 PLAN-002。

## 禁止修改范围

- `skills/ai-dev-flow/**`
- 所有代码、测试、版本、发布和本机 Skill 文件
- 已提交的 v0.7 历史任务和 release artifacts

## 规划结论

- 保留项目，但只把状态、权限、证据、Git 和高风险停止条件作为核心价值。
- Lite 成为默认，但必须有覆盖全部关键完成标准的确定性验证；“容易回滚”不能替代验证，存在用户观察或真实环境证据时升级 Tracked。
- Lite 不创建 TASK、不调用独立 Reviewer、不进入 repair loop。
- 首版实现确定性自动审核闸门：Lite 禁止，Tracked 风险触发，Controlled 交付前强制；Tracked 命中门禁但缺少 Reviewer authority/capability 时必须 Blocked、合法升级或取得用户明确授权的独立 Reviewer，不建设通用调度平台。
- Tracked / Controlled repair 基础预算为 2；只有范围冻结、finding 单调减少且验证改善时自动增加第 3 轮，3 为绝对上限。
- Reviewer 独立性指只读职责和上下文隔离，不要求不同厂商；模型 Adapter 和看板 Loop 投影仍延期。
- 先冻结样本/标签/计量协议并做零额度回放；通过后仅制作默认关闭、可整体回退的最小原型，再用一个前沿模型、一个 Lite 代表任务完成最多 3 次对照；全部门槛通过后才全面收缩和迁移。
- 候选实施链最多 3 个 LEAN TASK，验收前不创建。

## 关键量化门槛

- Lite 运行时除 `SKILL.md` 外最多读取 1 份 reference，总工作流说明不超过 400 行。
- Tracked 默认最多读取 3 份 reference。
- 活跃核心 reference 目标不超过 12 份；历史兼容资料可保留但不默认加载。
- `PROMPTS.md` 退出运行时，短入口不超过 6 个、总计不超过 200 行。
- Lite 独立 Reviewer、跨模型调用和自动 repair 扩展均为 0。
- Tracked 未命中风险闸门时 Reviewer 为 0；命中后只使用一个隔离 Reviewer 上下文。
- Controlled 必须有一个可用的隔离 Reviewer 上下文；缺少 authority / capability 时不得自批。
- Tracked / Controlled 最多 3 轮 repair、4 轮 Review；模型或供应商更换不重置计数。
- 小样本真实模型对照总执行不超过 3 次，禁止厂商 fan-out。
- Lite 相对现行 Full 的工作流输入、模型调用和用户流程问题均至少减少 50%，且不得增加 P0/P1 漏检、权限越界或状态误报。
- 计量单位固定为工作流输入 UTF-8 字节/非空行、模型请求次数、需用户回复的阻塞问题、逐完成标准验证结果、expected/actual 安全标签和 repair trace 决策。
- 维护预算：活跃核心 reference 不超过 12、新增核心文件不超过 2、活跃规范行数不高于冻结基线；迁移预算：用户步骤不超过 3、历史 TASK 批量改写为 0、新 required dependency 为 0、实施 TASK 不超过 3。
- 样本不足时只能写“固定样本未观察到漏检”或“证据不足”，不得外推为普遍不增加 P0/P1。

## 候选实施链

本计划通过后才允许另行创建，当前不存在：

1. `LEAN-001`：冻结样本 manifest、expected labels、统计命令和 ledger schema，执行零额度回放并形成三档路由/保留清单/基线报告。
2. `LEAN-002`：只制作默认关闭、可整体回退的最小原型，完成最多三次 Lite 小样本真实对照；不得全面迁移或默认启用。
3. `LEAN-003`：仅在全部门槛通过后全面精简 Skill、核心 references 和模板，收敛自动审核/第 3 轮规则，编写迁移说明并作是否发布 v0.8 的最终决策。

## 完成标准

- [x] 明确原 PLAN-001 为什么不是瘦身，并完成重开。
- [x] 有当前规模基线。
- [x] 有三档模式、升级条件和每档默认禁止项。
- [x] 有 keep / simplify / retire 清单。
- [x] 有运行时文档和模型调用硬预算。
- [x] 有 Lite / Tracked / Controlled 的自动审核触发、跳过、输入、输出和降级规则。
- [x] 有 Tracked / Controlled 第 3 轮修复的自动授予条件、停止条件和绝对上限。
- [x] 有零额度优先的对照 eval 与量化通过门槛。
- [x] Lite 明确要求确定性验证覆盖完成标准，容易回滚不再替代验证或用户观察。
- [x] Tracked 命中审核门禁但缺 Reviewer 时有 Blocked / 合法升级 / 明确授权的降级路径。
- [x] 实施顺序固定为回放、最小原型与对照、通过后全面收缩。
- [x] 固定样本、expected labels、计量单位、维护/迁移预算和证据不足结论限制可复现。
- [x] 有 9 -> 最多 3 的实施链收缩方案。
- [x] 有无收益退出条件和回滚路径。
- [x] 独立 Review 完成且无 P0/P1。
- [x] 用户完成新的 UA2；本次验收依据为用户在 2026-07-19 明确确认“审核及验收通过”，未沿用原 Loop 方案的 UA。

## 验证方式

- 核对最终范围只包含本 RFC、本 TASK 和 `docs/TASK_BOARD.md`。
- 运行 41 项单元测试，确认规划没有改变现行行为。
- 运行 `workflow_lint.py`，记录相对基线增量。
- 运行 tracked 与 untracked Markdown whitespace check。
- 检查 Markdown 引用、任务 ID 唯一性和已删除旧路径不存在。

## 风险与停止条件

- 如果计划继续新增超过 3 个首版实施任务，停止并重新证明必要性。
- 如果瘦身需要自动调度器、数据库、遥测或计费系统，停止。
- 如果 Lite 会绕过 authority、真实环境或不可逆操作门禁，停止。
- 如果自动审核需要通用调度器、数据库或模型 Adapter，停止；首版只能保留确定性闸门。
- 如果第 3 轮没有 finding 减少和验证改善证据，或试图重试不可逆外部动作，停止。
- 如果计划把某个模型设为核心依赖，停止。
- 如果对照未达到净收益门槛，停止 v0.8 扩建并退回最小治理核心。

## 当前结果

- 整体瘦身 RFC 已完成第 1 轮有限修复和独立复审：4 项 P1 均已关闭，未发现新的 P0～P3；用户已完成新的 UA2，PLAN-001 已流转为 `Accepted`。
- 原未提交 Loop 扩建 RFC 和 9 个 Draft TASK 已移除。
- 临时 PLAN-002 已移除，避免两个计划并存。
- 本轮没有修改 Skill、代码、测试或现行规则。
- 本轮没有运行外部模型评估，也没有创建 `LEAN-*`、修改现行 Skill 或自批 Review。

## 修改文件

| 文件 | 主要改动 |
|---|---|
| `docs/plans/V0.8_SKILL_SLIMMING_RFC.md` | 形成三档路由、自动审核闸门、受控修复延长、运行时预算、额度门禁、前置 eval 和退出条件 |
| `docs/tasks/PLAN-001.md` | 重开 PLAN-001，替换原 Loop 扩建范围，并写入审核/修复缺口的完成标准 |
| `docs/TASK_BOARD.md` | 收缩为当前事实、任务索引、授权边界、审核/修复核心约束和下一动作 |

## 验证结果

- 最终规划范围只有上述 3 个文件：1 个 tracked 修改、2 个 untracked 新文件。
- 旧 Loop RFC、9 个 `LOOP-*` 和临时 PLAN-002 路径已不存在。
- 单元测试：41 / 41 通过。
- PLAN-001 targeted lint：`errors=0`、`violations=0`、`warnings=2`；两项 warning 为 Legacy 映射和未形成 Git transition baseline。
- 全仓 lint：`errors=19`、`violations=0`、`warnings=18`；19 项 error 全部来自既有 `CONTRACT-001`～`006` legacy 记录，本任务未新增 violation。
- `git diff --check`：通过；两个 untracked Markdown 的 no-index check 仅返回“存在新增差异”的预期 code 1，没有 whitespace 报告。
- 本地 Markdown 链接：9 个，缺失 0。
- 自动审核 / 第 3 轮合同断言：`errors=0`；旧延期表述和已移除旧路径均未残留。
- 验收写回复验：PLAN-001 targeted lint 为 `errors=0`、`violations=0`、`warnings=3`；全仓 lint 为 `errors=19`、`violations=0`、`warnings=19`；提交前 Contract 投影为 `Accepted / Review Passed / UA2 Passed / User Confirmed / Committed / Unmerged`，任务与看板无状态漂移。

## 代码审查

- 审查状态：复审通过
- 审查范围：本 RFC、本 TASK 和看板的最终三文件增量。
- 审查日期：2026-07-19
- 审查角色：Reviewer；本轮只记录 finding，不修改 RFC 方案。
- 审查结论：通过（`Passed`）；第 1 轮 4 项 P1 均已关闭，未发现新的 P0～P3。
- 最高严重等级：无；P0 0 项，P1 0 项，P2 0 项，P3 0 项。
- 是否允许进入验收建议：是；允许进入 UA2，但 Review Passed 不等于 UA2、Accepted、commit、merge 或规则生效。
- 复审证据：逐项核对 RFC 修订、历史 P1 样本来源、三文件范围、41 项单元测试、targeted/full lint、tracked/untracked whitespace、9 个本地链接、冲突标记和敏感信息扫描。

### P0 必须修改项

- 无。

### 第 1 轮 P1（复审已关闭）

#### `PLAN-001-P1-001`：Lite 可能跳过必要的用户验证

- 证据：`docs/plans/V0.8_SKILL_SLIMMING_RFC.md:72-86`。
- 问题：Lite 准入条件允许“有确定性验证或容易回滚”，同时取消完整 UA 记录并在验证通过后立即结束。小型 UI、交互或其他用户可见改动可能仅因容易回滚而进入 Lite，却没有覆盖完成标准的确定性验证或最小用户验收。
- 风险：用户可观察结果可能未验证即被流程视为结束，与“不能因瘦身绕过验收门禁”的目标冲突。
- 必须修复：明确 Lite 必须有覆盖完成标准的确定性验证；仅“容易回滚”不得替代验证。缺少确定性验证或需要用户观察结果时，必须升级到 Tracked，并保留最小用户验收步骤。
- 复审结论：已关闭。RFC §5.1 已把覆盖全部关键完成标准的确定性验证设为 Lite 必要条件，并规定用户观察、体验判断或真实环境证据升级到 Tracked。

#### `PLAN-001-P1-002`：Tracked 命中审核门禁后缺少 Reviewer 降级路径

- 证据：`docs/plans/V0.8_SKILL_SLIMMING_RFC.md:163-185`。
- 问题：Tracked 命中风险条件时要求启动独立 Review，但 Reviewer 与 Engineer 不能隔离时又禁止自动审核；RFC 只为 Controlled 定义了 Blocked / 降级规则，没有定义 Tracked 的合法后续状态。
- 风险：公共 API、共享组件或核心路径等已命中审核门禁的 Tracked 任务，可能因 harness 缺少隔离能力而静默跳过 Review。
- 必须修复：明确 Tracked 命中审核门禁但缺少 Reviewer authority / capability 时，只能进入 Blocked、升级 Controlled、取得人工/独立 Reviewer，或由用户明确授权其他安全降级；不得继续并视为 Review Passed。
- 复审结论：已关闭。RFC §8.1 已把 authority / capability 设为硬门禁，限定 Blocked、能提供合法 Reviewer 的升级或明确授权替代，并禁止把未执行 Review 记为 `Passed`。

#### `PLAN-001-P1-003`：“先验证收益再实施”与候选任务顺序矛盾

- 证据：`docs/plans/V0.8_SKILL_SLIMMING_RFC.md:232-254`、`275-277`。
- 问题：RFC 声明“先验证收益，再实施”，但候选顺序实际为 `LEAN-001` 历史回放、`LEAN-002` 完成 Skill 精简实现、`LEAN-003` 才做真实模型对照。
- 风险：关键实现成本可能在真实收益尚未验证前已经发生，且执行者无法判断 `LEAN-002` 应做到最小原型还是完整改造。
- 必须修复：明确分阶段门禁。`LEAN-002` 在真实对照前只能形成可回滚的最小原型/受控试点，还是可以完成全部精简，必须给出单一结论；如先做原型，应规定真实对照通过后才能继续全面收缩和迁移。
- 复审结论：已关闭。RFC §9.2、§9.4 和 §10 已固定为零额度回放、默认关闭且可整体回退的最小原型与三次对照、全部门槛通过后才全面收缩。

#### `PLAN-001-P1-004`：净收益门槛尚不可客观复现

- 证据：`docs/plans/V0.8_SKILL_SLIMMING_RFC.md:59-66`、`247-267`。
- 问题：净收益公式包含维护和迁移成本，但评估记录与通过门槛没有相应计量方法或上限；一个代表任务、三次执行只覆盖“无 Skill / Lite / Full”，没有实际覆盖 Tracked、Controlled、自动审核和第 3 轮修复。
- 风险：`LEAN-003` 可能在没有证明全部核心变更净正收益的情况下作出 v0.8 发布建议；“减少 50%”和“不增加漏检”也缺少冻结样本、统计单位和判定口径。
- 必须修复：补充可复现的评估协议，包括固定样本与预期标签、输入/调用/用户问题的计量单位、维护和迁移成本预算、各模式分别需要证明的结论，以及样本不足时不得作出“不增加 P0/P1 漏检”的强结论。
- 复审结论：已关闭。RFC §9.1～§9.3 已冻结 6 个路由样本和 2 个 repair trace、expected labels、逐样本 ledger、固定计量单位、维护/迁移预算、分模式有限结论和证据不足限制；`CONTRACT-002/003` 原任务记录确有已关闭的历史 P1，可作为对应回放来源。

### P2 / P3 建议项

- 无。

## 审查-修复循环（review_repair_loop）第 1 轮记录

- 当前轮次：1 / 2，仍遵守现行最多 2 轮规则；未使用候选第 3 轮规则自举。
- 本轮角色：修复者（Repairer），随后只切换 Verifier / Archivist；未担任 Reviewer，未自我批准。
- 修复范围：`docs/plans/V0.8_SKILL_SLIMMING_RFC.md`、本 TASK、`docs/TASK_BOARD.md`。

| 审查项 | 等级 | Repairer 处理 | 修订位置 |
|---|---|---|---|
| `PLAN-001-P1-001` | P1 | Lite 必须以覆盖全部关键完成标准的确定性验证为准；可回滚不再替代验证，需要用户观察时升级 Tracked | RFC §5.1、§8.1 |
| `PLAN-001-P1-002` | P1 | Tracked 缺 authority/capability 时限定为 Blocked、能提供合法 Reviewer 的 Controlled 升级、人工/独立 Reviewer 或用户明确授权；未审核不得记 Passed | RFC §8.1 |
| `PLAN-001-P1-003` | P1 | 单一实施顺序改为零额度回放、可回退最小原型与真实对照、全部通过后全面收缩 | RFC §9.2、§9.4、§10 |
| `PLAN-001-P1-004` | P1 | 冻结 8 个样本/trace、expected labels、计量单位、ledger、维护/迁移预算、分模式结论和样本不足限制 | RFC §9.1～§9.3 |

- 未处理意见：无；P2/P3 为 0。
- 修改文件：RFC、本 TASK、TASK_BOARD；未修改 Skill、代码、测试或现行规则。
- 验证结果：41 / 41 单元测试通过；PLAN-001 targeted lint 为 `errors=0`、`violations=0`、`warnings=2`；全仓 lint 为 `errors=19`、`violations=0`、`warnings=18`，19 项 error 均来自既有 `CONTRACT-001`～`006` legacy 记录；范围、空白、冲突标记、本地链接和 4 项 P1 合同断言通过。
- 是否需要再审查：否；独立 Reviewer 已逐项确认 4 项 P1 关闭，随后用户确认“审核及验收通过”。
- 是否触发人工接管：否。

## Diff 审查

- 审查状态：复审通过
- Base commit：`042288713ab41a7bab73d1ec18a86c80679ba287`
- 审查范围：`docs/plans/V0.8_SKILL_SLIMMING_RFC.md`、`docs/tasks/PLAN-001.md`、`docs/TASK_BOARD.md` 的工作区增量。
- 范围结论：规划增量仅包含上述 3 个文件；未发现 `skills/ai-dev-flow/**`、代码、测试、版本或发布文件越界修改。
- 自动验证：41 / 41 单元测试通过；PLAN-001 targeted lint 为 `0 errors / 0 violations / 2 warnings`；`git diff --check` 通过；9 个本地 Markdown 链接缺失 0。
- Diff 结论：通过；修订仍限定在 RFC、TASK 和 TASK_BOARD 三文件，未修改 Skill、代码、测试、版本或发布文件，4 项 P1 均已关闭且无新增 finding。
- 是否允许进入验收建议：是，建议 UA2。
- 是否允许合并：否；Review 与 UA2 已完成，但本轮没有 commit / merge 授权。

## 用户动作等级 / 验收建议

- 建议 UA：UA2。
- 用户动作等级：UA2
- 用户需要做什么：已阅读并确认瘦身 RFC 的方向、复杂度与成本上限。
- agent 已提供的证据：三文件 diff 范围、独立复审结论、41 / 41 单元测试、targeted/full lint、whitespace、本地链接和 4 项 P1 关闭记录。
- 验收确认：用户已确认
- 当前状态：独立复审通过，用户已完成新的 UA2；任务已 `Accepted`。
- 本任务不要求实机测试。
- 新 UA2 不自动授权创建 LEAN TASK、修改 Skill、commit、merge、push 或 release。
- 是否允许关闭任务：否；本次用户确认包含 Review 与 UA2，不包含 `Closed`。

## 用户验收反馈 / 实机测试反馈

- 验收反馈状态：通过
- 用户确认记录：用户于 2026-07-19 明确表示“审核及验收通过”。
- 当前反馈关联的 UA 等级：UA2。
- 反馈分类：接受本 RFC 的三档路由、成本上限、审核/修复门禁、分阶段评估和无收益退出策略。
- 授权边界：只确认 Review Passed 与 UA2 Passed；不授权创建或执行 `LEAN-*`、修改 Skill、commit、merge、push、release、本机同步或 `Closed`。
- 下一步建议：用户已单独授权形成可引用的 Accepted Git baseline；后续是否创建 `LEAN-001` 仍需另行授权。

## 提交 / 合并

- Commit 状态：已提交
- 合并状态：未合并
- Commit 授权：用户于 2026-07-19 明确要求“提交”；本记录所在 commit 承载 PLAN-001 Accepted baseline，精确 hash 以 `git log` 为准。
- 未取得 merge、push、release、本机同步或 `Closed` 授权。

## 下一步

1. PLAN-001 已完成 Review 与 UA2，记录为 `Accepted`，并由用户授权形成 Accepted Git baseline。
2. merge、push、release、本机同步和 `Closed` 仍须分别授权。
3. 如需进入实施阶段，须另行授权创建 `LEAN-001`；本次提交不授权创建或执行 `LEAN-*`。
