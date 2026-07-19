# LEAN-002：构建默认关闭原型并执行阶段 B 对照

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `LEAN-002`
- `task_type`: `code`
- `task_class`: `C`
- `lifecycle`: `Ready`
- `review_status`: `Needs Fix`
- `ua_level`: `UA3`
- `ua_status`: `Pending`
- `commit_status`: `Committed`
- `merge_status`: `Not Applicable`

## 目标与边界

- 目标：修复两项整体 Review P1；用实际原型 policy 直接驱动新 stage A，并在新协议独立 Review 通过后完成一个新的三次同基线代表任务对照。
- 非目标：不修改或合并 `V08-LEAN-EVAL-002` 历史证据；不提前全面精简或默认启用现行 Skill；不迁移历史 TASK，不作 v0.8 发布决定。
- 允许修改：原型两文件、`evaluations/v0.8/v003/**`、本任务、PLAN-001、v0.8 RFC 与任务板。
- 禁止修改：`evaluations/v0.8` 下 V002 的 manifest/replay/tests/results、现行 Skill/现行 references、历史 TASK、依赖文件、版本与发布身份。

## 依赖与授权

- 前置依赖：`LEAN-001` stage A 8 / 8 零差异且独立 Review `Passed`。
- Base commit：`da66c04`。
- 用户授权：按 PLAN-001 串行执行 LEAN-001～003。
- 允许当前任务形成独立 commit；不授权 merge、push、release、本机 Skill 同步或 `Closed`。
- 后续 `LEAN-003` 只有在阶段 B 全部门槛与本任务独立 Review 均通过后才允许创建。

## 用户续做授权与修复合同

- 用户指令：用户在看到 `Blocked` 解释后明确要求“那就继续完成 v0.8”，不接受把 v0.7 作为最终建议。
- Repair Base：`f240889`。
- 本轮只修复 `LEAN002-P1-001`、`LEAN002-P1-002`，不重开已确认通过的效率、任务结果、范围和维护/迁移结论。
- 新 evaluation ID：`V08-LEAN-EVAL-003`；V002 全部文件和结论只读保留。
- 新 main 预算：严格 3 次，顺序仍为 `no-skill -> lite -> full`；新协议独立 Review 前调用数为 0。
- 模型一致性：冻结同一父任务、`fork_turns=none`、无 model/reasoning override、canonical agent path 与顺序收据；不伪造平台未暴露的 backend 精确版本。
- 原型一致性：单一机器可读 policy 是 route/review/repair 的事实源；stage A 必须直接读取它验证 6 routes + 2 traces。
- 停止条件：新协议 Review 有 P0/P1、stage A 有差异、三档任一任务失败、scorer 门槛失败或整体 Review 有 P0/P1 时停止，不创建 `LEAN-003`。

## 固定执行协议

1. 三个隔离临时 Git 工作区都从 manifest 冻结的 benchmark baseline 建立。
2. 三次主任务使用同一当前执行模型，不指定额外模型或供应商。
3. 顺序严格为 `no-skill`、`lite`、`full`，不得并行；每档恰好一次 main。
4. `no-skill` 只加载冻结 AGENTS fixture；`lite` 只加载本原型两文件；`full` 只加载 manifest 冻结的 10 个现行工作流文件。
5. 每次只允许修改 `task_summary.py`，运行 4 项 unittest 与 `git diff --check`。
6. 每次保存模型输出、修改后文件、验证日志、逐文件输入 hash 与阻塞问题；Full 所需 Reviewer 另计调用，不伪装成 main。
7. 评分只使用 `replay.py score-phase-b`；不得因看到结果而改冻结输入、阈值或 oracle。

## 完成标准与验证

- 完成标准：默认关闭原型满足两文件和维护/迁移预算；三次同模型 main 严格串行且任务结果通过；阶段 B 原始 JSON 可机械评分；独立 Review 给出后续门禁结论。
- 验证命令或检查：stage A verify/replay、stage B scorer、评估专项 unittest、TASK lint 与 `git diff --check`。

### 详细完成标准

- [x] 原型默认关闭，未接入现行入口，删除原型目录即可回退。
- [x] 原型核心文件不超过 2，活跃 reference 不超过 12，不增加依赖或历史 TASK 改写。
- [x] 三次 main 按固定顺序串行完成，模型标识一致且每次输入/输出/验证均绑定 hash。
- [x] 三次均只修改 `task_summary.py`，4 / 4 测试及 `git diff --check` 通过。
- [x] Lite Reviewer 调用为 0；Full 的 Reviewer/流程问题按实际证据记录。
- [x] 阶段 B 原始 JSON 可被评分器接受，汇总结论不由人工填写。
- [ ] 独立 Review 无 P0/P1，且明确是否允许创建 `LEAN-003`。

