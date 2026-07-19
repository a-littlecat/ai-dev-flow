# LEAN-001：冻结 v0.8 评估合同并执行零额度回放

## 任务元数据

| 字段 | 当前值 |
|---|---|
| 任务编号 | `LEAN-001` |
| 任务类型 | 测试 |
| 当前模式 | 等待第 2 轮有限修复（`repair_task`） |
| 任务状态 | 需修复（`Needs Fix`） |
| 优先级 | 高 |
| 风险等级 | 中 |
| 任务分级 | C：新增可复现评估工具和冻结证据，但不修改现行 Skill 行为 |
| 建议执行位置 | 独立分支 `codex/lean-v08-slimming` |
| 独立审查 | 必须 |
| 用户动作等级 | UA3：查看回放、hash 与门禁证据 |
| 前置任务 | `PLAN-001` Accepted；Accepted baseline `54ebc98`，术语澄清 HEAD `b7938ef` |
| Base commit | `b7938ef61a13ddb1ea22787c9a9a2d70298aadd4` |

## 背景

`PLAN-001` 规定 v0.8 必须先冻结样本、expected labels、统计命令和 ledger schema，再执行不调用额外模型的零额度回放。只有阶段 A 通过，才能制作默认关闭的最小原型并进入三模式真实任务对照。

## 目标与边界

- 目标：冻结评估合同并用只读标准库工具完成 6 个路由样本与 2 个 repair trace 的零额度回放。
- 非目标：不修改现行 Skill，不制作原型，不执行当前模型真实任务对照。
- 允许修改：`evaluations/v0.8/**`、本任务和 `docs/TASK_BOARD.md`。
- 禁止修改：`skills/ai-dev-flow/**`、历史任务、版本、发布、远程仓库和本机 Skill。
- 完成标准：全部冻结 hash 可复算，8 个样本 expected / actual 差异为 0，且独立 Review 无 P0/P1。
- 验证命令或检查：`replay.py verify`、`replay.py replay --check`、代表任务 4 项测试、仓库 41 项测试、targeted lint、JSON/AST 和 diff hygiene。

## 目标

- 冻结 6 个路由样本、2 个 repair trace，以及它们引用的 commit、TASK、Review、验证记录 hash。
- 固定工作流输入、模型调用、用户流程问题、任务结果、审核质量、repair、维护成本和迁移成本的计量单位与判定规则。
- 冻结阶段 B 的 Lite 代表任务、执行顺序、验收 oracle 和同基线要求。
- 提供只读、标准库实现的回放脚本，逐项输出 expected / actual / difference ledger。
- 形成三档路由、keep / simplify / retire、当前规模基线和阶段 A 门禁报告。

## 非目标

- 不修改 `skills/ai-dev-flow/**` 现行实现、模板、入口或测试行为。
- 不制作 Lite 原型，不执行当前模型真实任务对照。
- 不接入额外模型、数据库、遥测、计费系统或 required dependency。
- 不 merge、push、release、同步本机 Skill 或关闭 PLAN-001。

## 允许修改范围

- `evaluations/v0.8/**`
- `docs/tasks/LEAN-001.md`
- `docs/TASK_BOARD.md`

## 禁止修改范围

- `skills/ai-dev-flow/**`
- 已提交的 `REL-*`、`CONTRACT-*` 与 `PLAN-001` 历史记录
- 版本、发布、远程仓库和本机 Skill 副本

## Git 信息

- 当前分支：`codex/lean-v08-slimming`
- 执行位置：独立分支
- Worktree 路径：不适用
- Base commit：base=b7938ef61a13ddb1ea22787c9a9a2d70298aadd4;diff=b7938ef..HEAD
- 当前 HEAD：`05d6828`（第 1 轮 repair commit）
- Diff 范围：`b7938ef..05d6828`
- 是否有未提交改动：开始前否
- 是否存在不应提交文件：否
- 是否允许 commit：是；按 LEAN 任务保留独立 commit
- 是否允许合并：否

## 依赖关系

- 前置任务：`PLAN-001` Accepted。
- 后续任务：`LEAN-002`；仅在本任务阶段 A 门禁通过后允许创建并执行。
- 外部依赖：无。
- 必须串行原因：`LEAN-002` 必须消费本任务冻结的协议，不能追溯修改单位、阈值、样本或 oracle。

## 执行步骤

1. 冻结样本来源、commit 和文件 hash。
2. 冻结代表任务、执行顺序、计量协议和 ledger schema。
3. 实现只读回放器和机械门禁判定。
4. 执行 6 个路由样本和 2 个 repair trace 回放。
5. 输出原始 ledger、阶段 A 报告和当前规模基线。
6. 运行自动验证并进入独立 Review。

## 完成标准

