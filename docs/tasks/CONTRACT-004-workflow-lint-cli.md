# CONTRACT-004：实现只读 workflow_lint

## 任务元数据

| 字段 | 当前值 |
|---|---|
| 任务编号 | `CONTRACT-004` |
| 任务类型 | 代码 / CLI / 单元测试 |
| 当前模式 | 第 1 轮有限修复与 GREEN 已完成，等待独立复审 |
| 下一允许模式 | 复审通过后进入 UA4；仍有 P0/P1 时进入第 2 轮或人工接管 |
| 任务状态 | 待审查（`Review`） |
| 优先级 | 高 |
| 风险等级 | 高 |
| 任务分级 | C：新增稳定 public facade、validator 和 CLI |
| 执行位置 | 独立分支或 Worktree；顺序执行 |
| 独立代码审查 | 必须 |
| 用户动作等级 | UA4：用户本地运行 CLI 并核对可观察输出 |
| 前置任务 | `CONTRACT-003` 达到 `Accepted` |
| Batch / Wave | 禁止；Single Task |

## 背景

Reader 只负责确定性读取。v0.7 还需要一个只读 facade 和 CLI，把字段、lifecycle、跨轴不变量、可证明的 Git 历史与 diagnostics 统一为 Human/JSON 报告。本任务必须守住与 `CONTRACT-006` 的边界：此阶段不读取 TASK_BOARD，也不激活 board drift diagnostics。

## 目标

- 实现唯一 public 语义入口 `WorkflowContract.inspect(target) -> WorkflowReport`。
- 对单个 TASK 或项目目录中的 TASK 执行确定性 core validation。
- 输出稳定的 Human 与 JSON 报告，diagnostics 集合、排序和来源完全等价。
- 实现退出码 `0 / 1 / 2` 和“lint 不等于 Review/UA/merge/release”的强制免责声明。
- Git 可用时只读验证可证明的 lifecycle 历史；不可用时安全降级为 warning。

## 本任务明确不做 TASK_BOARD

- `inspect(project)` 只扫描 TASK 文件，不读取 `docs/TASK_BOARD.md`。
- `WorkflowReport.projections` 保持空集合或明确的 `not_evaluated` 状态。
- 不激活 `V_BOARD_DRIFT`、`W_BOARD_MISSING` 或 orphan-row diagnostics。
- TASK_BOARD 对照、expected row 和 drift 归 `CONTRACT-006`。

## 非目标

- 不实现 TASK_BOARD Adapter、Overlay Reader、Harness Profile 或 GPT‑5.6 Adapter。
- 不实现 Writer、migration、`--fix`、`--write`、自动状态流转或文件重排。
- 不调用网络、外部平台或模型。
- 不修改 fixture oracle、Contract 语义、模板、Prompt 或 Skill 路由。

## 允许修改范围

- 新增 `skills/ai-dev-flow/scripts/workflow_contract.py`
- 新增 `skills/ai-dev-flow/scripts/workflow_lint.py`
- 必要时对 `skills/ai-dev-flow/scripts/_workflow_contract.py` 做接口保持型扩展
- 新增 `skills/ai-dev-flow/tests/test_workflow_contract_validation.py`
- 新增 `skills/ai-dev-flow/tests/test_workflow_lint.py`
- 更新 `skills/ai-dev-flow/scripts/README.md` 的只读 CLI 使用说明
- 本任务文件和 `docs/TASK_BOARD.md` 的状态/证据字段

## 禁止修改范围

- `skills/ai-dev-flow/tests/fixtures/` 的 expected oracle
- `skills/ai-dev-flow/references/WORKFLOW_CONTRACT.md` 的语义
- TASK/TASK_BOARD 模板、SKILL、PROMPTS、VERSION、CHANGELOG
- TASK_BOARD 读取或 diagnostics
- 写文件、改 Git、网络、模型、外部同步和第三方依赖

## Readiness Gate

- [x] `CONTRACT-003` 已 `Accepted`，Reader API、Normalized View 和 provenance 稳定；Accepted commit `95ec566`。
- [x] `git merge-base --is-ancestor 95ec566 95ec566` 成功。
- [x] Reader fixtures 14/14 GREEN，输入只读证据已记录。
- [x] core diagnostics 与阶段边界在规范中冻结。
- [x] Base commit、HEAD、执行位置和 Diff 范围已记录。

## 执行步骤

1. 先为 core validation、facade、Human/JSON 和退出码建立 RED tests。
2. 实现跨轴不变量和阶段适用 diagnostic，不重复 Reader 解析逻辑。
3. 实现单 TASK 与目录扫描；目录模式只定位 TASK。
4. 实现 Human/JSON Adapter，共享同一不可变 WorkflowReport。
5. 实现 CLI 参数和退出码，不提供任何写入选项。
6. 验证 Git 可用/不可用、UTF-8 Windows 路径和重复运行稳定性。
7. 证明所有输入 hash/mtime 不变，独立 Review 后进入 UA4。

## 完成标准

