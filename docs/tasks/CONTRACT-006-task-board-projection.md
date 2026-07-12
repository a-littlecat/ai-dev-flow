# CONTRACT-006：增加 TASK_BOARD 只读投影与 drift 检查

## 任务元数据

| 字段 | 当前值 |
|---|---|
| 任务编号 | `CONTRACT-006` |
| 任务类型 | 代码 / 投影 Adapter / 模板 |
| 当前模式 | 执行与验证已完成，等待独立审查（`review_task`） |
| 下一允许模式 | 审查通过后进入 UA6；存在 P0/P1 时进入有限修复 |
| 任务状态 | 待审查（`Review`） |
| 优先级 | 中 |
| 风险等级 | 高 |
| 任务分级 | C：新增 TASK_BOARD Adapter 并影响状态一致性判断 |
| 执行位置 | 独立分支或 Worktree；顺序执行 |
| 独立代码审查 | 必须 |
| 用户动作等级 | UA6：用户回归验收 TASK 权威、看板投影和 legacy 兼容 |
| 前置任务 | `CONTRACT-004`、`CONTRACT-005` 均达到 `Accepted` |
| Batch / Wave | 禁止；Single Task |

## 背景

`CONTRACT-004` 只 lint TASK，不读取 TASK_BOARD。本任务才引入 `BoardProjectionAdapter`，把 TASK 归一化状态投影为 expected row，与现有看板行做只读 compare。projection 不是 Writer：任何 drift 只报告 expected、actual 和 provenance，不能自动修复或反向覆盖 TASK。

## 唯一允许的数据流

```text
TASK
  -> Normalized Contract
  -> expected board row
  -> compare existing board row
  -> diagnostics / stdout / JSON
```

## 目标

- 定义精简 board row：TASK、标题、等级、lifecycle、Review、UA、acceptance、delivery、TASK 路径。
- 实现 `TaskBoardProjectionAdapter` 的只读解析、expected row 与 compare。
- 在同一 WorkflowReport 中启用 `V_BOARD_DRIFT`、`W_BOARD_MISSING` 及必要的 board 结构 diagnostics。
- 让 Human/JSON 输出给出字段级 expected/actual/provenance。
- 更新 TASK_BOARD 模板，使日常视图保持轻量，完整 legacy 视图保留为兼容/诊断参考。

## 非目标

- 不得写入、创建、删除、重排或格式化 TASK_BOARD。
- 不根据 TASK_BOARD 回写 TASK。
- 不提供 `--fix`、`--write`、自动创建缺失行或状态推进。
- 不做 GitHub、Notion、Jira 或其他外部双向同步。
- 不实现 Overlay Reader；`CONTRACT-007` 前只输出未评估 warning。
- 不改变 Contract 语义、diagnostic severity、Compact 路由或 legacy 映射。

## 允许修改范围

- `skills/ai-dev-flow/scripts/workflow_contract.py`
- `skills/ai-dev-flow/scripts/workflow_lint.py`
- 必要的内部 board adapter 模块
- 新增 `skills/ai-dev-flow/tests/test_task_board_projection.py`
- 新增 board projection fixtures/oracle
- `skills/ai-dev-flow/references/TASK_BOARD_TEMPLATE.md`
- `skills/ai-dev-flow/scripts/README.md`
- 本任务文件和 `docs/TASK_BOARD.md` 的人工状态/证据字段

## 禁止修改范围

- `WORKFLOW_CONTRACT.md` 的字段、不变量或 diagnostic severity
- Reader legacy 语义、Compact Template 或 Writer 路由
- TASK_BOARD 的运行时写入逻辑
- 自动迁移、`--fix`、`--write`、网络和外部同步
- Overlay、Harness Profile、GPT‑5.6 Adapter、VERSION、CHANGELOG

## Readiness Gate

- [x] `CONTRACT-004` Accepted `7f0f7e5`、`CONTRACT-005` Accepted `61d0911`。
- [x] 两个 Accepted commit 均为当前 Base `61d0911` 的祖先。
- [x] TASK 权威、Compact/legacy 路由和 9 个投影字段已在规范冻结。
- [x] Base/HEAD `61d0911`；独立 Worktree `D:\open-source\ai-dev-flow-contract-006`；diff `61d0911..HEAD`。

## 执行步骤

1. 先定义轻量 expected row 和 board diagnostic oracle，建立 RED tests。
2. 实现只读 TASK_BOARD parser 和 expected row projection。
3. 实现字段级 compare、稳定排序和 expected/actual/provenance。
4. 把 board diagnostics 接入既有 WorkflowReport 和 Human/JSON Adapter。
5. 更新 TASK_BOARD_TEMPLATE 的轻量/legacy 边界，不删除兼容说明。
6. 证明 TASK 和 TASK_BOARD 的内容、hash、mtime 在 lint 前后不变。
7. 做 legacy、Compact、Overlay 未评估和错误结构回归。
8. 独立 Review 与 UA6 后更新任务状态，不自动修复本看板。

## 完成标准

