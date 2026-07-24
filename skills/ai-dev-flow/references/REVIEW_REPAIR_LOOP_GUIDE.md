# 审查-修复循环（Review-Repair Loop / review_repair_loop）指南

审查-修复循环（Review-Repair Loop / `review_repair_loop`）用于把审查、修复、复审固化为有限循环，避免 AI 无限自修复或自我批准。

## 适用条件

- 已有明确任务文件。
- 已有明确 Review 结论。
- 已有明确 diff 范围。
- 任务状态通常为 `Needs Fix`。

## 不适用条件

- 没有任务文件。
- 没有明确 diff。
- 审查意见只是泛泛建议。
- 修复需要扩大任务范围。
- 修复需要用户决策。
- 根因不清、没有 RED / GREEN / SIGNAL，或只是用户说“不行”但缺少可判定证据。

## 与诊断和实机信号的关系

- 审查-修复循环（`review_repair_loop`）基于明确审查意见和 Repair 输入清单修复。
- Bug 诊断（`bug_diagnosis`）用于根因不清时建立证据、假设和复现信号。
- 实机测试信号复现（`real_env_signal`）用于真实环境问题进入 Bug 诊断前，把用户反馈转成 RED / GREEN / SIGNAL。
- 不要把“猜测修复”伪装成修复任务（`repair_task`）。
- Repairer 只能处理审查指出的问题或明确 Repair 输入清单，不得扩大范围或自我批准。

## 基本规则

- 一轮 repair 只计“冻结 finding 的 patch 到下一次独立复审”；只读 Review、无 patch UA、诊断、测试重跑、收据同步和记录纠错不计。
- `AutoRepair` 基础预算为 2 轮；只有 `CORE.md` progress gate 全部通过时才允许第 3 轮，3 为自主 loop 上限。
- 达到 `Stop` 后进入用户裁决；用户可明确授权默认一次的有界 `EscalatedRepair`，不要求用户必须亲自修改。
- 同一 finding / closure contract 继承 `repair_chain_id` 和计数；换 TASK 或模型不重置。
- 每轮 repair 只能处理审查指出的问题。
- 每轮结束必须重新进入 `review_task`。
- `repair_task` 不得直接把任务标记为 Accepted。
- Reviewer 不得直接修复。
- Engineer / Repairer 不得自我批准。
- 建议修改项如果超出当前任务范围，应转为后续任务。

## 审查严重等级处理

| 审查等级 | 中文说明 | 处理规则 |
| --- | --- | --- |
| P0 | 阻止合并 / 验收 | 必须修复 |
| P1 | 高风险 | 验收前必须修复 |
| P2 | 建议修复 | 可转后续任务 |
| P3 | 风格或可选建议 | 不阻塞 |

## 每轮记录

每轮必须记录：

- 本轮编号。
- 本轮处理的审查意见。
- 未处理意见及原因。
- 修改文件。
- 验证命令。
- 验证结果。
- 是否需要再审查。
- 是否进入用户裁决，以及是否获得 `EscalatedRepair` 授权。

## 停止条件

- P0/P1 已修复并复审通过。
- 剩余问题均为 P2/P3，且已记录后续任务或风险。
- 第 2 轮后 progress gate 不通过，或第 3 轮后仍无法通过：自主 loop `Stop`，进入用户裁决。
- 修复需要扩大范围。
- diff 归属不清。
- 验证无法判断。
- 需要用户决策。

## 输出格式

```markdown
## 审查-修复循环（review_repair_loop）记录

- 当前任务：
- 当前轮次：
- 自主最大轮次：3（基础 2；第 3 轮需 progress gate）
- repair_chain_id：
- 当前尝试：AR-1 / AR-2 / AR-3 / ER-1...
- 本轮角色：修复者（Repairer）/ 审查者（Reviewer）

## 本轮处理

| 审查项 | 严重等级 | 处理结果 | 说明 |
| --- | --- | --- | --- |
| 待填写 | P0 / P1 / P2 / P3 | 已修复 / 转后续 / 不处理 | 待填写 |

## 验证

- 验证命令：
- 验证结果：

## 下一步

- 进入 review_task
- Stop 并进入用户裁决
- 按明确授权执行一次 EscalatedRepair
- 转后续任务
```