- [x] 6 个路由样本与 2 个 repair trace 均有稳定 ID、冻结来源、expected / actual 和 difference。
- [x] 历史样本引用的 commit、TASK、Review 与验证记录可逐项 hash 校验。
- [x] Lite / Tracked / Controlled 路由、审核门禁、authority / delivery 和 repair extend / stop 均与预期一致。
- [x] 代表任务、执行顺序、oracle、统计单位与零分母规则在原型前冻结。
- [x] ledger schema 能逐样本记录原始数据，不只记录汇总结论。
- [x] 当前规模、keep / simplify / retire 和维护/迁移预算可机械复算。
- [x] 回放不修改现行 Skill，不调用模型或外部服务，不引入依赖。
- [ ] 独立 Review 无 P0/P1。

## 自动验证命令

```powershell
python -B -X utf8 evaluations/v0.8/replay.py verify
python -B -X utf8 evaluations/v0.8/replay.py replay --check
python -B -X utf8 -m unittest discover -s skills/ai-dev-flow/tests -p "test_*.py" -v
python -B -X utf8 skills/ai-dev-flow/scripts/workflow_lint.py docs/tasks/LEAN-001.md --format human
git diff --check
```

补充静态检查：解析 `replay.py` AST，并解析 `evaluations/v0.8/**` 下全部 JSON。仓库与本机安装副本均不存在旧的 `quick_validate.py`，不得把历史命令伪装成本轮已执行验证。

## 验证结果

- `replay.py verify`：通过；6 个路由样本、2 个 repair trace、历史 Git 对象/hash 与冻结规模基线全部一致。
- `replay.py replay --check`：通过；8 条原始记录，expected / actual 差异 0，模型/Reviewer/subagent 调用 0。
- 评估工具专项回归：7 / 7 通过；覆盖旧伪造 payload、错 baseline hash、空 oracle、负数、Denied/Unknown authority、新增 P0、严重度升级和非法轮次。
- 代表任务基线：4 / 4 单元测试通过。
- 仓库回归：41 / 41 单元测试通过。
- 静态检查：`replay.py` AST 与 `evaluations/v0.8/**` 全部 JSON 解析通过。
- targeted workflow lint：0 error / 0 violation / 1 warning；warning 为预期 Legacy 映射。
- `git diff --check`：通过。
- 历史验证命令漂移：仓库及本机安装副本均不存在旧 `quick_validate.py`；本任务未声称执行该命令，使用当前真实验证入口替代。

## 执行结果

- 状态：已完成，等待独立 Review。
- 执行摘要：已冻结评估 manifest、ledger schema、代表任务、历史证据和统计协议，并完成零额度回放。
- 实际验证结果：8 / 8 expected 与 actual 一致；代表任务 4 / 4、仓库回归 41 / 41 通过。

## Outcome

- Base / Diff：base=b7938ef61a13ddb1ea22787c9a9a2d70298aadd4;diff=b7938ef..05d6828
- 隔离位置：独立分支 `codex/lean-v08-slimming`。
- 回滚方式：回退本任务独立 commit；不得使用破坏性 reset。
- 修改文件：`evaluations/v0.8/**`、`docs/tasks/LEAN-001.md`、`docs/TASK_BOARD.md`。
- 验证证据：8 / 8 回放一致；7 / 7 评估工具专项、4 / 4 代表任务、41 / 41 仓库回归、JSON/AST、targeted lint 与 diff hygiene 通过。
- Review findings：`LEAN001-P1-001-R1`；每个 run 尚未强制恰好一个 main，可能突破三次主任务硬上限。

## 修改文件

| 文件 | 修改说明 |
|---|---|
| `docs/tasks/LEAN-001.md` | 记录任务边界、Git 基线、验证与后续证据 |
| `docs/TASK_BOARD.md` | 投影 LEAN-001 当前状态与新授权 |
| `evaluations/v0.8/**` | 新增冻结 manifest、fixture、回放器、schema、原始 ledger 与阶段 A 报告 |

## 代码审查

- 审查状态：需要修改
- 审查人或审查 agent：Codex 隔离只读 Reviewer（第 1 轮 findings；同一上下文待复审）
- 审查严重等级：P1；P0 0 项、残留 P1 1 项、P2/P3 0 项
- 审查结论：`Needs Fix`；原 P1-002、P1-003 与两项 P2 已关闭，P1-001 残留一项主任务预算缺口；不允许进入 `LEAN-002`
- P0 / P1 必须修改项：
  1. `LEAN001-P1-001`：阶段 B 评分器信任缺失/负数/空 oracle/未绑定 hash 的调用方数字，可伪造 `all_gates_pass=true`。
  2. `LEAN001-P1-002`：authority / delivery / real-environment gate 未建模，`safety_gate` 仅因非 Lite 默认写 `Preserved`。
  3. `LEAN001-P1-003`：repair 只比较 P0+P1 总数，未阻止新增 P0/P1、严重度升级或稳定 ID 漂移。
- P2 建议修改项：
  1. `LEAN001-P2-001`：targeted lint 文档命令使用了 CLI 不支持的参数。
  2. `LEAN001-P2-002`：Git 事实仍停留在提交前 HEAD / working-tree。