- [x] TASK 始终是细粒度事实源，board 只做 projection/compare。
- [x] expected row 只有约定的 9 个字段，不复制 Base、Diff、锁、命令或完整门禁。
- [x] 一致、字段 drift、missing row、orphan row、duplicate ID、legacy conflict 均有确定结果。
- [x] `V_BOARD_DRIFT` 包含字段级 expected、actual 和两侧 provenance。
- [x] Human/JSON board diagnostics 语义、排序和 source 一致。
- [x] TASK/TASK_BOARD 内容、SHA-256 和 mtime 在运行前后不变。
- [x] CLI 不存在 `--fix / --write`，不自动创建或删除行。
- [x] 不以 board 值覆盖 TASK，不做双向同步。
- [x] `CONTRACT-007` 前 Overlay 只产生 `W_PROJECT_OVERLAY_UNEVALUATED` 或规范约定 warning。
- [x] TASK_BOARD_TEMPLATE 日常视图轻量，完整视图明确为 legacy/diagnostic。
- [x] 仅使用 Python 标准库。
- [ ] 独立代码 Review 无 P0/P1，用户完成 UA6 回归验收。

## 验证方式

```powershell
python -B -X utf8 -m unittest discover -s skills/ai-dev-flow/tests -p "test_*board*.py" -v
python -B -X utf8 -m unittest discover -s skills/ai-dev-flow/tests -p "test_workflow_contract*.py" -v
python -B -X utf8 skills/ai-dev-flow/scripts/workflow_lint.py . --format human
python -B -X utf8 skills/ai-dev-flow/scripts/workflow_lint.py . --format json
git diff --check
git diff --name-only
```

验证矩阵必须包含：

- board 一致。
- 单字段和多字段 drift。
- missing row、orphan row、duplicate task ID。
- legacy field conflict。
- Human/JSON 等价。
- expected/actual/provenance 完整。
- TASK 与 TASK_BOARD hash/mtime 不变。
- 无 `--fix / --write`、网络或 Git mutation。
- Overlay 未实现时不夸大为已检查。

## 停止条件

- projection 必须写文件或重排 Markdown 才能工作。
- 需要把 TASK_BOARD 重新定义为状态真相源。
- expected row 需要复制完整 TASK 内容。
- drift 需要模型判断或无法给出字段 provenance。
- 必须依赖 `CONTRACT-007` 才能完成首批核心投影。
- 需要外部平台同步、第三方依赖或自动修复。

## 代码审查

- 审查状态：未审查
- 审查人或审查 agent：待填写
- 审查严重等级：待填写
- P0 / P1 必须修改项：待审查
- 审查结论：待填写
- 是否允许进入验收建议：待确认

## 执行与验证记录

- RED：新增 board projection tests 后 3/3 失败，分别证明缺失 board diagnostics、无 9 字段 projection、单 TASK stage 标记错误。
- 新增 `_task_board.py`：只读 canonical/legacy table 定位、9 字段行解析、路径归一化、split/combined legacy 轴与 conflict 表示。
- 扩展 `WorkflowContract.inspect(project)`：生成 expected projection，比较 actual board，输出字段级 expected/actual/双侧 provenance；单 TASK 明确 `not_evaluated: single_task_target`。
- CLI JSON 序列化 projection；Human/JSON 使用同一 diagnostics。
- 覆盖矩阵：一致、单/多字段 drift、missing、orphan、duplicate ID、legacy partial、combined/split conflict、bad board、单 TASK 不读 board、hash/mtime 不变、无写入/API/网络。
- GREEN：完整 `test_*.py` 39/39 通过；board 专项 7/7 通过；fixture Base→工作区 diff 为空。
- 真实项目根 Human/JSON 均完成只读扫描；board-specific diagnostics 为 0，生成 2 个可安全投影的 expected rows。整体 exit 2 来自既有 legacy TASK 的 Reader 错误，不属于 006 board adapter，未在本任务越界修改历史任务。
- 修改文件：`_task_board.py`、`workflow_contract.py`、`workflow_lint.py`、board/validation tests、`TASK_BOARD_TEMPLATE.md`、scripts README、当前 TASK/TASK_BOARD。

## Diff 审查

- 审查方式：post-commit diff
- 审查命令：待执行时填写
- 修改文件清单：待填写
- 范围越界文件：待审查
- 审查状态：未审查
- 审查结论：待填写

## 用户动作等级 / 验收建议

- 用户动作等级：UA6
- 用户需要做什么：回归验证 TASK 权威、board drift、legacy/Compact 与不写入行为
- agent 已提供的证据：待执行后填写
- 是否允许关闭任务：否 / 待用户确认

## 用户验收反馈 / 实机测试反馈

- 验收反馈状态：无反馈
- 当前反馈关联的 UA 等级：UA6
- 反馈分类：待确认
- 下一步建议：等待任务执行、Review 和回归验收

## 合并状态

- 合并状态：未合并
- 合并目标：待执行时填写
- 合并说明：实际 merge 必须另获用户确认

## 提交 / 合并

- Commit 状态：实现候选待提交
- Commit hash：待填写
- Merge 状态：未合并
- 回滚方式：回退本任务独立 commit；执行时细化

## Git 与交接

- 当前分支：`codex/contract-006-board-projection`
- 建档时 HEAD：`4a6c41781a028bf6c78c1283f16f5d120ee61ae1`
- 执行 Base commit：`61d0911dfa3ff890b1a75493e2c5210c2ed9d7d1`
- 计划分支：`codex/contract-006-board-projection`
- Diff 范围：`61d0911..HEAD`（待审查）
- 后续任务：`CONTRACT-007` 不在本轮范围，需另行创建和确认
- 不要重复尝试：把 projection 实现成 TASK_BOARD Writer 或自动修复器