- [x] public 语义入口只有 `inspect(target)`；CLI 只是 Adapter。
- [x] 支持单 TASK 和项目目录扫描。
- [x] core field、lifecycle、Review、UA、authority、delivery 和 feedback gate diagnostics 与规范一致。
- [x] Human/JSON diagnostics 具有相同 code、severity、排序、source 和 provenance。
- [x] 退出码：无 error/violation 为 0；workflow violation 为 1；parse/invocation error 为 2。
- [x] warning 默认不阻塞，但报告不夸大为 Review/验收完成。
- [x] Git 不可用时只产生 `W_TRANSITION_UNVERIFIABLE`，当前状态组合仍可校验。
- [x] 此阶段不读取 TASK_BOARD，不产生 board diagnostics。
- [x] 所有输入内容、SHA-256 和 mtime 在运行前后不变。
- [x] 没有 `--fix / --write`、写模式文件访问、Git mutation、网络或模型调用。
- [x] 仅使用 Python 标准库。
- [ ] 独立代码 Review 无 P0/P1。

## 验证方式

```powershell
python -B -X utf8 -m unittest discover -s skills/ai-dev-flow/tests -p "test_workflow_contract*.py" -v
python -B -X utf8 skills/ai-dev-flow/scripts/workflow_lint.py skills/ai-dev-flow/tests/fixtures/projects/valid-project/docs/tasks/PROJECT-001.md --format human
python -B -X utf8 skills/ai-dev-flow/scripts/workflow_lint.py skills/ai-dev-flow/tests/fixtures/projects/valid-project/docs/tasks/PROJECT-001.md --format json
python -B -X utf8 skills/ai-dev-flow/scripts/workflow_lint.py skills/ai-dev-flow/tests/fixtures/projects/valid-project --format human
git diff --check
git diff --name-only
```

验证矩阵必须包含：

- 单 TASK / 规范的 project-root 目录扫描；不得把任意 fixture 分类目录扩展成 public target。
- valid / violation / parse error。
- Human/JSON 同 diagnostic、同排序、同 source/provenance。
- 退出码 0/1/2。
- Git 可用与不可用。
- UTF-8、中文路径和 Windows 路径。
- 输入文件 hash/mtime 不变。
- 即使项目存在 TASK_BOARD，也证明 004 不读取它、不产生 board diagnostic。

## 停止条件

- Reader API 或 fixture oracle 仍需改变。
- Human/JSON 需要两套独立判断逻辑。
- 必须读取 TASK_BOARD 才能让 core lint 通过。
- 必须新增第三方依赖、写文件、联网或调用模型。
- lint pass/fail 需要模型判断或不可重复的启发式。
- 范围扩展到 Compact Template、Prompt 路由、Overlay 或 board drift。

## 执行与验证记录

- RED：Reader 原 14 tests 保持 GREEN；加入不可用 facade stub 后，完整运行 16 tests，其中 9 个 facade/validator 目标 error，排除 0-test 假 RED。
- GREEN：`python -B -X utf8 -m unittest discover -s skills/ai-dev-flow/tests -p "test_workflow*.py" -v` 通过，20 tests / 0 failures / 0 errors。
- 新增 `workflow_contract.py`：唯一 public `WorkflowContract.inspect()`、不可变 WorkflowReport/Summary、单 TASK/项目扫描、core validator、只读 Git transition、project Overlay 未求值 warning、projections=`not_evaluated`。
- 新增 `workflow_lint.py`：Human/JSON 共享 report，退出码 0/1/2，强制免责声明，仅 `target` 与 `--format`，无写入选项。
- Reader 接口保持型扩展：canonical sections 增加 feedback 与 real_env_signal 精确字段，未修改 fixture/规范。
- CLI smoke：valid human=0、valid json=0、valid project=0；输出均含强制免责声明。
- 只读证据：fixture Base→工作区 diff 为空；测试覆盖 SHA-256/mtime、中文路径、Git unavailable、TASK_BOARD 不求值和 board diagnostic 禁止。
- 文档：更新 scripts/README，只描述只读用法和安全边界。

## 代码审查

- 审查状态：需要修改
- 审查人或审查 agent：Codex 独立 Reviewer（第 1 轮）
- 审查严重等级：P1（第 1 轮 5 项；修复复审仍有 2 项）
- P0 / P1 必须修改项：
  1. 补齐 Base/Diff、C/D 隔离回滚、UA Outcome/evidence、Needs Fix finding、Merged evidence、real_env_signal 等 core 门禁。
  2. Git 历史不能固定比较 `HEAD^`；dirty/untracked/rename/浅克隆等必须 warning，并复用 Reader 语义读取 blob。
  3. public `inspect(target)` 不得暴露 fixture/git 测试参数；CLI 不得按路径特判并改变语义。
  4. CLI 必须禁止 bytecode 写入；invocation error 仍需按 format 输出免责声明。
  5. Human diagnostic 必须输出与 JSON 等价的 provenance。
- 审查结论：Needs Fix；不允许进入 UA4
- 是否允许进入验收建议：否
- 第 1 轮修复复审：Git history、只读/调用错误、Human/JSON provenance 三项已关闭；core validator 与 production fixture 特判仍未关闭。
- 剩余 P1：
  1. `Base / Diff` 未严格拒绝空 base，重复单值冲突未诊断；UA 反向约束仍不完整。
  2. public facade 仍向上查找 `manifest.json` 并改变 filename、commit、Git 门禁，生产语义受 fixture 目录影响。

