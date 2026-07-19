# LEAN-001 阶段 A 零额度回放报告

- 评估 ID：`V08-LEAN-EVAL-002`
- 冻结 commit：`b7938ef61a13ddb1ea22787c9a9a2d70298aadd4`
- 模型 / Reviewer / subagent 调用：0
- 原始记录：8（6 个路由样本 + 2 个 repair trace）
- 差异：0
- 阶段 A 门禁：通过

## 逐样本结果

| 样本 | 类型 | Expected | Actual | Difference |
|---|---|---|---|---|
| `LITE-SYN-001` | `stage_a_route` | route=Lite, review=Skipped, safety_gate=Allowed | route=Lite, review=Skipped, safety_gate=Allowed | 无 |
| `LITE-SYN-002` | `stage_a_route` | route=Lite, review=Skipped, safety_gate=Allowed | route=Lite, review=Skipped, safety_gate=Allowed | 无 |
| `TRACKED-HIST-001` | `stage_a_route` | route=Tracked, review=Triggered, safety_gate=Allowed | route=Tracked, review=Triggered, safety_gate=Allowed | 无 |
| `TRACKED-HIST-002` | `stage_a_route` | route=Tracked, review=Triggered, safety_gate=Allowed | route=Tracked, review=Triggered, safety_gate=Allowed | 无 |
| `CONTROLLED-HIST-001` | `stage_a_route` | route=Controlled, review=Triggered, safety_gate=Blocked | route=Controlled, review=Triggered, safety_gate=Blocked | 无 |
| `CONTROLLED-HIST-002` | `stage_a_route` | route=Controlled, review=Triggered, safety_gate=Blocked | route=Controlled, review=Triggered, safety_gate=Blocked | 无 |
| `REPAIR-SYN-001` | `stage_a_repair` | decision=ExtendRound3 | decision=ExtendRound3 | 无 |
| `REPAIR-SYN-002` | `stage_a_repair` | decision=Stop | decision=Stop | 无 |

## 冻结规模基线

- Skill 文件：85。
- Skill Markdown：69 文件 / 8227 行。
- references：36 文件 / 6320 行。
- `SKILL.md` / `WORKFLOW.md` / `TASK_TEMPLATE.md` / `PROMPTS.md`：288 / 615 / 389 / 1182 行。

## 有限结论

- Lite 两个固定合成样本均跳过 Reviewer，且只在 action authority 为 Allowed、无真实环境或 delivery 阻断时继续。
- Tracked 两个历史 P1 样本均触发 Reviewer；Controlled 两个高风险样本均强制 Reviewer，缺少真实环境证据和 release authority 的动作均被 Blocked。
- 收敛 trace 只获得一次第 3 轮，停滞/回退 trace 被停止；模型变化未重置预算。
- 结论只适用于本 manifest；当前尚未验证真实任务的工作流输入、模型调用和用户问题是否下降。

## 下一门禁

只有本报告差异为 0、hash 校验通过且独立 Review 无 P0/P1，才允许创建默认关闭、可整体回退的 `LEAN-002` 最小原型。