- 风险：若不修复，阶段 B 可以被伪造数据放行，未授权 delivery 和新增高严重 finding 可能被错误标记为安全。
- 是否允许进入验收建议：否

## 第 1 轮修复独立复审

- 结论：`Needs Fix`；P0 0 项、残留 P1 1 项。
- 已关闭：`LEAN001-P1-002`、`LEAN001-P1-003`、`LEAN001-P2-001`、`LEAN001-P2-002`。
- 未完全关闭：`LEAN001-P1-001`。
- `LEAN001-P1-001-R1`：model-call evidence 允许同一 run 出现多个 `kind=main`；三个 run 固定但主任务执行总数未强制等于 manifest 上限 3。
- 必须修复：每个 run 恰好一个 main，三次 run 合计恰好 3 个 main；Reviewer/subagent/retry 单独计数；增加多 main payload 拒绝测试。
- 范围：只允许修改评分器、专项测试、本任务和看板；不得进入原型或阶段 B。

## 审查-修复循环第 1 轮

- Repairer 范围：只处理第 1 轮 3 项 P1、2 项 P2；未创建原型、未执行阶段 B、未修改现行 Skill。
- `LEAN001-P1-001`：阶段 B 改为严格 raw evidence 合同；baseline/brief/workflow/model call/output/verification 均绑定路径与 hash，工作流输入、调用数、阶段 A、维护/迁移成本由评分器复算；缺字段、负数、空 oracle、错 hash、重复/越界证据直接拒绝。
- `LEAN001-P1-002`：6 个样本新增 requested action、action authority、delivery 与 real-environment evidence；未授权 release 和缺 UA6 真实环境证据均实际返回 `Blocked`。冻结合同发生语义修复，按规则启用新评估 ID `V08-LEAN-EVAL-002`，未与旧 ledger 合并。
- `LEAN001-P1-003`：repair 按稳定 ID 与 P0/P1 严重度逐轮比较；新增 P0/P1、P1→P0、验证不改善、轮次结构异常或绝对上限异常立即 `Stop`。
- `LEAN001-P2-001`：targeted lint 改为当前 CLI 支持的 positional target。
- `LEAN001-P2-002`：Git 事实更新为已提交实现 / 审查记录与本轮 `b7938ef..HEAD`。
- 新增回归：7 项，包含 Reviewer 提供的伪通过与新增 P0 反例。
- 验证：8 / 8 零差异、7 / 7 + 4 / 4 + 41 / 41 测试、JSON/JSONL/AST、targeted lint 0 error/violation、`git diff --check` 通过。
- 是否需要复审：是；Engineer / Repairer 不自批。

## Diff 审查

- 审查方式：post-commit diff
- 审查命令：`git diff b7938ef..HEAD`
- 修改文件清单：`evaluations/v0.8/**`、本任务、看板
- 范围越界文件：无
- 审查状态：需要修改
- 审查结论：第 1 轮修复范围无越界且自动验证通过，但残留主任务调用预算 P1；进入第 2 轮有限修复。
- 是否允许进入验收建议：否

## 用户动作等级 / 验收建议

- 用户动作等级：UA3
- 是否需要用户实机测试：否
- 用户需要做什么：查看阶段 A hash、ledger、expected / actual 与门禁结论；无需自己运行命令。
- agent 已提供的证据：历史 hash 校验、8 条原始 ledger、阶段 A 报告、4 / 4 + 41 / 41 测试、targeted lint、JSON/AST 与 diff hygiene。
- 是否允许关闭任务：否；本轮未包含 `Closed` 授权。

## 提交 / 合并

- Commit 状态：已提交（本记录所在 LEAN-001 task commit）
- Commit hash：实现 `c607cb7`；第 1 轮审查记录 `9ef43d3`；第 1 轮 repair `05d6828`；本次复审写回由下一独立 commit 记录
- Merge 状态：未合并
- 回滚方式：回退本任务独立 commit；不得使用破坏性 reset。

## 停止条件

- 任一历史 commit、TASK、Review 或验证记录无法校验。
- 任一 P0/P1、authority、真实环境或 delivery 门禁漏检。
- 样本、expected label、计量单位或 oracle 在回放后被追溯修改。
- 需要修改现行 Skill、接入模型/外部服务或引入依赖才能完成阶段 A。

## 下一步建议

- 仅在阶段 A 与独立 Review 通过后创建并执行 `LEAN-002`。

## 交接摘要

- 本次完成：冻结评估协议、代表任务与历史证据，完成零额度回放并生成原始 ledger / 报告。
- 修改文件：`evaluations/v0.8/**`、本任务和看板。
- 验证结果：8 / 8 回放一致；7 / 7 + 4 / 4 + 41 / 41 测试通过；targeted lint 无 error/violation。
- 遗留问题：第 2 轮只修复 `LEAN001-P1-001-R1`；阶段 B 尚未开始。
- 下一会话建议读取：本任务、`PLAN-001`、v0.8 RFC、阶段 A 报告。
- 不要重复尝试：不得在回放后更改冻结协议以制造通过结果。
