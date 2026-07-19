# LEAN-002：构建默认关闭原型并执行阶段 B 对照

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `LEAN-002`
- `task_type`: `code`
- `task_class`: `C`
- `lifecycle`: `Review`
- `review_status`: `In Review`
- `ua_level`: `UA3`
- `ua_status`: `Pending`
- `commit_status`: `Committed`
- `merge_status`: `Not Applicable`

## 目标与边界

- 目标：在不改变现行 v0.7 默认入口的前提下，制作最多 2 个核心文件、可通过删除目录整体回退的 v0.8 Lite 原型；随后按冻结顺序使用当前执行会话同一模型完成三次同基线代表任务，并生成可机械复算的原始证据。
- 非目标：不全面精简或默认启用现行 Skill；不改冻结评估协议，不迁移历史 TASK，不作 v0.8 发布决定。
- 允许修改：原型两文件、`evaluations/v0.8/results/phase-b/**`、本任务与任务板。
- 禁止修改：现行 Skill/现行 references、冻结 manifest/oracle/threshold/benchmark baseline、历史 TASK、依赖文件、版本与发布身份。

## 依赖与授权

- 前置依赖：`LEAN-001` stage A 8 / 8 零差异且独立 Review `Passed`。
- Base commit：`da66c04`。
- 用户授权：按 PLAN-001 串行执行 LEAN-001～003。
- 允许当前任务形成独立 commit；不授权 merge、push、release、本机 Skill 同步或 `Closed`。
- 后续 `LEAN-003` 只有在阶段 B 全部门槛与本任务独立 Review 均通过后才允许创建。

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

- Base / Diff：base=da66c04;diff=da66c04..HEAD
- 隔离位置：专用分支 `codex/lean-v08-slimming`；每次 benchmark 另用独立临时 Git 工作区。
- 回滚方式：回退本任务独立 commit 并移除未接入入口的原型目录；不得使用破坏性 reset。
- 修改文件：原型两文件、`evaluations/v0.8/results/phase-b/**`、本任务与任务板；现行 Skill、冻结 manifest 和依赖未改。
- 验证证据：stage A 8 / 8 零差异；三档各 4 / 4；阶段 B 保存结果与机械评分一致；`all_gates_pass=true`。
- 原型状态：默认关闭、未接入现行入口；2 个新核心文件、1 个活跃 reference、64 个活跃规范非空行。
- 三档结果：严格串行 3 次 main；no-skill/lite/full 调用数为 1/1/3，阻塞问题为 0/0/1，Lite Reviewer 为 0。
- 效率结果：Lite 相对 Full 的字节、非空行、模型调用、阻塞问题分别降低 93.15%、94.54%、66.67%、100%。
- 阶段 B 门禁：机械评分全部通过；固定样本策略为 `DoNotUseSkill`，只说明该 Lite 样本中 no-skill 成本更低且质量相同。
- Review findings：pending independent LEAN-002 review；Full benchmark 内部 Reviewer 已 Passed，但不替代本任务整体 Review。
- UA 动作与结果：UA3 Pending；Full 产生的验收问题仅为评估证据，未由 agent 代答。

## 状态边界

- 当前为 `Review / In Review`，不是 Review Passed、UA3 Passed、Accepted、Merged、Released 或 Closed。
- 阶段 B 机械评分已通过，但必须等待本任务整体独立 Review 后才能判断 `LEAN-003` 技术门禁。
