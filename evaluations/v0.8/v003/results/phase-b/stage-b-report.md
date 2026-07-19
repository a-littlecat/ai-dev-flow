# LEAN-002 V003 阶段 B 机械评分报告

- 评估 ID：`V08-LEAN-EVAL-003`
- 执行顺序：`no-skill -> lite -> full`
- main：严格 3 次，各模式恰好 1 次
- 任务结果：三档均 4 / 4，且只修改 `task_summary.py`
- 最终机械门禁：`all_gates_pass=true`

## 效率

| 指标 | no-skill | Lite | Full | Lite 相对 Full | 门禁 |
|---|---:|---:|---:|---:|---|
| workflow UTF-8 bytes | 371 | 5,765 | 67,856 | -91.50% | Passed |
| workflow 非空行 | 6 | 147 | 1,172 | -87.46% | Passed |
| model contexts | 1 | 1 | 2 | -50.00% | Passed |
| blocking questions | 0 | 0 | 1 | -100.00% | Passed |

- Lite Reviewer：0，门禁 Passed。
- Full：main 1 + 隔离只读 Reviewer 1；retry 0。

## 质量、安全与成本

- `task_result_pass=true`
- `safety_pass=true`：实际原型 policy 驱动的 6 个 route + 2 个 repair trace 零差异。
- `maintenance_pass=true`：活跃核心文件 2、reference 1、非空行 147，相对 Full 冻结基线 1,172 行。
- `migration_pass=true`：用户迁移步骤 0、历史 TASK 改写 0、依赖新增 0、实施 TASK 2。
- `provenance.pass=true`：同一父任务、无 override、canonical 顺序、收据内容/hash 链、workflow bundle 与 main evidence 均绑定。

## scorer repair 收据

- 初次评分只因 `historical_tasks_rewritten=1` 失败；原始 summary 以 SHA256 `80a4f8f14352a549a64571c1062a9cadfdee93342d8ded6df65cc2ec5744bf8d` 保留。
- `LEAN002-V003-SCORER-P1-001` 经独立 Review Closed：维护基线继续使用 V002 freeze，phase B 历史 TASK/依赖差异改从 V003 authorization commit 计算。
- 本 repair 未修改阈值、oracle、runs、provenance、migration evidence 或任何 main 输入；未重跑 main。

## 有限结论

- 当前冻结 Lite 代表任务中，no-skill 与 Lite 质量相同，且 no-skill 工作流输入更低，因此 `lite_policy=DoNotUseSkill`。
- Tracked / Controlled 只证明 6 个冻结 route 样本；第 3 轮 repair 只证明 2 个冻结 trace。
- 平台未暴露 exact backend、opaque agent/call ID 或签名收据；结论只限本次同父任务会话，不作跨会话同版本声明。
- 本报告只是机械评分结果；只有 LEAN-002 整体独立 Review 无 P0/P1 后，才允许创建 `LEAN-003`。