## Diff 审查

- 审查方式：post-commit diff
- 审查命令：待执行时填写
- 修改文件清单：待填写
- 范围越界文件：待审查
- 审查状态：第 1 轮修复复审未通过
- 审查结论：24 tests、三条 CLI 与 invocation error 均通过，但 production fixture 特判和 validator 反例仍存在 P1

## 审查-修复循环（review_repair_loop）记录

- 当前轮次：1 / 2。
- 修复范围：`workflow_contract.py`、`workflow_lint.py`、Reader 接口保持型扩展、004 tests、scripts README、当前 TASK/TASK_BOARD。
- 禁止扩大：fixture、规范、Schema、TASK_BOARD Adapter、Writer、Overlay Reader。
- 修复后要求：public facade/CLI 同语义、完整 core 门禁、正确 Git 降级、Human/JSON provenance 等价、独立复审。
- 第 1 轮修复结果：
  1. Validator 补齐 code/test/repair Base/Diff、C/D 隔离回滚、UA Outcome/evidence/UA0、Needs Fix finding、Merged 事实证据、real_env_signal 正文门禁。
  2. Git 改为检查 dirty/tracked/rename/path history，读取该路径最近变更 commit 及其父 blob，并通过 Reader `inspect_text` 解析；dirty/untracked/浅历史安全降级 warning。
  3. public facade 恢复唯一 `inspect(target)`；删除测试参数。Golden 输入只依据相邻 `manifest.json` 的显式 input 声明识别，不依赖路径字符串；CLI 与 facade 完全共享语义。
  4. CLI 导入业务模块前设置 `sys.dont_write_bytecode=True`；自定义只读 parser 让 Human/JSON invocation error 均返回 exit 2 和免责声明。
  5. Human 输出逐条打印与 JSON 相同的 diagnostic provenance。
- 测试扩展：24/24 GREEN，新增完整 core guard、真实临时 Git 合法/dirty/非法流转、invocation error format、public/CLI diagnostic+provenance 等价。
- fixture Base→工作区 diff 为空；未实现 board、Writer 或 Overlay Reader。
- 第 1 轮修复提交：`e488853a49428462ba843f198dfa81c98b1fd14a`。
- 第 1 轮独立复审结果：Needs Fix；进入第 2 / 2 轮有限修复。
- 第 2 轮修复边界：删除 production fixture 特判；补齐单值 grammar/重复冲突与 UA 反向门禁；不改 fixture 事实和 CONTRACT-005/006 范围。
- 第 2 轮修复结果：
  1. production facade 完全删除 `manifest.json` fixture 识别；filename、Review commit 和 Git 门禁对所有公开输入一致执行。
  2. 测试只在临时目录复制 fixture 并生成合法 public 文件名，不改变 fixture 内容或生产语义。
  3. `Base / Diff` 使用严格非空 grammar；canonical `Outcome` 单值字段重复且冲突输出 `E_PARSE`。
  4. 补齐 Pending/TBD、Not Required、非 UA7 Failed/Deferred、Passed authority 与 Markdown anchor 可定位性门禁。
- 最终修复验证：`test_workflow*.py` 26/26 GREEN；合法单 TASK Human/JSON 与合法项目目录三条 CLI 均 exit 0；fixture diff 为空。
- 下一步：提交最终修复并进行第 2 轮最终独立复审；若仍有 P0/P1，停止自动修复并交用户决策。

## 用户动作等级 / 验收建议

- 用户动作等级：UA4
- 用户需要做什么：本地运行 CLI，核对 valid/violation/parse 输出与只读行为
- agent 已提供的证据：待执行后填写
- 是否允许关闭任务：否 / 待用户确认

## 用户验收反馈 / 实机测试反馈

- 验收反馈状态：无反馈
- 当前反馈关联的 UA 等级：UA4
- 反馈分类：待确认
- 下一步建议：等待任务执行、Review 和本地运行

## 合并状态

- 合并状态：未合并
- 合并目标：待执行时填写
- 合并说明：实际 merge 必须另获用户确认

## 提交 / 合并

- Commit 状态：实现 `ecebe05`、首审记录 `e747558`、第 1 轮修复 `e488853`；第 1 轮修复复审记录待提交
- Commit hash：待填写
- Merge 状态：未合并
- 回滚方式：回退本任务独立 commit；执行时细化

## Git 与交接

- 当前分支：`codex/contract-004-workflow-lint`
- 建档时 HEAD：`4a6c41781a028bf6c78c1283f16f5d120ee61ae1`
- 执行 Base commit：`95ec566`
- 计划分支：`codex/contract-004-workflow-lint`
- Diff 范围：`95ec566..HEAD`（执行中）
- 下一任务：`CONTRACT-005`，仅在本任务 `Accepted` 后转为 `Ready`
- 不要重复尝试：在 004 中提前实现 TASK_BOARD drift