### 自动验证命令

```powershell
python -B -X utf8 evaluations/v0.8/replay.py verify
python -B -X utf8 evaluations/v0.8/replay.py replay --check
python -B -X utf8 evaluations/v0.8/replay.py score-phase-b --runs evaluations/v0.8/results/phase-b/runs.json
python -B -X utf8 -m unittest discover -s evaluations/v0.8 -p "test_*.py" -v
python -B -X utf8 skills/ai-dev-flow/scripts/workflow_lint.py docs/tasks/LEAN-002.md --format human
git diff --check
```

## Outcome

- Base / Diff：base=f240889;diff=working-tree
- 隔离位置：专用分支 `codex/lean-v08-slimming`；每次 benchmark 另用独立临时 Git 工作区。
- 回滚方式：回退本任务独立 commit 并移除未接入入口的原型目录；不得使用破坏性 reset。
- 修改文件：原型两文件、`evaluations/v0.8/results/phase-b/**`、本任务与任务板；现行 Skill、冻结 manifest 和依赖未改。
- 验证证据：stage A 8 / 8 零差异；三档各 4 / 4；阶段 B 保存结果与机械评分一致；`all_gates_pass=true`。
- 原型状态：默认关闭、未接入现行入口；2 个新核心文件、1 个活跃 reference、64 个活跃规范非空行。
- 三档结果：严格串行 3 次 main；no-skill/lite/full 调用数为 1/1/3，阻塞问题为 0/0/1，Lite Reviewer 为 0。
- 效率结果：Lite 相对 Full 的字节、非空行、模型调用、阻塞问题分别降低 93.15%、94.54%、66.67%、100%。
- 阶段 B 门禁：机械评分全部通过，但整体独立 Review 发现 2 项 P1，因此全面实施门禁失败。
- Review findings：待修复 `LEAN002-P1-001` 与 `LEAN002-P1-002`；旧 finding 和 Reviewer 证据保持原样，新证据使用 V003。
- UA 动作与结果：UA3 Pending；Full 产生的验收问题仅为评估证据，未由 agent 代答。

## 独立整体复审

- Reviewer：Codex 隔离只读 Reviewer。
- 结论：`Blocked`；P0=0，P1=2，P2=0，P3=0。
- `LEAN002-P1-001`：stage A 由 `replay.py` 内置 `route_sample()` / `repair_decision()` 自洽生成，未读取原型；阶段 B 又只真实执行 Lite 样本，不能证明 Tracked、Controlled 与第三轮 repair 的实际原型规则。
- `LEAN002-P1-002`：仓库只能证明三个隔离上下文均继承当前默认模型且未传 override；运行平台未暴露可持久化的精确模型版本或 opaque call ID，无法满足冻结协议的独立审计要求。
- 已确认通过：授权 diff、默认关闭与可回退、三工作区单文件范围及各 4 / 4、stage A 8 / 8、scorer 与保存 summary 等值、专项 8 / 8、TASK lint、diff hygiene 和固定样本结论边界。
- 修复约束：修改原型会改变 Lite workflow hash，必须创建新 evaluation ID 并重跑三次；PLAN-001 的当前模型 main 总预算已用满，且平台级版本/call ID 证据当前不可获得，不能用 repair 或改协议绕过。
- 后续门禁：不允许创建 `LEAN-003`。

## 原型关闭

- 处理：原型保持未接入现行入口，并在控制面标记为关闭；不得再显式激活或作为 v0.8 实施入口。
- 保留原因：两文件原样保留为 `V08-LEAN-EVAL-002` 的 hash-bound 审计输入，使 scorer 仍可复算；这不代表原型可用或已验收。
- 回退事实：如需物理移除，可回退原型 commits `0622ba7` / `8aa3f55`；当前未做破坏性删除。

用户续做授权后，原型仅为 V003 repair 重新开放；仍未接入现行入口，也不得在新整体 Review 前作为正式 v0.8 入口。

## 状态边界

- 当前为 `Ready / Needs Fix`，等待 V003 policy 与零额度协议实现；不是 Review Passed、UA3 Passed、Accepted、Merged、Released 或 Closed。
- `LEAN-003` 仍未创建；只有新评估和 LEAN-002 整体 Review 均通过才解除门禁。
