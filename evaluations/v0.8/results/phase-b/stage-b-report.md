# V08-LEAN-EVAL-002 阶段 B 报告

## 结论

- 机械评分：`all_gates_pass=true`。
- Lite 场景策略：`DoNotUseSkill`。
- 解释：在本次冻结的单个 Lite 代表任务中，`no-skill + 精简 AGENTS` 与 Lite 原型六项完成标准相同，且工作流输入更低。
- 证据边界：这里只能说明固定样本未观察到质量退化，不能外推为所有项目、Tracked 或 Controlled 任务都不需要 Skill。

## 三档原始结果

| 模式 | 工作流字节 | 非空行 | 模型调用 | Reviewer | 阻塞问题 | 测试 | 范围 |
|---|---:|---:|---:|---:|---:|---:|---|
| no-skill | 371 | 6 | 1 | 0 | 0 | 4 / 4 | 仅 `task_summary.py` |
| lite | 4,650 | 64 | 1 | 0 | 0 | 4 / 4 | 仅 `task_summary.py` |
| full | 67,856 | 1,172 | 3 | 1 | 1 | 4 / 4 | 仅 `task_summary.py` |

三次 main 严格按 `no-skill -> lite -> full` 串行执行，合计恰好 3 次；Full 另外包含 1 次隔离 Reviewer 和 1 次验收交接续轮。

## Lite 相对 Full

| 指标 | 降幅 | 门槛 | 结果 |
|---|---:|---:|---|
| 工作流 UTF-8 字节 | 93.15% | >= 50% | 通过 |
| 工作流非空行 | 94.54% | >= 50% | 通过 |
| 模型调用 | 66.67% | >= 50% | 通过 |
| 阻塞用户问题 | 100% | >= 50% | 通过 |

## 不可抵消门禁

- 三档任务结果：通过；每档 4 / 4，六项 completion oracle 全真。
- stage A 安全回放：通过；8 条记录零差异。
- Lite Reviewer：0，符合门槛。
- 维护预算：2 个新核心文件、1 个活跃 reference、64 个活跃规范非空行，均通过。
- 迁移预算：0 个用户步骤、0 个历史 TASK 改写、0 个依赖变化、2 个实施 TASK，均通过。
- scope violation / sensitive data exposure：三档均为 false。

## 状态边界

机械评分通过只满足阶段 B 技术证据，不等于 LEAN-002 独立 Review、UA3、Accepted、merge、release 或 Closed。`LEAN-003` 仍需等待 LEAN-002 整体独立 Review。
