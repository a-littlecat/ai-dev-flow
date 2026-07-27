# Loop Engineering 指南

Loop Engineering 用于编排已有模式，而不是替代已有模式。Loop 负责把 `create_task`、`execute_task`、`review_task`、`repair_task`、`close_task` 等步骤串联起来，但每一步仍要声明当前子模式。

## Loop 是什么

- 一种外层编排方式。
- 用来控制任务从分拣、执行、验证、审查、修复到验收建议的节奏。
- 用来限制自主循环次数、记录停止原因和触发用户裁决。

## Loop 不是什么

- Loop 不是 TASK。
- Loop 不是任务状态。
- Loop 不替代 `TASK_BOARD`。
- Loop 不替代 Batch 或 Parallel Wave。
- Loop 不允许无限自修复。

## Loop 与 TASK / Batch / Wave / 状态机的关系

- `TASK` 仍是最小责任单位。
- Batch 是 A/B 小任务的顺序打包方式。
- Wave 是多个执行会话的并行调度方式。
- Loop 是外层编排方式。
- Batch、Wave、Loop 都不能吞掉 TASK 边界。

## triage_loop

用途：

- 读取 `docs/TASK_BOARD.md`。
- 找出 Ready、Review、Needs Fix、Blocked。
- 找出可 Batch 的 A/B 小任务。
- 找出可 Parallel Wave 的互不冲突任务。
- 输出下一步建议。

规则：

- 默认只读。
- 不直接执行代码。
- 不启动多个执行会话。
- 只推荐 Batch / Wave 候选，不直接执行。

## goal_loop

用途：

```text
execute_task -> validation -> review_task -> repair_task -> review_task -> acceptance suggestion
```

停止条件：

- 完成标准满足。
- 自动验证通过，或明确记录无法运行原因和替代证据。
- 审查通过，或只剩 P2/P3 且已记录为后续任务。
- 用户动作等级已给出。
- 任务文件和 `TASK_BOARD` 已更新。

## review_repair_loop

用途：

- 针对 Review 后的 Needs Fix。
- `AutoRepair` 基础预算为 2 轮；仅 `CORE.md` progress gate 全部通过时允许第 3 轮，3 为自主 loop 上限。
- `Stop` 后由用户裁决，可明确授权默认一次的 `EscalatedRepair`；授权失败后不得自动连跑。
- P0/P1 必须修。
- P2 可转后续任务。
- P3 不阻塞。
- 范围越界时停止。

## status_loop

用途：

- 工作开始前或阶段结束后汇总状态。
- 输出 standup / next / blocked。
- 默认只读。
- 不改变任务状态，除非用户明确要求。

## Loop 停止条件

任何 Loop 出现以下情况必须停止：

- 任务范围膨胀。
- 修改文件明显超过预期。
- 涉及新模块或新依赖。
- 需要架构变更。
- 发现原需求不清。
- 验证无法判断。
- diff 归属不清。
- 工作区已有来源不明的未提交改动。
- P0/P1 反复出现且两轮内无法修复。
- 需要用户决策。

## Loop 最大循环次数

- `triage_loop`：默认 1 轮，只读。
- `goal_loop`：默认 1 个任务闭环。
- `review_repair_loop`：`AutoRepair` 基础 2 轮；严格进展时可有第 3 轮；其后自主 loop 停止。
- `status_loop`：默认 1 轮，只读。

第 3 轮只由 `CORE.md` progress gate 自动授予并记录原因；更换 TASK 或模型不重置 repair chain。用户确认不能让自主 loop 自动突破上限，但可另行授予有界 `EscalatedRepair`，默认一次。

## 用户裁决条件

- 风险等级无法判断。
- 需要合并、发布、删除、重构、依赖变更或架构决策。
- 第 2 轮后 progress gate 不通过，或第 3 轮后仍有 P0/P1。
- 验证环境无法由 agent 复现。
- 用户动作等级为 UA7。

## Loop 记录要求

建议把 Loop 状态记录到：

```text
docs/loops/LOOP_STATE.md
```

也可以使用本 Skill 的 `LOOP_STATE_TEMPLATE.md` 创建项目内模板。

记录内容至少包括：

- Loop 类型。
- 读取范围。
- 当前轮次。
- 输出文件。
- 停止原因。
- 下一步候选。
- 是否需要用户裁决；如已授权，记录 `ER-*` 尝试 ID 和次数。

## Loop 输出格式

```markdown
## Loop 结果

- Loop 类型：triage_loop / goal_loop / review_repair_loop / status_loop
- 当前子模式：
- 轮次：
- 读取范围：
- 输出文件：
- 结论：
- 停止原因：
- 是否触发用户裁决：

## 下一步建议

- 待填写
```
